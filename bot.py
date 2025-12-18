import logging
import json
import os
import pytz
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from datetime import datetime, timedelta, time
from uuid import uuid4
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="telegram.ext._application")

# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone
TBILISI_TZ = pytz.timezone("Asia/Tbilisi")

# File paths
DATA_FILE = os.path.join(os.path.dirname(__file__), "reminders.json")

# Default group ID for "To Group" option
DEFAULT_GROUP_ID = -1003342043555

# Conversation states
(FREQUENCY, TIME, MESSAGE, MULTI_MSG, DESTINATION, DESTINATION_ID, 
 ATTACHMENT, REPEAT_UNTIL, CUSTOM_DAYS,
 EDIT_SELECT, EDIT_FIELD, EDIT_VALUE,
 DELETE_SELECT, USERNAME_INPUT,
 HOURLY_START, HOURLY_END, HOURLY_DAYS) = range(17)

# ==================== DATA PERSISTENCE ====================

def load_reminders() -> dict:
    """Load reminders from JSON file."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_reminders(data: dict):
    """Save reminders to JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

def add_reminder(reminder: dict) -> str:
    """Add a reminder and return its ID."""
    data = load_reminders()
    reminder_id = str(uuid4())[:8]
    reminder["id"] = reminder_id
    reminder["created_at"] = datetime.now(TBILISI_TZ).isoformat()
    reminder["completed"] = False
    data[reminder_id] = reminder
    save_reminders(data)
    return reminder_id

def get_user_reminders(user_id: int) -> list:
    """Get all reminders for a user."""
    data = load_reminders()
    return [r for r in data.values() if r.get("user_id") == user_id and not r.get("completed")]

def delete_reminder(reminder_id: str) -> bool:
    """Delete a reminder by ID."""
    data = load_reminders()
    if reminder_id in data:
        del data[reminder_id]
        save_reminders(data)
        return True
    return False

def update_reminder(reminder_id: str, updates: dict) -> bool:
    """Update a reminder."""
    data = load_reminders()
    if reminder_id in data:
        data[reminder_id].update(updates)
        save_reminders(data)
        return True
    return False

def mark_completed(reminder_id: str):
    """Mark reminder as completed."""
    update_reminder(reminder_id, {"completed": True})

# ==================== BOT COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message."""
    await update.message.reply_text(
        "👋 Hello! I am a Reminder Bot.\n\n"
        "📌 Commands:\n"
        "/newreminder - Create a reminder\n"
        "/listreminders - View your reminders\n"
        "/editreminder - Edit a reminder\n"
        "/deletereminder - Delete a reminder\n"
        "/getid - Get current chat ID\n"
        "/cancel - Cancel current operation"
    )

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get chat ID."""
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Private Chat"
    await update.message.reply_text(f"Chat ID: `{chat_id}`\nTitle: {chat_title}", parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel operation."""
    context.user_data.clear()
    await update.message.reply_text("❌ Operation cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ==================== NEW REMINDER FLOW ====================

async def new_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start new reminder creation."""
    context.user_data.clear()
    reply_keyboard = [["Daily", "One-time"], ["Weekly", "Custom Days"], ["Hourly Range"]]
    await update.message.reply_text(
        "📅 How often should I remind you?\n\n"
        "• Hourly Range: Every hour in a time range",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return FREQUENCY

async def frequency_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle frequency selection."""
    freq = update.message.text
    context.user_data["frequency"] = freq
    
    if freq == "Custom Days":
        await update.message.reply_text(
            "📆 Enter days (comma-separated):\n"
            "Example: Mon,Wed,Fri or 1,3,5 (1=Monday)",
            reply_markup=ReplyKeyboardRemove()
        )
        return CUSTOM_DAYS
    
    if freq == "Hourly Range":
        await update.message.reply_text(
            "🕐 Enter START time (HH:MM):\n"
            "Example: 17:00",
            reply_markup=ReplyKeyboardRemove()
        )
        return HOURLY_START
    
    await update.message.reply_text(
        "⏰ What time? (Format: HH:MM)\n"
        "Time is in Tbilisi (UTC+4)",
        reply_markup=ReplyKeyboardRemove()
    )
    return TIME

async def custom_days_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom days input."""
    text = update.message.text.upper()
    day_map = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6,
               "1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6}
    
    days = []
    for part in text.split(","):
        part = part.strip()
        if part in day_map:
            days.append(day_map[part])
    
    if not days:
        await update.message.reply_text("❌ Неверный формат. Попробуйте: Mon,Wed,Fri")
        return CUSTOM_DAYS
    
    context.user_data["custom_days"] = days
    await update.message.reply_text("⏰ Во сколько? (Формат: HH:MM)")
    return TIME

# ==================== HOURLY RANGE HANDLERS ====================

async def hourly_start_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle hourly range start time."""
    time_str = update.message.text
    try:
        datetime.strptime(time_str, "%H:%M")
        context.user_data["hourly_start"] = time_str
        await update.message.reply_text(
            "🕐 Enter END time (HH:MM):\n"
            "Example: 24:00 or 01:00"
        )
        return HOURLY_END
    except ValueError:
        await update.message.reply_text("❌ Invalid format. Use HH:MM")
        return HOURLY_START

async def hourly_end_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle hourly range end time."""
    time_str = update.message.text
    
    if time_str == "24:00":
        context.user_data["hourly_end_midnight"] = True
    
    try:
        if time_str != "24:00":
            datetime.strptime(time_str, "%H:%M")
        context.user_data["hourly_end"] = time_str
        await update.message.reply_text(
            "📆 Enter days (comma-separated):\n"
            "Example: Mon,Tue,Wed,Thu,Fri"
        )
        return HOURLY_DAYS
    except ValueError:
        await update.message.reply_text("❌ Invalid format. Use HH:MM")
        return HOURLY_END

async def hourly_days_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle hourly range days selection."""
    text = update.message.text.upper()
    day_map = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6,
               "1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6}
    
    days = []
    for part in text.split(","):
        part = part.strip()
        if part in day_map:
            days.append(day_map[part])
    
    if not days:
        await update.message.reply_text("❌ Invalid format. Try: Mon,Tue,Wed,Thu,Fri")
        return HOURLY_DAYS
    
    context.user_data["custom_days"] = days
    
    start_h = int(context.user_data["hourly_start"].split(":")[0])
    end_str = context.user_data["hourly_end"]
    
    if end_str == "24:00":
        end_h = 24
    else:
        end_h = int(end_str.split(":")[0])
    
    hours = list(range(start_h, end_h + 1)) if end_h > start_h else list(range(start_h, 24)) + list(range(0, end_h + 1))
    context.user_data["hourly_times"] = [f"{h:02d}:00" for h in hours]
    
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    days_str = ", ".join([day_names[d] for d in days])
    
    await update.message.reply_text(
        f"✅ Configured!\n"
        f"📆 Days: {days_str}\n"
        f"⏰ Hours: {context.user_data['hourly_start']} - {end_str} ({len(hours)} reminders/day)\n\n"
        f"📝 Enter reminder text, then /done"
    )
    context.user_data["messages"] = []
    return MULTI_MSG

async def time_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle time input."""
    time_str = update.message.text
    try:
        datetime.strptime(time_str, "%H:%M")
        context.user_data["time"] = time_str
        await update.message.reply_text("📝 What to remind?\n(Enter text, then /done)")
        context.user_data["messages"] = []
        return MULTI_MSG
    except ValueError:
        await update.message.reply_text("❌ Invalid format. Use HH:MM")
        return TIME

async def multi_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collect multiple messages."""
    if update.message.text == "/done":
        if not context.user_data.get("messages"):
            await update.message.reply_text("❌ Add at least one message!")
            return MULTI_MSG
        
        reply_keyboard = [["No attachment"], ["Send photo/file"]]
        await update.message.reply_text(
            "📎 Attach photo or file?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return ATTACHMENT
    
    context.user_data["messages"].append({"type": "text", "content": update.message.text})
    count = len(context.user_data["messages"])
    await update.message.reply_text(f"✅ Message #{count} added. More or /done")
    return MULTI_MSG

async def attachment_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle attachment choice."""
    if update.message.text == "No attachment":
        return await ask_repeat_until(update, context)
    else:
        await update.message.reply_text("📤 Send photo or document.", reply_markup=ReplyKeyboardRemove())
        return ATTACHMENT

async def attachment_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle received attachment."""
    if update.message.photo:
        context.user_data["attachment"] = {"type": "photo", "file_id": update.message.photo[-1].file_id}
        await update.message.reply_text("✅ Photo attached!")
    elif update.message.document:
        context.user_data["attachment"] = {"type": "document", "file_id": update.message.document.file_id}
        await update.message.reply_text("✅ Document attached!")
    else:
        await update.message.reply_text("❌ Send photo or document.")
        return ATTACHMENT
    return await ask_repeat_until(update, context)

async def ask_repeat_until(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for repeat until date."""
    freq = context.user_data.get("frequency")
    if freq in ["Daily", "Weekly", "Custom Days", "Hourly Range"]:
        reply_keyboard = [["No end date"], ["Set end date"]]
        await update.message.reply_text(
            "📆 Set end date?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return REPEAT_UNTIL
    return await ask_destination(update, context)

async def repeat_until_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle repeat until choice."""
    if update.message.text == "No end date":
        context.user_data["repeat_until"] = None
        return await ask_destination(update, context)
    await update.message.reply_text("📅 Enter end date (YYYY-MM-DD):", reply_markup=ReplyKeyboardRemove())
    return REPEAT_UNTIL

async def repeat_until_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle repeat until date input."""
    try:
        datetime.strptime(update.message.text, "%Y-%m-%d")
        context.user_data["repeat_until"] = update.message.text
        return await ask_destination(update, context)
    except ValueError:
        await update.message.reply_text("❌ Invalid format. Use YYYY-MM-DD")
        return REPEAT_UNTIL

# Simple user ID storage for To Username feature
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_user(user_id: int, username: str):
    users = load_users()
    users[str(user_id)] = {"username": username}
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

async def ask_destination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for destination."""
    # Save user for future lookups
    if update.effective_user.username:
        save_user(update.effective_user.id, update.effective_user.username)
    
    reply_keyboard = [["To Me", "To Group"], ["To Username", "Specific Chat ID"]]
    await update.message.reply_text(
        "📍 Where should I send the reminder?\n\n"
        "• To Me: Private message to you\n"
        "• To Group: Default group\n"
        "• To Username: Send to a specific user\n"
        "• Specific Chat ID: Enter ID manually",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return DESTINATION

async def destination_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle destination choice."""
    choice = update.message.text
    
    if choice == "To Me":
        context.user_data["chat_id"] = update.effective_user.id
        return await finalize_reminder(update, context)
    elif choice == "To Group":
        context.user_data["chat_id"] = DEFAULT_GROUP_ID
        return await finalize_reminder(update, context)
    elif choice == "To Username":
        await update.message.reply_text("👤 Enter username (without @):", reply_markup=ReplyKeyboardRemove())
        return USERNAME_INPUT
    elif choice == "Specific Chat ID":
        await update.message.reply_text("📝 Enter Chat ID:", reply_markup=ReplyKeyboardRemove())
        return DESTINATION_ID
    else:
        await update.message.reply_text("❌ Please select an option.")
        return DESTINATION

async def username_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Resolve username to chat ID."""
    username = update.message.text.strip().replace("@", "").lower()
    users = load_users()
    
    target_id = None
    for uid, info in users.items():
        if info.get("username", "").lower() == username:
            target_id = int(uid)
            break
    
    if target_id:
        context.user_data["chat_id"] = target_id
        await update.message.reply_text(f"✅ Found user @{username}")
        return await finalize_reminder(update, context)
    else:
        await update.message.reply_text(
            f"❌ User @{username} not found.\n"
            "They must have used /start with me first.\n\n"
            "Try another username or /cancel"
        )
        return USERNAME_INPUT

async def destination_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle chat ID input."""
    try:
        context.user_data["chat_id"] = int(update.message.text)
        return await finalize_reminder(update, context)
    except ValueError:
        await update.message.reply_text("❌ Неверный ID. Введите число.")
        return DESTINATION_ID

async def finalize_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save the reminder and schedule it."""
    ud = context.user_data
    
    # Handle Hourly Range
    if ud.get("frequency") == "Hourly Range":
        hourly_times = ud.get("hourly_times", [])
        for t in hourly_times:
            reminder = {
                "user_id": update.effective_user.id,
                "frequency": "Hourly Range",
                "time": t,
                "messages": ud["messages"],
                "chat_id": ud["chat_id"],
                "attachment": ud.get("attachment"),
                "repeat_until": ud.get("repeat_until"),
                "custom_days": ud.get("custom_days"),
            }
            reminder_id = add_reminder(reminder)
            schedule_reminder(context.application, reminder_id)
        
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        days_str = ", ".join([day_names[d] for d in ud.get("custom_days", [])])
        
        await update.message.reply_text(
            f"✅ Created!\n\n"
            f"📆 Days: {days_str}\n"
            f"⏰ Hours: {ud['hourly_start']} - {ud['hourly_end']}\n"
            f"🔢 Reminders: {len(hourly_times)}/day\n"
            f"📍 Chat ID: {ud['chat_id']}",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Normal reminder
    reminder = {
        "user_id": update.effective_user.id,
        "frequency": ud["frequency"],
        "time": ud["time"],
        "messages": ud["messages"],
        "chat_id": ud["chat_id"],
        "attachment": ud.get("attachment"),
        "repeat_until": ud.get("repeat_until"),
        "custom_days": ud.get("custom_days"),
    }
    
    reminder_id = add_reminder(reminder)
    schedule_reminder(context.application, reminder_id)
    
    freq_str = ud["frequency"]
    if ud.get("custom_days"):
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        days_str = ", ".join([day_names[d] for d in ud["custom_days"]])
        freq_str = f"Custom ({days_str})"
    
    await update.message.reply_text(
        f"✅ Reminder created!\n\n"
        f"🆔 ID: `{reminder_id}`\n"
        f"📅 Frequency: {freq_str}\n"
        f"⏰ Time: {ud['time']} (Tbilisi)\n"
        f"📍 Chat ID: {ud['chat_id']}",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

# ==================== SCHEDULING ====================

def schedule_reminder(app, reminder_id: str):
    """Schedule a reminder job."""
    data = load_reminders()
    if reminder_id not in data:
        return
    
    reminder = data[reminder_id]
    time_str = reminder["time"]
    if time_str == "24:00":
        time_str = "00:00"
    
    time_obj = datetime.strptime(time_str, "%H:%M").time().replace(tzinfo=TBILISI_TZ)
    freq = reminder["frequency"]
    
    try:
        for job in app.job_queue.get_jobs_by_name(reminder_id):
            job.schedule_removal()
    except:
        pass
    
    if freq == "Daily":
        app.job_queue.run_daily(send_reminder_callback, time=time_obj, days=(0,1,2,3,4,5,6), name=reminder_id, data=reminder_id)
    elif freq == "Weekly":
        app.job_queue.run_daily(send_reminder_callback, time=time_obj, days=(0,), name=reminder_id, data=reminder_id)
    elif freq == "Custom Days":
        days = tuple(reminder.get("custom_days", [0]))
        app.job_queue.run_daily(send_reminder_callback, time=time_obj, days=days, name=reminder_id, data=reminder_id)
    elif freq == "One-time":
        now = datetime.now(TBILISI_TZ)
        naive_time = time_obj.replace(tzinfo=None)
        target = TBILISI_TZ.localize(datetime.combine(now.date(), naive_time))
        if target <= now:
            target += timedelta(days=1)
        app.job_queue.run_once(send_reminder_callback, when=target, name=reminder_id, data=reminder_id)
    elif freq == "Hourly Range":
        days = tuple(reminder.get("custom_days", [0,1,2,3,4]))
        app.job_queue.run_daily(send_reminder_callback, time=time_obj, days=days, name=reminder_id, data=reminder_id)

async def send_reminder_callback(context: ContextTypes.DEFAULT_TYPE):
    """Send the reminder."""
    reminder_id = context.job.data
    data = load_reminders()
    
    if reminder_id not in data:
        return
    
    reminder = data[reminder_id]
    chat_id = reminder["chat_id"]
    
    if reminder.get("repeat_until"):
        end_date = datetime.strptime(reminder["repeat_until"], "%Y-%m-%d").date()
        if datetime.now(TBILISI_TZ).date() > end_date:
            mark_completed(reminder_id)
            context.job.schedule_removal()
            return
    
    keyboard = [[InlineKeyboardButton("✅ Done", callback_data=f"done_{reminder_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    for i, msg in enumerate(reminder["messages"]):
        is_last = i == len(reminder["messages"]) - 1
        markup = reply_markup if is_last else None
        if msg["type"] == "text":
            await context.bot.send_message(chat_id=chat_id, text=f"🔔 {msg['content']}", reply_markup=markup)
    
    attachment = reminder.get("attachment")
    if attachment:
        if attachment["type"] == "photo":
            await context.bot.send_photo(chat_id=chat_id, photo=attachment["file_id"])
        elif attachment["type"] == "document":
            await context.bot.send_document(chat_id=chat_id, document=attachment["file_id"])
    
    if reminder["frequency"] == "One-time":
        mark_completed(reminder_id)

async def done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Done button press."""
    query = update.callback_query
    await query.answer()
    reminder_id = query.data.replace("done_", "")
    await query.edit_message_text("✅ Done!")

# ==================== LIST REMINDERS ====================

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List user's reminders."""
    reminders = get_user_reminders(update.effective_user.id)
    
    if not reminders:
        await update.message.reply_text("📭 No active reminders.")
        return
    
    text = "📋 Your reminders:\n\n"
    for r in reminders:
        freq = r["frequency"]
        if r.get("custom_days"):
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            days_str = ", ".join([day_names[d] for d in r["custom_days"]])
            freq = f"Custom ({days_str})"
        msg_preview = r["messages"][0]["content"][:20] + "..." if len(r["messages"][0]["content"]) > 20 else r["messages"][0]["content"]
        text += f"🆔 `{r['id']}` | ⏰ {r['time']} | {freq}\n💬 {msg_preview}\n\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

# ==================== DELETE REMINDER ====================

async def delete_reminder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start delete flow."""
    reminders = get_user_reminders(update.effective_user.id)
    
    if not reminders:
        await update.message.reply_text("📭 No reminders to delete.")
        return ConversationHandler.END
    
    text = "🗑 Which reminder to delete?\n\n"
    for r in reminders:
        text += f"`{r['id']}` - {r['messages'][0]['content'][:20]}...\n"
    text += "\nEnter ID or /cancel"
    await update.message.reply_text(text, parse_mode="Markdown")
    return DELETE_SELECT

async def delete_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle delete selection."""
    reminder_id = update.message.text.strip()
    data = load_reminders()
    
    if reminder_id in data and data[reminder_id]["user_id"] == update.effective_user.id:
        for job in context.application.job_queue.get_jobs_by_name(reminder_id):
            job.schedule_removal()
        delete_reminder(reminder_id)
        await update.message.reply_text(f"✅ Reminder `{reminder_id}` deleted.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Reminder not found.")
    return ConversationHandler.END

# ==================== EDIT REMINDER ====================

async def edit_reminder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start edit flow."""
    reminders = get_user_reminders(update.effective_user.id)
    
    if not reminders:
        await update.message.reply_text("📭 No reminders to edit.")
        return ConversationHandler.END
    
    text = "✏️ Which reminder to edit?\n\n"
    for r in reminders:
        text += f"`{r['id']}` - {r['time']} - {r['messages'][0]['content'][:15]}...\n"
    text += "\nEnter ID or /cancel"
    await update.message.reply_text(text, parse_mode="Markdown")
    return EDIT_SELECT

async def edit_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle edit selection."""
    reminder_id = update.message.text.strip()
    data = load_reminders()
    
    if reminder_id in data and data[reminder_id]["user_id"] == update.effective_user.id:
        context.user_data["edit_id"] = reminder_id
        reply_keyboard = [["Time", "Message"], ["Frequency", "End Date"]]
        await update.message.reply_text("What to edit?", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return EDIT_FIELD
    await update.message.reply_text("❌ Reminder not found.")
    return ConversationHandler.END

async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle field selection."""
    field = update.message.text.lower()
    context.user_data["edit_field"] = field
    prompts = {"time": "⏰ New time (HH:MM):", "message": "💬 New message:", "frequency": "📅 New frequency (Daily/One-time/Weekly):", "end date": "📆 New end date (YYYY-MM-DD or 'none'):"}
    await update.message.reply_text(prompts.get(field, "Enter new value:"), reply_markup=ReplyKeyboardRemove())
    return EDIT_VALUE

async def edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Apply edit."""
    value = update.message.text
    field = context.user_data["edit_field"]
    reminder_id = context.user_data["edit_id"]
    
    updates = {}
    if field == "time":
        try:
            datetime.strptime(value, "%H:%M")
            updates["time"] = value
        except:
            await update.message.reply_text("❌ Invalid format.")
            return EDIT_VALUE
    elif field == "message":
        updates["messages"] = [{"type": "text", "content": value}]
    elif field == "frequency":
        if value in ["Daily", "One-time", "Weekly"]:
            updates["frequency"] = value
        else:
            await update.message.reply_text("❌ Use Daily/One-time/Weekly")
            return EDIT_VALUE
    elif field == "end date":
        if value.lower() == "none":
            updates["repeat_until"] = None
        else:
            try:
                datetime.strptime(value, "%Y-%m-%d")
                updates["repeat_until"] = value
            except:
                await update.message.reply_text("❌ Invalid format.")
                return EDIT_VALUE
    
    update_reminder(reminder_id, updates)
    for job in context.application.job_queue.get_jobs_by_name(reminder_id):
        job.schedule_removal()
    schedule_reminder(context.application, reminder_id)
    
    await update.message.reply_text(f"✅ Reminder `{reminder_id}` updated!", parse_mode="Markdown")
    context.user_data.clear()
    return ConversationHandler.END

# ==================== RESTORE ON STARTUP ====================

def restore_reminders(app):
    """Restore all reminders on bot startup."""
    data = load_reminders()
    count = 0
    for reminder_id, reminder in data.items():
        if not reminder.get("completed"):
            schedule_reminder(app, reminder_id)
            count += 1
    logger.info(f"Restored {count} reminders")

# ==================== MAIN ====================

def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(token).build()
    
    # New reminder conversation
    new_conv = ConversationHandler(
        entry_points=[CommandHandler("newreminder", new_reminder)],
        states={
            FREQUENCY: [MessageHandler(filters.Regex("^(Daily|One-time|Weekly|Custom Days|Hourly Range)$"), frequency_choice)],
            CUSTOM_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_days_choice)],
            HOURLY_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, hourly_start_choice)],
            HOURLY_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, hourly_end_choice)],
            HOURLY_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, hourly_days_choice)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_choice)],
            MULTI_MSG: [CommandHandler("done", multi_message), MessageHandler(filters.TEXT & ~filters.COMMAND, multi_message)],
            ATTACHMENT: [
                MessageHandler(filters.Regex("^(No attachment|Send photo/file)$"), attachment_choice),
                MessageHandler(filters.PHOTO | filters.Document.ALL, attachment_received)
            ],
            REPEAT_UNTIL: [
                MessageHandler(filters.Regex("^(No end date|Set end date)$"), repeat_until_choice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, repeat_until_date)
            ],
            DESTINATION: [MessageHandler(filters.Regex("^(To Me|To Group|To Username|Specific Chat ID)$"), destination_choice)],
            USERNAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, username_input)],
            DESTINATION_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, destination_id_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Delete conversation
    delete_conv = ConversationHandler(
        entry_points=[CommandHandler("deletereminder", delete_reminder_cmd)],
        states={DELETE_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_select)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Edit conversation
    edit_conv = ConversationHandler(
        entry_points=[CommandHandler("editreminder", edit_reminder_cmd)],
        states={
            EDIT_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_select)],
            EDIT_FIELD: [MessageHandler(filters.Regex("^(Time|Message|Frequency|End Date)$"), edit_field)],
            EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getid", get_id))
    app.add_handler(CommandHandler("listreminders", list_reminders))
    app.add_handler(new_conv)
    app.add_handler(delete_conv)
    app.add_handler(edit_conv)
    app.add_handler(CallbackQueryHandler(done_callback, pattern="^done_"))
    
    # Restore reminders
    restore_reminders(app)
    
    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
