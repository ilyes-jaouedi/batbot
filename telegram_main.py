import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

from agent.root_agent import create_root_agent
from runner.app_runner import run_interaction
from runner.local_session_service import LocalPickleSessionService
from agent.audio_transcriber import local_transcriber

# Configure basic logging for the local terminal
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", 0))
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "BatbotSecure2026")

# Track which users have successfully entered the password in this server session
authenticated_users = set()

# Initialize the ADK agent and the Persistent Session Service once
adk_agent = create_root_agent()
session_service = LocalPickleSessionService()

async def send_long_message(update: Update, text: str):
    """Sends a message, splitting it into chunks if it exceeds Telegram's limit."""
    max_length = 4000 # Safe limit below Telegram's 4096
    
    if len(text) <= max_length:
        try:
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(text) # Fallback if markdown parsing fails
        return
        
    # Split by paragraphs if possible to avoid breaking markdown formatting mid-sentence
    paragraphs = text.split('\n\n')
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_length:
            # Send the current chunk and start a new one
            if current_chunk:
                try:
                    await update.message.reply_text(current_chunk.strip(), parse_mode="Markdown")
                except Exception:
                    await update.message.reply_text(current_chunk.strip())
            current_chunk = para + "\n\n"
        else:
            current_chunk += para + "\n\n"
            
    # Send any remaining text
    if current_chunk.strip():
        try:
            await update.message.reply_text(current_chunk.strip(), parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(current_chunk.strip())


async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processes incoming messages (Text and Voice).
    Checks whitelist, password, transcribes audio if needed, and runs the ADK agent.
    """
    user_id = update.effective_user.id
    
    # --- 1. SECURITY CHECK (ID WHITELIST) ---
    if user_id != ALLOWED_USER_ID:
        logging.warning(f"Blocked unauthorized access attempt from User ID: {user_id}")
        return
        
    is_voice = bool(update.message.voice)
    user_input = update.message.text or ""
    
    # --- 2. PASSWORD AUTHENTICATION CHECK ---
    if user_id not in authenticated_users:
        if is_voice:
            await update.message.reply_text("🔒 Batbot is locked. Please TYPE the password to proceed. (Voice passwords not accepted).")
            return
            
        if user_input.strip() == BOT_PASSWORD:
            authenticated_users.add(user_id)
            await update.message.reply_text("✅ Access Granted. Welcome back, Ilyes. Batbot is ready. (Type /lock to secure the session later).")
            logging.info(f"User {user_id} successfully authenticated with password.")
        else:
            await update.message.reply_text("🔒 Batbot is locked. Please enter the password to proceed.")
            logging.warning(f"User {user_id} failed password authentication.")
        return

    # --- 3. MANUAL LOCK COMMAND ---
    if user_input.strip().lower() == "/lock":
        authenticated_users.discard(user_id)
        await update.message.reply_text("🔒 Session locked. Batbot is now asleep.")
        logging.info(f"User {user_id} manually locked the session.")
        return
        
    # --- 4. HANDLE VOICE MESSAGES ---
    if is_voice:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        try:
            voice_file = await context.bot.get_file(update.message.voice.file_id)
            os.makedirs("sandbox", exist_ok=True)
            local_path = os.path.join("sandbox", f"voice_memo_{user_id}.ogg")
            
            # Download from Telegram
            await voice_file.download_to_drive(local_path)
            
            # Transcribe locally with open-source Whisper
            user_input = await asyncio.to_thread(local_transcriber.transcribe, local_path)
            
            await send_long_message(update, f"🎙️ *Transcription:*\n_{user_input}_")
            
            # If transcription failed, don't pass it to the agent
            if user_input.startswith("Error during local transcription"):
                return
                
        except Exception as e:
            logging.error(f"Voice processing failed: {e}")
            await update.message.reply_text(f"❌ Failed to process audio: {e}")
            return
            
    if not user_input.strip():
        return
    
    # --- 5. RUN ADK AGENT ---
    logging.info(f"Passing to Agent: {user_input}")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    try:
        response_text = await run_interaction(adk_agent, session_service, str(user_id), user_input)

        if not response_text:
            response_text = "Task completed, but the agent returned an empty response."
            
        await send_long_message(update, response_text)
        
    except Exception as e:
        error_msg = f"An error occurred while running the agent: {str(e)}"
        logging.error(error_msg)
        await send_long_message(update, error_msg)

def main():
    if not TOKEN or not ALLOWED_USER_ID:
        logging.error("Missing TELEGRAM_BOT_TOKEN or ALLOWED_USER_ID in .env file.")
        return
        
    logging.info("Initializing Local Whisper Model (this may take a moment to download on the first run)...")
    local_transcriber.load_model()
        
    # Build the Telegram Application
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Add a handler to listen to TEXT and VOICE messages
    app.add_handler(MessageHandler(filters.TEXT | filters.VOICE, handle_telegram_message))
    
    logging.info("==================================================")
    logging.info(" Secure Telegram Bot is STARTING...")
    logging.info(f" Authorized to serve ONLY User ID: {ALLOWED_USER_ID}")
    logging.info(" Waiting for messages... Press Ctrl+C to stop.")
    logging.info("==================================================")
    
    # Start long-polling
    app.run_polling()

if __name__ == "__main__":
    main()
