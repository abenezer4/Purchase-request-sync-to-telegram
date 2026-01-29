from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from ..storage import storage_manager
from ..odoo_client import odoo_client
from ..crypto import crypto_manager
from ..config import ODOO_DB
import os

# States for ConversationHandler
EMAIL, PASSWORD = range(2)

from telegram import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: Greeting with Web App button."""
    user = update.effective_user
    
    # URL for the Mini App (Served by FastAPI)
    # Since we are running on standard port 8000 exposed via ngrok or similar for HTTPS
    # Or just generic localhost for Desktop testing.
    # Ideally USER sets a PUBLIC_URL env var. If not, we guess or ask.
    # For now, let's assume the user will need to configure the full URL in .env
    # But for local dev (desktop), localhost works. 
    # NOTE: Mini Apps require HTTPS! User MUST tunnel.  
    
    # We will look for APP_URL in env, default to example.
    webapp_url = os.getenv("APP_URL", "https://your-public-url.com")

    # Telegram STRICTLY requires HTTPS for WebAppInfo.
    if webapp_url.startswith("https://"):
        # Valid HTTPS -> Use Mini App Button
        keyboard = [
            [KeyboardButton("🚀 Open App", web_app=WebAppInfo(url=webapp_url))]
        ]
        await update.message.reply_text(
            f"Welcome back, {user.first_name}! 👋\n\n"
            "Tap the button below to open the Odoo Requests App. 📱",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    else:
        # HTTP/Localhost -> Send Link in Text (Buttons don't support HTTP)
        await update.message.reply_text(
            f"Welcome back, {user.first_name}! 👋\n\n"
            "⚠️ **Localhost Mode**\n"
            "Telegram buttons only work with HTTPS.\n\n"
            f"🔗 [Open App in Browser]({webapp_url})",
            parse_mode='Markdown'
        )
    return ConversationHandler.END

async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store email and ask for password."""
    email = update.message.text.strip()
    context.user_data['odoo_email'] = email
    
    await update.message.reply_text(
        "✅ Got it.\n\n"
        "🔑 Now, please enter your **Odoo password** or **API key**:\n"
        "_(This will be encrypted and stored securely)_",
        parse_mode='Markdown'
    )
    return PASSWORD

async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Authenticate with Odoo and store session."""
    password = update.message.text.strip()
    email = context.user_data.get('odoo_email')
    chat_id = update.effective_chat.id
    
    db_name = ODOO_DB

    processing_msg = await update.message.reply_text("🔄 Authenticating with Odoo...")
    
    uid = odoo_client.authenticate(db_name, email, password)
    
    if uid:
        encrypted_pass = crypto_manager.encrypt(password)
        session_data = {
            'odoo_uid': uid,
            'odoo_db': db_name,
            'odoo_email': email,
            'encrypted_token': encrypted_pass,
        }
        storage_manager.save_session(chat_id, session_data)
        
        await processing_msg.edit_text(
            "✅ Connected! You can now search PRs with /find.\n\n"
            "Try:\n"
            "`/find laptop`\n"
            "`/pending`\n"
            "`/myrequests`",
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await processing_msg.edit_text(
            "❌ Authentication failed.\n"
            "Please check your email and password/API key."
        )
        return ConversationHandler.END

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear session."""
    chat_id = update.effective_chat.id
    storage_manager.clear_session(chat_id)
    await update.message.reply_text("🔒 Logged out successfully. See you soon!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help."""
    text = (
        "🤖 **Odoo PR Bot Commands**\n\n"
        "🔎 **Search & View**:\n"
        "`/find <query>` - Search PRs\n"
        "`/view <PR-ref>` - View details\n"
        "`/pending` - Show pending\n"
        "`/approved` - Show approved\n"
        "`/myrequests` - Your PRs\n\n"
        "⚙️ **Account**:\n"
        "`/login` - Reconnect\n"
        "`/logout` - Sign out\n"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Process canceled.")
    return ConversationHandler.END
