
# 🧠 Chatbase File Conversational API

This Flask-based application allows users to chat with uploaded files (`.txt`, `.docx`, `.pdf`) and get summaries using the Chatbase API. It includes file processing, conversation tracking, and integration with various LLMs.

---

## 🚀 Features

- 📁 Upload and process `.txt`, `.docx`, and `.pdf` files
- 💬 Chat with the file contents
- ✂️ Get AI-generated summaries
- 🧾 In-memory conversation history
- 🔐 CORS enabled for frontend integration
- 🌐 Multi-model support (GPT-4, Claude, Gemini, etc.)

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/chatbase-file-api.git
cd chatbase-file-api
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Example `requirements.txt`:**

```
Flask
Flask-Cors
requests
python-docx
PyPDF2
```

---

## 🔧 Configuration

In `app.py`, configure your Chatbase credentials:

```python
CHATBASE_API_KEY = "your_chatbase_api_key"
CHATBASE_CHATBOT_ID = "your_chatbase_chatbot_id"
```

---

## 🧪 Running the Application

```bash
python app.py
```

Visit: [http://localhost:5000](http://localhost:5000)

---

## 📡 API Endpoints

### `/api/start-conversation` `[POST]`

Starts a new conversation.
```json
{
  "conversation_id": "uuid",
  "status": "new conversation started"
}
```

---

### `/api` `[POST]`

Chat with message and/or file.

**Payload:**
```json
{
  "message": "What is this document about?",
  "file": "base64_encoded_file",
  "file_type": "pdf|docx|txt",
  "conversation_id": "optional",
  "model": "optional"
}
```

---

### `/summarize` `[POST]`

Summarize provided text or uploaded file.

**Payload:**
```json
{
  "text": "optional text",
  "file": "base64_encoded_file",
  "file_type": "pdf|docx|txt",
  "conversation_id": "optional",
  "model": "optional"
}
```

---

### `/history` `[GET]`

Get conversation history.

**Query Parameters:**
- `conversation_id`
- `start_date=YYYY-MM-DD`
- `end_date=YYYY-MM-DD`
- `page`, `size`

---

### `/conversations` `[GET]`

Returns all in-memory conversations.

---

## 🌐 CORS

CORS enabled for:

```python
CORS(app, origins=["http://localhost:5173", "https://tial-dev.rpu.solutions"])
```

---

## 📁 Uploads

Uploaded files are stored temporarily in the `uploads/` directory and removed after use.

---

## 🔒 Note

This app stores conversation data in memory. For production, integrate a database for persistence.

---

## 📃 License

MIT License
