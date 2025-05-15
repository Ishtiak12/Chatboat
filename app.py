from flask import Flask, render_template, request, jsonify
import requests
from flask_cors import CORS
import os
from docx import Document
import PyPDF2
import base64
from datetime import datetime
import uuid

app = Flask(__name__)
#CORS(app, origins=["http://localhost:5173"])
CORS(app, origins=["http://localhost:5173", "https://tial-dev.rpu.solutions"])

# Configuration
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Chatbase API configuration
CHATBASE_API_KEY = ""
CHATBASE_CHATBOT_ID = ""
CHATBASE_API_URL = ""
CHATBASE_HISTORY_URL = ""

# Supported models
MODELS = [
    "gpt-4", "gpt-4-turbo", "gpt-4o",
    "claude-3-opus", "claude-3-sonnet", "claude-3-haiku",
    "gemini-1.5-pro", "gemini-1.5-flash", "DeepSeek-V3",
    "DeepSeek-R1", "gemini-2.0-pro", "gemini-2.0-flash", "command-r-plus"
]

# In-memory conversation storage
conversations = {}

def extract_text_from_docx(docx_path):
    try:
        doc = Document(docx_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"Error extracting from DOCX: {e}")
        return None

def extract_text_from_txt(txt_path):
    try:
        with open(txt_path, 'r') as file:
            return file.read()
    except Exception as e:
        print(f"Error extracting from TXT: {e}")
        return None

def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            return "".join([page.extract_text() for page in reader.pages])
    except Exception as e:
        print(f"Error extracting from PDF: {e}")
        return None

def send_message_to_chatbase(user_message, file_path=None, conversation_id=None, model=None):
    headers = {
        "Authorization": f"Bearer {CHATBASE_API_KEY}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }

    # Build the messages array
    messages = [{
        "role": "user",
        "content": user_message or ""
    }]

    # Add file content if provided
    if file_path:
        ext = os.path.splitext(file_path)[1].lower()
        extractors = {
            '.txt': extract_text_from_txt,
            '.docx': extract_text_from_docx,
            '.pdf': extract_text_from_pdf
        }
        extracted_text = extractors.get(ext, lambda x: None)(file_path)
        if extracted_text:
            messages[0]['content'] += f"\n\nFile Content:\n{extracted_text}"

    payload = {
        "chatbotId": CHATBASE_CHATBOT_ID,
        "stream": False,
        "temperature": 0,
        "messages": messages
    }

    if conversation_id:
        payload["conversationId"] = conversation_id

    if model and model in MODELS:
        payload["model"] = model

    try:
        response = requests.post(
            CHATBASE_API_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        # Print debug information
        print("Request Payload:", payload)
        print("Response Status:", response.status_code)
        print("Response Text:", response.text)
        
        response.raise_for_status()
        response_data = response.json()
        return response_data.get("text", "No response text")
    except requests.exceptions.RequestException as e:
        error_msg = f"Chatbase API error: {str(e)}"
        if hasattr(e, 'response') and e.response:
            error_msg += f"\nResponse: {e.response.text}"
        print(error_msg)
        return error_msg

@app.route('/api/start-conversation', methods=['POST'])
def start_conversation():
    conversation_id = str(uuid.uuid4())
    conversations[conversation_id] = {
        'created_at': datetime.now().isoformat(),
        'messages': [],
        'summaries': []
    }
    return jsonify({
        'conversation_id': conversation_id,
        'status': 'new conversation started'
    })

@app.route('/api', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message')
    file_base64 = data.get('file')
    file_type = data.get('file_type')
    conversation_id = data.get('conversation_id')
    model = data.get('model')
    file_path = None

    # If no conversation ID provided, create a new one
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        conversations[conversation_id] = {
            'created_at': datetime.now().isoformat(),
            'messages': [],
            'summaries': []
        }

    # If conversation ID exists but not in our storage, initialize it
    if conversation_id not in conversations:
        conversations[conversation_id] = {
            'created_at': datetime.now().isoformat(),
            'messages': [],
            'summaries': []
        }

    if file_base64 and file_type:
        try:
            file_content = base64.b64decode(file_base64)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"upload.{file_type}")
            with open(file_path, 'wb') as f:
                f.write(file_content)
        except Exception as e:
            print(f"File decode error: {e}")
            return jsonify({'error': 'Invalid file data'}), 400

    if not user_input and not file_path:
        return jsonify({'error': 'No input provided'}), 400
    
    try:
        response = send_message_to_chatbase(user_input, file_path, conversation_id, model)
        
        # Store message in conversation history
        if user_input:
            conversations[conversation_id]['messages'].append({
                'role': 'user',
                'content': user_input,
                'timestamp': datetime.now().isoformat(),
                'type': 'chat'
            })
        if file_path:
            conversations[conversation_id]['messages'].append({
                'role': 'user',
                'content': f"Uploaded file: {file_type}",
                'timestamp': datetime.now().isoformat(),
                'type': 'file_upload'
            })
        
        conversations[conversation_id]['messages'].append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat(),
            'type': 'chat_response'
        })

        return jsonify({
            'response': response,
            'conversation_id': conversation_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.json
    text = data.get('text')
    file_base64 = data.get('file')
    file_type = data.get('file_type')
    model = data.get('model')
    conversation_id = data.get('conversation_id')
    file_path = None

    # If no conversation ID provided, create a new one
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        conversations[conversation_id] = {
            'created_at': datetime.now().isoformat(),
            'messages': [],
            'summaries': []
        }

    if file_base64 and file_type:
        try:
            file_content = base64.b64decode(file_base64)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"summarize.{file_type}")
            with open(file_path, 'wb') as f:
                f.write(file_content)
        except Exception as e:
            print(f"File decode error: {e}")
            return jsonify({'error': 'Invalid file data'}), 400

    if not text and not file_path:
        return jsonify({'error': 'No input provided'}), 400

    try:
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            extractors = {
                '.txt': extract_text_from_txt,
                '.docx': extract_text_from_docx,
                '.pdf': extract_text_from_pdf
            }
            text = extractors.get(ext, lambda x: None)(file_path)

        if not text:
            return jsonify({'error': 'No text to summarize'}), 400

        summary = send_message_to_chatbase(f"Summarize this:\n{text}", model=model)
        
        # Store summary in conversation history
        conversations[conversation_id]['summaries'].append({
            'text': text if len(text) < 100 else text[:100] + "...",
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        })
        
        # Also store as a message
        conversations[conversation_id]['messages'].append({
            'role': 'user',
            'content': f"Summary request: {text if len(text) < 50 else text[:50] + '...'}",
            'timestamp': datetime.now().isoformat(),
            'type': 'summary_request'
        })
        
        conversations[conversation_id]['messages'].append({
            'role': 'assistant',
            'content': summary,
            'timestamp': datetime.now().isoformat(),
            'type': 'summary_response'
        })

        return jsonify({
            'summary': summary,
            'conversation_id': conversation_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

@app.route('/history', methods=['GET'])
def get_history():
    conversation_id = request.args.get('conversation_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)

    if start_date and end_date and start_date > end_date:
        return jsonify({'error': 'Start date must be before end date'}), 400

    # First check local conversation storage
    if conversation_id and conversation_id in conversations:
        return jsonify({
            'conversation_id': conversation_id,
            'created_at': conversations[conversation_id]['created_at'],
            'messages': conversations[conversation_id]['messages'],
            'summaries': conversations[conversation_id]['summaries']
        })

    # Fall back to Chatbase API if not found locally
    headers = {
        "Authorization": f"Bearer {CHATBASE_API_KEY}",
        "Content-Type": "application/json"
    }

    params = {
        "chatbotId": CHATBASE_CHATBOT_ID,
        "page": page,
        "size": size
    }

    if conversation_id:
        params["chatId"] = conversation_id
    
    date_format = "%Y-%m-%d"
    if start_date:
        try:
            datetime.strptime(start_date, date_format)
            params["startDate"] = start_date
        except ValueError:
            return jsonify({'error': 'Invalid start date format'}), 400
    
    if end_date:
        try:
            datetime.strptime(end_date, date_format)
            params["endDate"] = end_date
        except ValueError:
            return jsonify({'error': 'Invalid end date format'}), 400

    try:
        response = requests.get(CHATBASE_HISTORY_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if 'conversations' in data:
            return jsonify(data)
        elif 'data' in data and 'conversations' in data['data']:
            return jsonify(data['data'])
        elif 'items' in data:
            return jsonify({'conversations': data['items']})
        
        return jsonify({'error': 'Unexpected API response format'}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/conversations', methods=['GET'])
def list_conversations():
    return jsonify({
        'conversations': [
            {
                'id': conv_id,
                'created_at': conv['created_at'],
                'message_count': len(conv['messages']),
                'summary_count': len(conv['summaries'])
            }
            for conv_id, conv in conversations.items()
        ]
    })

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)