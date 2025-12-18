# Telegram Reminder Bot 🔔

A feature-rich Telegram bot for setting and managing reminders with AI assistant integration.

## Features

- ✅ **Persistent Storage** - Reminders survive bot restarts
- ✅ **Flexible Scheduling** - Daily, Weekly, One-time, or Custom Days
- ✅ **Multiple Messages** - Send a sequence of messages per reminder
- ✅ **Attachments** - Attach photos or documents
- ✅ **End Date** - Set when recurring reminders should stop
- ✅ **Confirmation Buttons** - Mark reminders as "Done"
- ✅ **Edit & Delete** - Full reminder management
- ✅ **AI Assistant** - Built-in AI chat powered by OpenRouter

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Start the Bot
```bash
python bot.py
```
Or double-click `start.bat`

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and help |
| `/newreminder` | Create a new reminder |
| `/listreminders` | View all active reminders |
| `/editreminder` | Modify an existing reminder |
| `/deletereminder` | Remove a reminder |
| `/ai` | Chat with AI assistant |
| `/getid` | Get current chat ID (for group reminders) |
| `/cancel` | Cancel current operation |

### Creating a Reminder

1. Send `/newreminder`
2. Choose frequency: Daily, One-time, Weekly, or Custom Days
3. Enter time in HH:MM format (Tbilisi Time UTC+4)
4. Type your reminder message(s), send `/done` when finished
5. Optionally attach a photo or document
6. Set an end date for recurring reminders (optional)
7. Choose destination: current chat or specific chat ID

### Group Reminders

1. Add the bot to your group
2. Send `/getid` in the group to get the Chat ID
3. Use that ID when creating a reminder

## Configuration

Edit these values in `bot.py`:

```python
# Bot Token
token = "YOUR_BOT_TOKEN"

# Timezone
TBILISI_TZ = pytz.timezone("Asia/Tbilisi")

# AI API Key
OPENROUTER_API_KEY = "YOUR_API_KEY"
```

## Files

- `bot.py` - Main bot code
- `requirements.txt` - Python dependencies
- `reminders.json` - Persistent reminder storage (auto-created)
- `start.bat` - Windows launcher

## License

MIT
