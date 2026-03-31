import os
import json
import subprocess
import requests
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import arxiv
from .rag_manager import rag_manager
from .config import KNOWLEDGE_BASE_DIR
from .email_manager import email_manager

# Import the shared IEEE SDK
from xploreapi.xploreapi import XPLORE

# --- HUMAN-IN-THE-LOOP STATE ---
pending_actions = {}

def approve_action(action_id: str) -> str:
    """
    Executes an action that was previously paused pending human approval.
    The agent MUST only call this if the user explicitly says 'Yes' or 'Approve' 
    to the previously requested confirmation.
    
    Args:
        action_id: The unique ID of the pending action.
    """
    if action_id not in pending_actions:
        return "Error: Invalid or expired action ID."
        
    action = pending_actions.pop(action_id)
    action_type = action.get('type')
    
    try:
        if action_type == 'write_file':
            with open(action['filename'], "w", encoding="utf-8") as f:
                f.write(action['content'])
            return f"Approved and executed: Successfully wrote to {action['filename']}"
            
        elif action_type == 'replace_file':
            with open(action['filename'], 'r', encoding='utf-8') as f:
                content = f.read()
            for old_str, new_str in zip(action['old_strings'], action['new_strings']):
                content = content.replace(old_str, new_str)
            with open(action['filename'], 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Approved and executed: Successfully updated '{action['filename']}'."
            
        elif action_type == 'shell_command':
            result = subprocess.run(
                action['command'], shell=True, capture_output=True, text=True, timeout=30
            )
            output = result.stdout
            if result.stderr:
                output += f"\n--- STDERR ---\n{result.stderr}"
            if not output.strip():
                return f"Approved and executed: Command '{action['command']}' succeeded but produced no output."
            return output
            
        elif action_type == 'send_email':
            return email_manager.send_email(
                to_address=action['to_address'], 
                subject=action['subject'], 
                body=action['body']
            )
            
        else:
            return "Error: Unknown action type."
    except Exception as e:
        return f"Error executing approved action: {str(e)}"

def reject_action(action_id: str) -> str:
    """
    Cancels a pending action if the user says 'No' or 'Cancel'.
    """
    if action_id in pending_actions:
        del pending_actions[action_id]
        return "Action cancelled successfully."
    return "No such pending action to cancel."

# --- MODIFIED TOOLS (Require Approval) ---

def write_to_file(filename: str, content: str) -> str:
    """
    Proposes writing content to a file. 
    THIS DOES NOT EXECUTE IMMEDIATELY. It returns an action_id.
    You MUST ask the user: "Do you approve writing to [filename]?". 
    If they say yes, use the approve_action tool with the ID.
    
    Args:
        filename: The name of the file to write to.
        content: The text content to write into the file.
    """
    action_id = f"write_{int(datetime.now().timestamp())}"
    pending_actions[action_id] = {
        'type': 'write_file',
        'filename': filename,
        'content': content
    }
    return f"ACTION PAUSED: User approval required. Ask the user if they approve writing to '{filename}'. If they say yes, call approve_action('{action_id}'). If no, call reject_action('{action_id}')."

def replace_in_file(filename: str, old_strings: List[str], new_strings: List[str]) -> str:
    """
    Proposes modifying an existing file.
    THIS DOES NOT EXECUTE IMMEDIATELY. It returns an action_id.
    You MUST ask the user for approval before calling approve_action.
    """
    if len(old_strings) != len(new_strings):
        return "Error: old_strings and new_strings lists must have the same number of items."
        
    if not os.path.exists(filename):
        return f"Error: File '{filename}' not found. Cannot replace."

    action_id = f"replace_{int(datetime.now().timestamp())}"
    pending_actions[action_id] = {
        'type': 'replace_file',
        'filename': filename,
        'old_strings': old_strings,
        'new_strings': new_strings
    }
    return f"ACTION PAUSED: User approval required. Ask the user if they approve modifying '{filename}'. If they say yes, call approve_action('{action_id}')."

def run_shell_command(command: str) -> str:
    """
    Proposes executing a shell command on the local machine.
    THIS DOES NOT EXECUTE IMMEDIATELY. It returns an action_id.
    You MUST explicitly ask the user: "Do you approve running the command: `[command]`?".
    If they say yes, use approve_action.
    """
    action_id = f"shell_{int(datetime.now().timestamp())}"
    pending_actions[action_id] = {
        'type': 'shell_command',
        'command': command
    }
    return f"ACTION PAUSED: CRITICAL SECURITY CHECK. You MUST ask the user: 'Do you approve running the command: `{command}` ?'. If they say yes, call approve_action('{action_id}')."

def send_phd_email(to_address: str, subject: str, body: str) -> str:
    """
    Proposes sending an email from the user's CentraleSupelec PhD account.
    THIS DOES NOT EXECUTE IMMEDIATELY. It returns an action_id.
    You MUST explicitly ask the user: "Do you approve sending this email to [to_address] with subject [subject]?".
    If they say yes, use approve_action.
    
    Args:
        to_address: The recipient's email address.
        subject: The subject line.
        body: The plain text body of the email.
    """
    action_id = f"email_{int(datetime.now().timestamp())}"
    pending_actions[action_id] = {
        'type': 'send_email',
        'to_address': to_address,
        'subject': subject,
        'body': body
    }
    return f"ACTION PAUSED: CRITICAL SECURITY CHECK. Ask the user if they approve sending the email to '{to_address}'. If yes, call approve_action('{action_id}')."

# --- UNMODIFIED TOOLS (Safe to run without asking) ---

def log_to_journal(entry: str) -> str:
    """
    Autonomously appends a note to 'batbot.md' (the agent's personal journal).
    Use this to remember user preferences, acronyms, project context, or useful facts for the future.
    This tool DOES NOT require user approval.
    
    Args:
        entry: The markdown-formatted text to append to the journal.
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        formatted_entry = f"\n### [{timestamp}]\n{entry}\n"
        with open("batbot.md", "a", encoding="utf-8") as f:
            f.write(formatted_entry)
        return "Successfully logged entry to batbot.md."
    except Exception as e:
        return f"Error logging to journal: {str(e)}"

def read_journal() -> str:
    """
    Reads the contents of 'batbot.md' to recall past context, preferences, or acronyms you previously saved.
    """
    try:
        if not os.path.exists("batbot.md"):
            return "Journal is currently empty."
        with open("batbot.md", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading journal: {str(e)}"

def read_phd_emails(count: int = 5) -> str:
    """
    Reads the latest UNREAD emails from the user's CentraleSupelec PhD inbox.
    
    Args:
        count: The maximum number of unread emails to retrieve (default 5).
        
    Returns:
        A formatted string of the latest unread emails (Sender, Subject, and Body).
    """
    return email_manager.read_latest_emails(count)

def search_phd_emails(query: str, count: int = 5) -> str:
    """
    Searches the user's CentraleSupelec PhD inbox for specific emails based on a query.
    
    Args:
        query: An IMAP search string. Use formatting like 'FROM "name@domain.com"', 'SUBJECT "meeting"', or 'BODY "urgent"'. You can combine them, e.g., 'FROM "boss@x.com" SUBJECT "update"'.
        count: The maximum number of matching emails to retrieve (default 5).
        
    Returns:
        A formatted string of the matching emails.
    """
    return email_manager.search_emails(query, count)

def read_file(filename: str) -> str:
    """Reads the content of a file."""
    try:
        if not os.path.exists(filename):
            return f"Error: File '{filename}' not found."
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def get_current_time() -> str:
    """Returns the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def ingest_knowledge_base() -> str:
    """Scans and ingests PDFs into the RAG database."""
    return rag_manager.ingest_pdfs()

def search_knowledge_base(query: str) -> str:
    """Searches the local RAG database."""
    return rag_manager.query_knowledge(query)

def fetch_webpage_text(url: str) -> str:
    """Downloads a webpage and extracts its text."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style", "header", "footer", "nav"]):
            script.decompose()
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        return f"Error fetching webpage '{url}': {str(e)}"

def download_pdf_from_url(url: str, filename: Optional[str] = None) -> str:
    """Downloads a PDF to the knowledge base."""
    try:
        if not filename:
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename.lower().endswith('.pdf'):
                filename = "downloaded_paper.pdf"
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
            
        os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
        file_path = os.path.join(KNOWLEDGE_BASE_DIR, filename)
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
            
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return f"Successfully downloaded PDF to '{file_path}'."
    except Exception as e:
        return f"Error downloading PDF: {str(e)}"

def search_arxiv(query: str, max_results: int = 5) -> str:
    """Searches ArXiv for papers."""
    try:
        client = arxiv.Client()
        search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
        results = []
        for result in client.results(search):
            authors = ", ".join([author.name for author in result.authors])
            results.append(f"Title: {result.title}\nAuthors: {authors}\nPDF Link: {result.pdf_url}\nSummary: {result.summary}\n")
        return "\n--- PAPER ---\n".join(results) if results else "No papers found."
    except Exception as e:
        return f"Error searching ArXiv: {str(e)}"

def search_ieee(query: str, max_results: int = 5) -> str:
    """Searches IEEE Xplore for papers."""
    api_key = os.getenv("IEEE_API_KEY")
    if not api_key: return "Error: IEEE_API_KEY is not set."
    try:
        xplore = XPLORE(api_key)
        xplore.queryText(query)
        xplore.maximumResults(max_results)
        data = json.loads(xplore.callAPI())
        articles = data.get("articles", [])
        output = [f"ID: {art.get('article_number')}\nTitle: {art.get('title')}\nAccess: {art.get('access_type')}" for art in articles]
        return "\n--- IEEE RESULTS ---\n".join(output) if output else "No papers found."
    except Exception as e:
        return f"Error searching IEEE: {str(e)}"

def get_ieee_full_text(article_number: str) -> str:
    """Retrieves full text of an IEEE paper."""
    api_key = os.getenv("IEEE_API_KEY")
    auth_token = os.getenv("IEEE_AUTH_TOKEN")
    if not api_key: return "Error: IEEE_API_KEY is not set."
    try:
        xplore = XPLORE(api_key)
        xplore.articleNumber(article_number)
        meta_data = json.loads(xplore.callAPI())
        articles = meta_data.get("articles", [])
        if not articles: return "Error: Could not find metadata."
        
        is_open_access = articles[0].get("access_type") == "Open Access"
        xplore = XPLORE(api_key)
        
        if is_open_access:
            xplore.openAccess(article_number)
        else:
            if not auth_token: return "Paper is not Open Access. IEEE_AUTH_TOKEN required."
            xplore.setAuthToken(auth_token)
            xplore.fullTextRequest(article_number)
            
        full_text_raw = xplore.callAPI()
        try:
            return json.loads(full_text_raw).get("text", full_text_raw)
        except:
            return full_text_raw
    except Exception as e:
        return f"Error retrieving IEEE text: {str(e)}"
