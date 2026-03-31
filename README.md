# Private Local AI Assistant (Batbot)

A highly capable, private AI assistant built with the [Google Agent Development Kit (ADK)](https://github.com/google/adk-python). It acts as a secure, local bridge between your devices (via Telegram) and your PC, local files, emails, and research tools. 

Designed to be heavily customizable, you can mold it to be your researcher, software engineer, or daily operations manager.

## 🌟 Key Features

*   **Secure Remote Access:** Whitelisted Telegram User ID authentication and a session-based password lock (`/lock`).
*   **Multimodal Voice Support:** Free, local, and private voice-to-text using an open-source **Whisper** model (no API costs, handles long audio).
*   **Email Integration:** Read, search, and send emails directly from your personal or work account via secure IMAP/SMTP.
*   **Local RAG (Knowledge Base):** A private vector database (ChromaDB) that ingests your PDFs, Word docs, and Images (local OCR). Ask technical questions grounded in your local documents.
*   **NotebookLM Integration:** Fully automate Google NotebookLM via the `notebooklm-py` CLI to create notebooks, upload sources, and generate audio podcasts/overviews.
*   **Autonomous Researcher:**
    *   **ArXiv:** Search for papers, read abstracts, and auto-download PDFs into your knowledge base.
    *   **IEEE Xplore:** Search the IEEE database and retrieve full-text content.
*   **Web Scraper:** Extract clean text from documentation, blog posts, or news articles.
*   **PC & Coding Assistant:** Execute local terminal commands and modify existing Python files with surgical string replacement.
*   **Human-in-the-Loop (Safety):** The agent **cannot** send emails, run shell commands, or write files without your explicit "Yes" on Telegram.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
*   **Python 3.12+**
*   **Poetry**
*   **gcloud CLI** (Authenticated via `gcloud auth application-default login`)
*   *(Optional)* Playwright & Chromium for NotebookLM authentication.

### 2. Environment Configuration (`.env`)
Create a `.env` file in the root directory:

```env
# --- Google Cloud / Gemini ---
GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
GOOGLE_CLOUD_LOCATION="global"
GOOGLE_GENAI_USE_VERTEXAI=TRUE

# --- Telegram Security ---
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
ALLOWED_USER_ID=123456789  # Your Telegram User ID
BOT_PASSWORD="YourSecurePassword"

# --- Email Integration ---
EMAIL_ADDRESS="your.email@example.com"
EMAIL_PASSWORD="your_app_password"

# --- Academic APIs (Optional) ---
IEEE_API_KEY="your_ieee_key"
IEEE_AUTH_TOKEN="your_ieee_tdm_token"
```

### 3. Installation
```bash
poetry install

# Optional: Setup NotebookLM automation login
poetry run playwright install chromium
poetry run notebooklm login
```

---

## 🚀 Running the Assistant

Start the gateway:
```bash
poetry run python telegram_main.py
```
*Note: On the first run, the system will download ~400MB of open-source models for Whisper and local Embeddings.*

---

## 🧰 Typical Workflows

### 🎓 Research & Learning
*   **Literature Review:** *"Search ArXiv for 'agentic workflows' and summarize the top 3."*
*   **Acquisition:** *"Download the second paper and ingest it into my knowledge base."*
*   **Podcast Generation:** *"Create a new NotebookLM notebook, add my recent research papers to it, and generate an audio overview podcast."*

### 💻 Engineering & DevOps
*   **System Check:** *"Check the status of my local Docker containers."*
*   **File Editing:** *"In `sandbox/script.py`, replace `verbose=True` with `verbose=False`."*
*   **Terminal Execution:** *"Run `git status` and tell me what files changed."*

### 📧 Daily Operations
*   **Email:** *"Search my inbox for emails from 'boss@company.com' containing 'meeting'."*
*   **Summarization:** *"Fetch this URL and summarize the main points for me."*

### 🛡️ Safety System (HITL)
When the assistant attempts a sensitive action (Shell, Write, Email), it will pause and generate an `action_id`.
*   **Assistant:** *"I am about to run `rm sandbox/temp.py`. Do you approve?"*
*   **You:** *"Yes"*
*   **Assistant:** *"Approved. Command executed."*

---

## 🏗️ Project Structure
*   `telegram_main.py`: Entry point and security gateway for Telegram.
*   `agent/`:
    *   `root_agent.py`: The brain (LlmAgent) and tool registrations.
    *   `tools.py`: Python functions for file I/O, scraping, and APIs.
    *   `rag_manager.py`: ChromaDB and text extraction logic.
    *   `email_manager.py`: IMAP/SMTP handlers.
    *   `audio_transcriber.py`: Local Whisper transcription.
    *   `config.py`: Centralized instructions and model settings.
*   `knowledge_base/`: Folder for your PDFs and documents to ingest.
*   `sandbox/`: The default workspace for code and text outputs.
*   `chroma_db/`: Persistent local vector database for RAG.