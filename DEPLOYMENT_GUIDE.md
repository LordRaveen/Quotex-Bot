# PythonAnywhere Deployment Guide

## 🚀 Deploying Your Quotex Trading Bot

### Step 1: Create PythonAnywhere Account
1. Go to [PythonAnywhere.com](https://www.pythonanywhere.com)
2. Sign up for a free account (or paid for better performance)
3. Access your dashboard

### Step 2: Upload Your Files
1. Go to the **Files** tab
2. Create a new directory: `quotex-bot`
3. Upload these files to the directory:
   - `run.py`
   - `main.py`
   - `functions.py`
   - `requirements.txt`
   - `templates/index.html`

### Step 3: Install Dependencies
1. Go to the **Consoles** tab
2. Open a **Bash console**
3. Navigate to your project directory:
   ```bash
   cd quotex-bot
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Step 4: Configure Telegram Session
1. In the bash console, run:
   ```bash
   python -c "from telethon.sync import TelegramClient; TelegramClient('my_session', 26500165, '119c983b9aee401c4411b140bf11f463').start()"
   ```
2. Enter your phone number when prompted
3. Enter the verification code sent to your Telegram
4. This will create the `my_session.session` file

### Step 5: Set Up Scheduled Task
1. Go to the **Tasks** tab
2. Add a new scheduled task:
   - **Command**: `cd ~/quotex-bot && python run.py`
   - **Schedule**: Daily at 8:00 AM UTC-3 (or whenever you want it to start)
   - **Enabled**: Yes

### Step 6: Test the Bot
1. In the bash console, run:
   ```bash
   cd quotex-bot
   python run.py
   ```
2. Check the logs to ensure everything is working

### Step 7: Monitor Your Bot
- Check the **Files** tab to view `trading_bot.log`
- Monitor the database file `trades.db`
- Check PythonAnywhere's task logs

## 📊 Bot Schedule

The bot will automatically:
- ✅ **Run Monday-Saturday** (no trading on Sundays)
- ✅ **Monitor 3 trading sessions daily**
- ✅ **Each session lasts 3 hours 30 minutes**
- ✅ **Monitor Telegram for signals**
- ✅ **Place trades automatically**
- ✅ **Handle gale trades**

## 🌍 Trading Sessions (UTC-3 Timezone)

### 🌅 Morning Session
- **Start Time:** 8:30 AM UTC-3
- **Duration:** 3 hours 30 minutes
- **End Time:** 12:00 PM UTC-3

**Global Times:**
- 🇧🇷 Brazil: 8:30 AM
- 🇺🇸 Miami: 7:30 AM
- 🇬🇧 UK: 11:30 AM
- 🇿🇦 South Africa: 10:30 AM
- 🇪🇸 Spain: 10:30 AM
- 🇲🇽 Mexico: 6:30 AM
- 🇨🇴 Colombia: 6:30 AM
- 🇳🇬 Nigeria: 12:30 PM
- 🇮🇳 India: 6:00 PM
- 🇲🇾 Malaysia: 8:30 PM
- 🇵🇭 Philippines: 8:30 PM

### 🌞 Afternoon Session
- **Start Time:** 4:00 PM UTC-3
- **Duration:** 3 hours 30 minutes
- **End Time:** 7:30 PM UTC-3

**Global Times:**
- 🇧🇷 Brazil: 4:00 PM
- 🇺🇸 Miami: 3:00 PM
- 🇬🇧 UK: 7:00 PM
- 🇿🇦 South Africa: 7:00 PM
- 🇪🇸 Spain: 5:00 PM
- 🇲🇽 Mexico: 1:00 PM
- 🇨🇴 Colombia: 1:00 PM
- 🇳🇬 Nigeria: 7:00 PM
- 🇮🇳 India: 10:30 PM
- 🇲🇾 Malaysia: 4:00 AM (next day)
- 🇵🇭 Philippines: 3:00 AM (next day)

### 🌙 Overnight Session
- **Start Time:** 12:00 AM UTC-3 (midnight)
- **Duration:** 3 hours 30 minutes
- **End Time:** 3:30 AM UTC-3

**Global Times:**
- 🇧🇷 Brazil: 12:00 AM
- 🇺🇸 Miami: 11:00 PM (previous day)
- 🇬🇧 UK: 3:00 AM
- 🇿🇦 South Africa: 2:00 AM
- 🇪🇸 Spain: 2:00 AM
- 🇲🇽 Mexico: 10:00 PM (previous day)
- 🇨🇴 Colombia: 10:00 PM (previous day)
- 🇳🇬 Nigeria: 4:00 AM
- 🇮🇳 India: 8:30 AM
- 🇲🇾 Malaysia: 11:00 AM
- 🇵🇭 Philippines: 11:00 AM

## ⚠️ Important Notes

1. **Free Account Limitations**: PythonAnywhere free accounts have limited CPU time
2. **Upgrade Recommended**: Consider upgrading for better reliability
3. **Backup**: Regularly backup your `trades.db` file
4. **Monitoring**: Check logs daily to ensure the bot is running properly
5. **Security**: Keep your API credentials secure

## 🔧 Troubleshooting

### Common Issues:
1. **Import Errors**: Make sure all dependencies are installed
2. **Telegram Auth**: Re-run the Telegram session setup if needed
3. **Quotex Connection**: Check your credentials and internet connection
4. **Timezone Issues**: Verify the timezone settings in `run.py`

### Log Locations:
- Bot logs: `trading_bot.log`
- PythonAnywhere logs: Tasks tab
- Database: `trades.db`

## 📞 Support

If you encounter issues:
1. Check the logs first
2. Verify all dependencies are installed
3. Ensure Telegram session is valid
4. Check PythonAnywhere's status page
