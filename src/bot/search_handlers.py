from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes
from ..storage import storage_manager
from ..odoo_client import odoo_client
from ..crypto import crypto_manager
from ..parser import parse_query
from ..config import logger, ODOO_URL
import hashlib
import json

STATE_ICONS = {
    'draft': '⚪',
    'to_approve': '🟡',
    'approved': '🟢',
    'rejected': '🔴',
    'done': '🏁'
}

import html

def format_pr_list(prs):
    """Format list of PRs for display."""
    lines = []
    for pr in prs:
        ref = html.escape(str(pr.get('name', 'N/A')))
        state = pr.get('state', 'unknown')
        icon = STATE_ICONS.get(state, '❓')
        
        req_val = pr.get('requested_by')
        requester = req_val[1] if isinstance(req_val, list) else str(req_val)
        requester = html.escape(requester)
        
        # partner_id removed
        
        date = pr.get('date_start', 'N/A')
        cost = pr.get('estimated_cost', 0.0)
        
        line = (
             f"<b>{ref}</b> | {icon} {html.escape(state.title())}\n"
             f"👤 {requester}\n"
             f"📅 {date}\n"
             f"💰 {cost}\n"
             f"/view_{pr['id']} <i>View Details</i>\n"
             "-------------------"
        )
        lines.append(line)
    return "\n".join(lines)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /find command."""
    query_text = " ".join(context.args) if context.args else ""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Shared Mode: No session check
    # session = storage_manager.get_session(chat_id)
    # if not session: ...
    
    # Lazy authenticate if needed (or cache UID somewhere)
    # For now, we'll authenticate every time or rely on client holding cookie? 
    # XMLRPC is stateless usually unless we use session.
    # Let's get the UID for the service user.
    from ..config import ODOO_DB, ODOO_EMAIL, ODOO_PASSWORD
    
    try:
        # Authenticate system user
        uid = odoo_client.authenticate(ODOO_DB, ODOO_EMAIL, ODOO_PASSWORD)
    except Exception as e:
        logger.error(f"Auth failed: {e}")
        await update.message.reply_text("❌ System Authentication Failed.")
        return

    # If query is empty, allow it -> parse_query returns empty domain -> Odoo returns latest 5
    if not query_text:
        # Pass
        pass

    # Parse query
    parsed = parse_query(query_text)
    domain = parsed['domain']
    
    try:
        # Perform search
        offset = 0
        limit = 5
        prs = odoo_client.search_prs(
            ODOO_DB, 
            uid, 
            ODOO_PASSWORD, 
            domain, 
            offset=offset, 
            limit=limit
        )
        
        if not prs:
            if query_text:
                await update.message.reply_text(f"🔍 No results found for '{query_text}'.")
            else:
                 await update.message.reply_text(f"🔍 No Purchase Requests found.")
            return

        # Cache context for pagination
        query_hash = hashlib.md5(query_text.encode()).hexdigest()
        cache_data = {
            'query_text': query_text,
            'domain': json.dumps(domain) if type(domain) is list else domain,
            'timestamp': str(update.message.date)
        }
        storage_manager.cache_search_results(query_hash, cache_data) 

        if query_text:
            msg_text = f"🔎 Found PRs for: \"{query_text}\"\n\n" + format_pr_list(prs)
        else:
            msg_text = f"🔎 Latest 5 Purchase Requests:\n\n" + format_pr_list(prs)
        
        # Pagination Buttons
        # Only show Next if we have 5 results (assumption)
        buttons = []
        if len(prs) == limit:
            buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"page:{query_hash}:{offset+limit}"))
        
        reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

        await update.message.reply_text(msg_text, parse_mode=constants.ParseMode.HTML, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Search failed: {e}")
        await update.message.reply_text("❌ An error occurred while searching.")

async def pagination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Next/Prev buttons."""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(':')
    if data[0] != 'page':
        return
        
    query_hash = data[1]
    offset = int(data[2])
    chat_id = update.effective_chat.id
    
    cached_search = storage_manager.get_cached_search(query_hash)
    
    if not cached_search:
        await query.edit_message_text("Search expired. Please search again.")
        return

    from ..config import ODOO_DB, ODOO_EMAIL, ODOO_PASSWORD
    uid = odoo_client.authenticate(ODOO_DB, ODOO_EMAIL, ODOO_PASSWORD)

    # Check if domainStr is string or list (redis stores as string if we dumped it)
    domainStr = cached_search['domain']
    domain = json.loads(domainStr) if isinstance(domainStr, str) else domainStr
    
    limit = 5
    prs = odoo_client.search_prs(
        ODOO_DB, 
        uid, 
        ODOO_PASSWORD, 
        domain, 
        offset=offset, 
        limit=limit
    )
    
    if not prs:
        await query.edit_message_text(f"No more results.")
        return
        
    msg_text = f"🔎 Found PRs for: \"{cached_search['query_text']}\" (Page {offset//limit + 1})\n\n" + format_pr_list(prs)
    
    # Pagination logic
    buttons = []
    if offset >= limit:
        buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"page:{query_hash}:{offset-limit}"))
    if len(prs) == limit:
        buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"page:{query_hash}:{offset+limit}"))
        
    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None
    
    await query.edit_message_text(msg_text, parse_mode=constants.ParseMode.HTML, reply_markup=reply_markup)

async def view_pr_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /view_<id> command."""
    command = update.message.text
    try:
        # Expected format: /view_123 or /view_123@BotName
        parts = command.split('_')
        if len(parts) < 2:
            return
        # Extract ID, ignoring @botname if present
        pr_id_str = parts[1].split('@')[0]
        pr_id = int(pr_id_str)
    except (IndexError, ValueError) as e:
        logger.warning(f"Invalid view command: {command} - {e}")
        await update.message.reply_text("Invalid command.")
        return

    user = update.effective_user
    # chat_id = update.effective_chat.id
    
    # Shared Mode
    from ..config import ODOO_DB, ODOO_EMAIL, ODOO_PASSWORD
    uid = odoo_client.authenticate(ODOO_DB, ODOO_EMAIL, ODOO_PASSWORD)
    
    try:
        pr = odoo_client.get_pr_details(
            ODOO_DB, uid, ODOO_PASSWORD, pr_id
        )
        
        if not pr:
            await update.message.reply_text("PR not found or access denied.")
            return
            
        state = pr.get('state', 'unknown')
        state_icon = STATE_ICONS.get(state, '❓')
        
        # Safe getter for many2one
        def m2o_name(field):
            val = pr.get(field)
            if isinstance(val, list) and len(val) > 1:
                return html.escape(val[1])
            return val or 'Unspecified'

        # Format Line Items
        lines_text = ""
        if pr.get('lines'):
            lines_text += "\n📦 <b>Items:</b>\n"
            for line in pr['lines']:
                prod_name = line.get('name') or "Unknown Product"
                qty = line.get('product_qty', 0)
                cost = line.get('estimated_cost', 0.0)
                lines_text += f"• {html.escape(prod_name)} (Qty: {qty}) - {cost}\n"
        else:
            lines_text += "\n📦 <b>Items:</b> None\n"

        text = (
            f"<b>{html.escape(pr.get('name', 'PR'))}</b> {state_icon}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Requester:</b> {m2o_name('requested_by')}\n"
            f"👨‍💼 <b>Head/Approver:</b> {m2o_name('assigned_to')}\n"
            f"📊 <b>Status:</b> {html.escape(state.title())}\n"
            f"📅 <b>Date:</b> {pr.get('date_start', 'N/A')}\n"
            f"💰 <b>Total Cost:</b> {pr.get('estimated_cost', 0)}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 <b>Description:</b>\n{html.escape(str(pr.get('description') or 'No description'))}\n"
            f"{lines_text}"
            f"━━━━━━━━━━━━━━━━━━\n"
        )
        
        odoo_link = f"{ODOO_URL}/web#id={pr['id']}&model=purchase.request&view_type=form"
        keyboard = [[InlineKeyboardButton("🌐 View in Odoo", url=odoo_link)]]
        
        await update.message.reply_text(
            text, 
            parse_mode=constants.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"View PR error: {e}")
        await update.message.reply_text("An error occurred.")
