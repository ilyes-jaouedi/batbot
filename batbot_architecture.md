# Batbot System Architecture

```mermaid
graph TD
    %% User Interface
    User((Ilyes)) -->|Text / Voice| Telegram[Telegram Bot]
    
    %% Gateway & Security
    subgraph Local PC (Security Gateway)
        Telegram -->|Webhook/Polling| TG_Main[telegram_main.py]
        TG_Main -->|1. Whitelist Check| Auth{Authorized?}
        Auth -->|No| Drop[Ignore]
        Auth -->|Yes| Pwd{Password Lock}
        Pwd -->|Locked| Prompt[Ask Password]
        Pwd -->|Unlocked| Processor
    end

    %% Input Processing
    subgraph Input Processor
        Processor -->|Voice| Whisper[Local Whisper Model]
        Whisper -->|Transcription| Agent_Core
        Processor -->|Text| Agent_Core
    end

    %% The Brain
    subgraph Batbot Brain (ADK)
        Agent_Core[Root Agent / Coordinator]
        Agent_Core -->|Config| Config[agent/config.py]
        Agent_Core -->|Search Delegate| SubAgent[search_agent.py]
    end

    %% Tools & Actions
    Agent_Core --> Tools{Tools Manager}
    
    subgraph Action Layers
        Tools -->|Read/Write| FileSys[(Local File System / Sandbox)]
        Tools -->|RAG| Chroma[(ChromaDB / Knowledge Base)]
        Tools -->|Email| Mail[[IMAP/SMTP Server]]
        Tools -->|Shell| CMD[Windows PowerShell / CMD]
        Tools -->|APIs| WebAPI[ArXiv / IEEE API]
    end

    %% Human in the Loop
    CMD --> HITL{HITL Approval}
    Mail --> HITL
    FileSys -->|Writes| HITL
    HITL -->|Request Action ID| TG_Main
    TG_Main -->|Confirm?| User
    User -->|Yes/No| TG_Main
    TG_Main -->|Approve/Reject| Tools
```

## Key Components:
1. **Frontend:** Telegram (Remote Control).
2. **Security:** Whitelist + Session Password.
3. **Transcription:** Local Whisper (Open Source).
4. **Brain:** Google ADK `LlmAgent` (Gemini 2.0 Flash).
5. **Memory:** Persistent Pickle-based session service.
6. **Knowledge:** Local RAG using ChromaDB & Sentence-Transformers.
7. **Safety:** Human-in-the-Loop (HITL) for all destructive or external actions.
