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

| Command           | Description                               |
| ----------------- | ----------------------------------------- |
| `/start`          | Welcome message and help                  |
| `/newreminder`    | Create a new reminder                     |
| `/listreminders`  | View all active reminders                 |
| `/editreminder`   | Modify an existing reminder               |
| `/deletereminder` | Remove a reminder                         |
| `/ai`             | Chat with AI assistant                    |
| `/getid`          | Get current chat ID (for group reminders) |
| `/cancel`         | Cancel current operation                  |

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

Set environment variable `TELEGRAM_BOT_TOKEN` or edit the fallback in `bot.py`.

## Ubuntu VPS Deployment

### 1. Upload Files to VPS

```bash
# On your local machine, or use git clone on VPS
scp -r ./* root@YOUR_VPS_IP:/opt/reminder-bot/
```

### 2. Install Python & Dependencies

```bash
ssh root@YOUR_VPS_IP

apt update && apt install -y python3 python3-pip python3-venv

cd /opt/reminder-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Systemd Service

```bash
# Edit the token in the service file
nano /opt/reminder-bot/reminder-bot.service
# Change: Environment=TELEGRAM_BOT_TOKEN=your_actual_token

# Install the service
cp /opt/reminder-bot/reminder-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable reminder-bot
systemctl start reminder-bot
```

### 4. Verify & Manage

```bash
# Check status
systemctl status reminder-bot

# View logs
journalctl -u reminder-bot -f

# Restart after changes
systemctl restart reminder-bot

# Stop
systemctl stop reminder-bot
```

## Files

- `bot.py` - Main bot code
- `requirements.txt` - Python dependencies
- `reminders.json` - Persistent reminder storage (auto-created)
- `start.bat` - Windows launcher

## License

MIT
