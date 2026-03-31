# Private Local AI Assistant (Batbot)

![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)
![Google ADK](https://img.shields.io/badge/Google%20ADK-latest-4285F4?logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

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
*   **One of the following authentication options** (see step 2)
*   *(Optional)* Playwright & Chromium for NotebookLM automation.

### 2. Authentication — Choose ONE Option

**Option A — Vertex AI (recommended for GCP users)**

Authenticate once with the gcloud CLI:
```bash
gcloud auth application-default login
```

Then set in your `.env`:
```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
```

**Option B — Gemini API Key (no GCP account needed)**

Get a free key at [Google AI Studio](https://aistudio.google.com/app/apikey) and set in your `.env`:
```env
GOOGLE_API_KEY=your_gemini_api_key
```

### 3. Full `.env` Configuration

Copy the template and fill in your values:
```bash
cp .env.template .env
```

```env
# --- Authentication (choose ONE option above) ---
GOOGLE_GENAI_USE_VERTEXAI=TRUE          # Option A
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
# GOOGLE_API_KEY=your_key               # Option B (comment out A)

# --- Telegram Security ---
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ALLOWED_USER_ID=123456789               # Your Telegram User ID (@userinfobot)
BOT_PASSWORD=YourSecurePassword

# --- Email Integration ---
EMAIL_ADDRESS=your.email@example.com
EMAIL_PASSWORD=your_app_password

# --- Academic APIs (Optional) ---
IEEE_API_KEY=your_ieee_key
IEEE_AUTH_TOKEN=your_ieee_tdm_token
```

### 4. Personalize the Agent

Open `agent/config.py` and edit the `ROOT_AGENT_INSTRUCTIONS` section to describe yourself:

```python
ROOT_AGENT_INSTRUCTIONS = """
You are Batbot, a highly capable, private AI assistant.

Your user is John.   # <-- replace with your name

The User's Context:
1. A PhD candidate at University X working on topic Y.
2. ...

- Address the user as 'John'.   # <-- replace with your first name
...
"""
```

This is the agent's system prompt — it shapes all its behavior and defaults.

### 5. Install & Run

```bash
poetry install

# Optional: Setup NotebookLM automation
poetry run playwright install chromium
poetry run notebooklm login

# Start the bot
poetry run python telegram_main.py
```

> **First run note:** The system will download ~400 MB of open-source models for Whisper and local embeddings.

---

## 🚀 Usage

Send a message to your bot on Telegram. You will be prompted for the password once per session. After authenticating, Batbot is ready.

Type `/lock` at any time to secure the session.

---

## 🧰 Typical Workflows

### 🎓 Research & Learning
*   **Literature Review:** *"Search ArXiv for 'agentic workflows' and summarize the top 3."*
*   **Acquisition:** *"Download the second paper and ingest it into my knowledge base."*
*   **Podcast Generation:** *"Create a new NotebookLM notebook, add my recent research papers, and generate an audio overview."*

### 💻 Engineering & DevOps
*   **System Check:** *"Check the status of my local Docker containers."*
*   **File Editing:** *"In `sandbox/script.py`, replace `verbose=True` with `verbose=False`."*
*   **Terminal Execution:** *"Run `git status` and tell me what files changed."*

### 📧 Daily Operations
*   **Email:** *"Search my inbox for emails from 'boss@company.com' containing 'meeting'."*
*   **Summarization:** *"Fetch this URL and summarize the main points for me."*

### 🛡️ Safety System (Human-in-the-Loop)
When the assistant attempts a sensitive action (shell command, file write, email send), it pauses and generates an `action_id`:

*   **Assistant:** *"I am about to run `rm sandbox/temp.py`. Do you approve?"*
*   **You:** *"Yes"*
*   **Assistant:** *"Approved. Command executed."*

---

## 🏗️ Project Structure

```
Batbot/
├── telegram_main.py        # Entry point and Telegram security gateway
├── agent/
│   ├── root_agent.py       # Root LlmAgent — model init and tool registration
│   ├── searcher.py         # Search sub-agent (Google Search via ADK)
│   ├── tools.py            # All tool functions (file I/O, scraping, APIs)
│   ├── rag_manager.py      # ChromaDB ingestion and retrieval logic
│   ├── email_manager.py    # IMAP/SMTP email handlers
│   ├── audio_transcriber.py# Local Whisper STT transcription
│   └── config.py           # Model settings and agent instructions (personalize this)
├── runner/
│   ├── app_runner.py       # ADK session runner
│   └── local_session_service.py  # Pickle-based persistent session storage
├── knowledge_base/         # Drop your PDFs and docs here to ingest
├── sandbox/                # Default workspace for agent file outputs
├── chroma_db/              # Persistent local vector database (auto-created)
├── .env.template           # Copy to .env and fill in your values
└── pyproject.toml
```

---

## 🔒 Privacy & Security

*   Your `.env` file, session data (`.pkl`), vector database (`chroma_db/`), and knowledge base are all **gitignored** and never leave your machine.
*   Only your Telegram User ID can interact with the bot.
*   All sensitive actions require explicit approval before execution.
*   Voice messages are transcribed **locally** — no audio is sent to external APIs.
