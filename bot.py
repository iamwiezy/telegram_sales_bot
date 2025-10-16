"""
Anonymous Dealer-Sales Telegram Bot
Facilitates anonymous communication between sales team and dealers
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import sqlite3
from datetime import datetime

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
# IMPORTANT: Replace these values with your actual credentials
BOT_TOKEN = "8414966602:AAGOtohqTO2qCIFBUf_1fQYF7aZkFIQaLsI"  # Get from @BotFather
ADMIN_ID = 7554149934  # Get from @userinfobot - replace with your Telegram ID number
# ======================================================

# Conversation states
ROLE_SELECTION, NAME_INPUT = range(2)

# ==================== DATABASE FUNCTIONS ====================
def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            paired_with INTEGER,
            active INTEGER DEFAULT 1,
            registered_date TEXT
        )
    ''')
    
    # Create messages table for history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            message_text TEXT,
            sent_time TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

def add_new_user(telegram_id: int, name: str, role: str):
    """Add a new user to the database"""
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (telegram_id, name, role, registered_date)
        VALUES (?, ?, ?, ?)
    ''', (telegram_id, name, role, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    logger.info(f"User added: {name} ({role})")

def find_user(telegram_id: int):
    """Find user by telegram ID"""
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def find_partner(telegram_id: int):
    """Find paired partner for a user"""
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT paired_with FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (result[0],))
        partner = cursor.fetchone()
        conn.close()
        return partner
    
    conn.close()
    return None

def create_pair(user1_id: int, user2_id: int):
    """Pair two users together"""
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET paired_with = ? WHERE telegram_id = ?', (user2_id, user1_id))
    cursor.execute('UPDATE users SET paired_with = ? WHERE telegram_id = ?', (user1_id, user2_id))
    conn.commit()
    conn.close()
    logger.info(f"Users paired: {user1_id} <-> {user2_id}")

def save_message(sender: int, receiver: int, text: str):
    """Save message to database"""
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (sender_id, receiver_id, message_text, sent_time)
        VALUES (?, ?, ?, ?)
    ''', (sender, receiver, text, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def get_all_users():
    """Get all registered users"""
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY registered_date DESC')
    users = cursor.fetchall()
    conn.close()
    return users

# ==================== BOT HANDLERS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    existing_user = find_user(user_id)
    
    if existing_user:
        # User already registered
        name, role = existing_user[1], existing_user[2]
        await update.message.reply_text(
            f"👋 Welcome back, {name}!\n\n"
            f"Your Role: {role}\n\n"
            "You can send messages anytime. Use /status to check your pairing.\n\n"
            "Commands:\n"
            "/status - Check pairing status\n"
            "/help - View help"
        )
        return ConversationHandler.END
    
    # New user - start registration
    keyboard = [['Sales Team', 'Dealer']]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "🤖 Welcome to Anonymous Communication Bot!\n\n"
        "This bot allows secure, anonymous messaging between sales team and dealers.\n\n"
        "👇 Please select your role:",
        reply_markup=markup
    )
    return ROLE_SELECTION

async def role_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle role selection"""
    selected_role = update.message.text
    
    if selected_role not in ['Sales Team', 'Dealer']:
        await update.message.reply_text("❌ Please select a valid role using the buttons.")
        return ROLE_SELECTION
    
    context.user_data['role'] = selected_role
    
    await update.message.reply_text(
        f"✅ Role selected: {selected_role}\n\n"
        "📝 Please enter your full name:",
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME_INPUT

async def name_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle name input and complete registration"""
    user_name = update.message.text.strip()
    user_role = context.user_data['role']
    user_id = update.effective_user.id
    
    if len(user_name) < 2:
        await update.message.reply_text("❌ Please enter a valid name (at least 2 characters).")
        return NAME_INPUT
    
    # Save user to database
    add_new_user(user_id, user_name, user_role)
    
    await update.message.reply_text(
        f"✅ Registration Successful!\n\n"
        f"👤 Name: {user_name}\n"
        f"🎭 Role: {user_role}\n"
        f"🆔 Your ID: {user_id}\n\n"
        "⏳ You'll be paired with a partner by the admin soon.\n"
        "You'll receive a notification when pairing is complete.\n\n"
        "Use /status to check your pairing status anytime."
    )
    
    # Notify admin
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆕 NEW USER REGISTERED\n\n"
                 f"👤 Name: {user_name}\n"
                 f"🎭 Role: {user_role}\n"
                 f"🆔 Telegram ID: {user_id}\n"
                 f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                 f"💡 Use /pair {user_id} <partner_id> to pair this user."
        )
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")
    
    return ConversationHandler.END

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel registration process"""
    await update.message.reply_text(
        "❌ Registration cancelled.\n\nUse /start to register again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's current status"""
    user_id = update.effective_user.id
    user = find_user(user_id)
    
    if not user:
        await update.message.reply_text(
            "❌ You're not registered yet.\n\nUse /start to register."
        )
        return
    
    partner = find_partner(user_id)
    
    status_msg = f"📊 YOUR STATUS\n\n"
    status_msg += f"👤 Name: {user[1]}\n"
    status_msg += f"🎭 Role: {user[2]}\n"
    status_msg += f"🆔 Your ID: {user_id}\n\n"
    
    if partner:
        status_msg += f"✅ Status: PAIRED\n"
        status_msg += f"👥 Paired with: {partner[2]}\n\n"
        status_msg += "You can send messages now. They will be forwarded anonymously."
    else:
        status_msg += f"⏳ Status: WAITING FOR PAIRING\n\n"
        status_msg += "An admin will pair you with a partner soon."
    
    await update.message.reply_text(status_msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information"""
    help_text = (
        "🤖 BOT COMMANDS\n\n"
        "👤 User Commands:\n"
        "/start - Register or view welcome message\n"
        "/status - Check your pairing status\n"
        "/help - Show this help message\n\n"
        "📖 HOW IT WORKS:\n"
        "1️⃣ Register with your role (Sales/Dealer)\n"
        "2️⃣ Admin pairs you with a partner\n"
        "3️⃣ Send messages normally - they're forwarded anonymously\n"
        "4️⃣ Your identity remains hidden from your partner\n\n"
        "💬 SENDING MESSAGES:\n"
        "Once paired, just type your message normally.\n"
        "The bot will forward it to your partner without revealing your identity.\n\n"
        "❓ Need assistance? Contact the administrator."
    )
    await update.message.reply_text(help_text)

# ==================== ADMIN COMMANDS ====================

async def admin_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to pair two users"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ This command is only available to admins.")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Invalid format.\n\n"
            "Usage: /pair <user1_id> <user2_id>\n"
            "Example: /pair 123456789 987654321\n\n"
            "Tip: Use /list to see all registered users and their IDs."
        )
        return
    
    try:
        user1_id = int(context.args[0])
        user2_id = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ User IDs must be numbers.")
        return
    
    user1 = find_user(user1_id)
    user2 = find_user(user2_id)
    
    if not user1 or not user2:
        await update.message.reply_text(
            "❌ One or both users not found.\n\n"
            "Use /list to see all registered users."
        )
        return
    
    # Create pairing
    create_pair(user1_id, user2_id)
    
    await update.message.reply_text(
        f"✅ PAIRING SUCCESSFUL!\n\n"
        f"User 1: {user1[1]} ({user1[2]}) - ID: {user1_id}\n"
        f"User 2: {user2[1]} ({user2[2]}) - ID: {user2_id}\n\n"
        f"Both users have been notified."
    )
    
    # Notify both users
    try:
        await context.bot.send_message(
            user1_id,
            f"✅ PAIRING COMPLETE!\n\n"
            f"You've been paired with a {user2[2]}.\n"
            f"You can now send messages - they'll be forwarded anonymously.\n\n"
            f"Just type your message normally!"
        )
        await context.bot.send_message(
            user2_id,
            f"✅ PAIRING COMPLETE!\n\n"
            f"You've been paired with a {user1[2]}.\n"
            f"You can now send messages - they'll be forwarded anonymously.\n\n"
            f"Just type your message normally!"
        )
    except Exception as e:
        logger.error(f"Failed to notify users: {e}")

async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to list all users"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ This command is only available to admins.")
        return
    
    users = get_all_users()
    
    if not users:
        await update.message.reply_text("📭 No users registered yet.")
        return
    
    message = "👥 REGISTERED USERS\n\n"
    
    for user in users:
        paired_status = "✅ Paired" if user[3] else "⏳ Unpaired"
        message += f"• {user[1]}\n"
        message += f"  Role: {user[2]}\n"
        message += f"  ID: {user[0]}\n"
        message += f"  Status: {paired_status}\n"
        if user[3]:
            partner = find_user(user[3])
            if partner:
                message += f"  Partner: {partner[1]}\n"
        message += "\n"
    
    message += f"Total Users: {len(users)}"
    
    await update.message.reply_text(message)

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to broadcast message to all users"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ This command is only available to admins.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a message.\n\n"
            "Usage: /broadcast <your message>\n"
            "Example: /broadcast System maintenance tonight at 10 PM"
        )
        return
    
    broadcast_msg = " ".join(context.args)
    users = get_all_users()
    success_count = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                user[0],
                f"📢 ANNOUNCEMENT\n\n{broadcast_msg}"
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {user[0]}: {e}")
    
    await update.message.reply_text(
        f"✅ Broadcast sent to {success_count}/{len(users)} users."
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to show statistics"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ This command is only available to admins.")
        return
    
    users = get_all_users()
    total = len(users)
    paired = sum(1 for u in users if u[3] is not None)
    unpaired = total - paired
    
    sales = sum(1 for u in users if u[2] == 'Sales Team')
    dealers = sum(1 for u in users if u[2] == 'Dealer')
    
    stats_msg = (
        f"📊 BOT STATISTICS\n\n"
        f"👥 Total Users: {total}\n"
        f"✅ Paired: {paired}\n"
        f"⏳ Unpaired: {unpaired}\n\n"
        f"🎭 BY ROLE:\n"
        f"Sales Team: {sales}\n"
        f"Dealers: {dealers}"
    )
    
    await update.message.reply_text(stats_msg)

# ==================== MESSAGE ROUTING ====================

async def route_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route messages between paired users"""
    sender_id = update.effective_user.id
    sender = find_user(sender_id)
    
    if not sender:
        await update.message.reply_text(
            "❌ You're not registered.\n\n"
            "Use /start to register first."
        )
        return
    
    partner = find_partner(sender_id)
    
    if not partner:
        await update.message.reply_text(
            "⏳ You're not paired yet.\n\n"
            "Please wait for an admin to pair you with a partner.\n"
            "Use /status to check your pairing status."
        )
        return
    
    message_text = update.message.text
    
    # Send to partner
    try:
        # Generate anonymous sender ID (last 4 digits)
        anon_id = str(sender_id)[-4:]
        
        await context.bot.send_message(
            partner[0],
            f"💬 Message from {sender[2]} #{anon_id}\n\n{message_text}"
        )
        
        # Save message
        save_message(sender_id, partner[0], message_text)
        
        # Notify admin (monitoring)
        await context.bot.send_message(
            ADMIN_ID,
            f"📨 MESSAGE LOG\n\n"
            f"From: {sender[1]} ({sender[2]})\n"
            f"To: {partner[1]} ({partner[2]})\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"Message:\n{message_text}"
        )
        
        await update.message.reply_text("✅ Message sent successfully!")
        
    except Exception as e:
        logger.error(f"Message routing error: {e}")
        await update.message.reply_text(
            "❌ Failed to send message.\n\n"
            "Please try again or contact admin."
        )

# ==================== MAIN FUNCTION ====================

def main():
    """Start the bot"""
    print("🚀 Initializing bot...")
    
    # Initialize database
    init_database()
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Registration conversation handler
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            ROLE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, role_selected)],
            NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_entered)],
        },
        fallbacks=[CommandHandler('cancel', cancel_registration)],
    )
    
    # Add handlers
    app.add_handler(registration_handler)
    app.add_handler(CommandHandler('status', status_command))
    app.add_handler(CommandHandler('help', help_command))
    
    # Admin handlers
    app.add_handler(CommandHandler('pair', admin_pair))
    app.add_handler(CommandHandler('list', admin_list))
    app.add_handler(CommandHandler('broadcast', admin_broadcast))
    app.add_handler(CommandHandler('stats', admin_stats))
    
    # Message routing
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_message))
    
    # Start polling
    print("✅ Bot is running!")
    print(f"👤 Admin ID: {ADMIN_ID}")
    print("Press Ctrl+C to stop")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()