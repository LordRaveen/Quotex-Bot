import asyncio
import json
import re
import time
from datetime import datetime, timedelta
import sqlite3
from telethon.sync import TelegramClient
from pyquotex.stable_api import Quotex
import logging
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Fix Unicode encoding for Windows console
import sys
if sys.platform.startswith('win'):
    # Set console to UTF-8 mode
    import os
    os.system('chcp 65001 > nul')

# Configuration
TELEGRAM_API_ID = 26500165
TELEGRAM_API_HASH = '119c983b9aee401c4411b140bf11f463'
TELEGRAM_SESSION = 'my_session'
TELEGRAM_CHAT = "https://t.me/+MJeq2boHo5gxNGVh"

QUOTEX_EMAIL = "courageokaka9@gmail.com"
QUOTEX_PASSWORD = "quotexPass9@"

# Trading parameters
DEFAULT_AMOUNT = 1.0  # Default bet amount in USD
CHECK_INTERVAL = 30  # Check for new signals every 30 seconds
GALE_MULTIPLIER = 2.0  # Martingale multiplier for gale trades
TEST_MODE = False  # Set to False to enable actual trading

# Session configuration (UTC-3 timezone)
SESSION_TIMEZONE = pytz.timezone('America/Sao_Paulo')  # UTC-3
SESSION_DURATION = 210  # 3 hours 30 minutes in minutes

# All trading sessions (UTC-3 timezone)
SESSIONS = [
    {
        "name": "Morning Session",
        "start_time": "08:30",  # 8:30 AM UTC-3
        "duration_minutes": 210,
        "description": "Morning trading session"
    },
    {
        "name": "Afternoon Session", 
        "start_time": "16:00",  # 4:00 PM UTC-3
        "duration_minutes": 210,
        "description": "Afternoon trading session"
    },
    {
        "name": "Overnight Session",
        "start_time": "00:00",  # 12:00 AM UTC-3 (midnight)
        "duration_minutes": 210,
        "description": "Overnight trading session"
    }
]

class TradingBot:
    def __init__(self):
        self.db_path = 'trades.db'
        self.init_database()
        self.quotex_client = None
        self.telegram_client = None
        self.last_processed_message_id = None
        
    def init_database(self):
        """Initialize SQLite database for tracking trades"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE,
                signal_text TEXT,
                asset TEXT,
                direction TEXT,
                expiry_minutes INTEGER,
                amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                executed_at TIMESTAMP,
                result TEXT,
                gale_level INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_messages (
                message_id TEXT PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def is_sunday(self):
        """Check if today is Sunday"""
        now = datetime.now(SESSION_TIMEZONE)
        return now.weekday() == 6  # Sunday is 6
    
    def get_next_session_start(self):
        """Get the next session start time"""
        now = datetime.now(SESSION_TIMEZONE)
        
        # If it's Sunday, return None (no trading)
        if self.is_sunday():
            return None
        
        # Check all sessions for today and tomorrow
        for session in SESSIONS:
            hour, minute = map(int, session["start_time"].split(':'))
            session_start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If session hasn't started yet today, return it
            if session_start > now:
                return session_start
        
        # If no sessions today, check tomorrow's first session
        tomorrow = now + timedelta(days=1)
        first_session = SESSIONS[0]  # Morning session
        hour, minute = map(int, first_session["start_time"].split(':'))
        next_session = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return next_session
    
    def is_session_active(self):
        """Check if we're currently in an active trading session"""
        now = datetime.now(SESSION_TIMEZONE)
        
        # No trading on Sundays
        if self.is_sunday():
            return False
        
        # Check all sessions
        for session in SESSIONS:
            hour, minute = map(int, session["start_time"].split(':'))
            session_start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            session_end = session_start + timedelta(minutes=session["duration_minutes"])
            
            # Check if current time is within this session
            if session_start <= now <= session_end:
                return True
        
        return False
    
    def get_current_session_info(self):
        """Get information about the current active session"""
        now = datetime.now(SESSION_TIMEZONE)
        
        for session in SESSIONS:
            hour, minute = map(int, session["start_time"].split(':'))
            session_start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            session_end = session_start + timedelta(minutes=session["duration_minutes"])
            
            if session_start <= now <= session_end:
                remaining = session_end - now
                return {
                    "name": session["name"],
                    "remaining_minutes": remaining.seconds // 60,
                    "remaining_hours": remaining.seconds // 3600,
                    "remaining_minutes_only": (remaining.seconds % 3600) // 60
                }
        
        return None
    
    def get_session_status(self):
        """Get current session status information"""
        now = datetime.now(SESSION_TIMEZONE)
        
        if self.is_sunday():
            return {
                "status": "sunday",
                "message": "No trading on Sundays",
                "next_session": None
            }
        
        if self.is_session_active():
            # Get current session info
            current_session = self.get_current_session_info()
            if current_session:
                return {
                    "status": "active",
                    "message": f"{current_session['name']} active - {current_session['remaining_hours']}h {current_session['remaining_minutes_only']}m remaining",
                    "next_session": None
                }
            else:
                return {
                    "status": "active",
                    "message": "Session active",
                    "next_session": None
                }
        else:
            next_session = self.get_next_session_start()
            if next_session:
                time_until = next_session - now
                hours = time_until.seconds // 3600
                minutes = (time_until.seconds % 3600) // 60
                
                # Determine which session is next
                next_session_name = "Next session"
                for session in SESSIONS:
                    hour, minute = map(int, session["start_time"].split(':'))
                    session_start = next_session.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if abs((next_session - session_start).total_seconds()) < 60:  # Within 1 minute
                        next_session_name = session["name"]
                        break
                
                return {
                    "status": "waiting",
                    "message": f"Waiting for {next_session_name} - {hours}h {minutes}m until start",
                    "next_session": next_session
                }
            else:
                return {
                    "status": "ended",
                    "message": "All sessions have ended for today",
                    "next_session": None
                }
    
    async def connect_quotex(self):
        """Connect to Quotex API"""
        try:
            logger.info("Attempting to connect to Quotex...")
            
            self.quotex_client = Quotex(email=QUOTEX_EMAIL, password=QUOTEX_PASSWORD, lang="en")
            check_connect, message = await self.quotex_client.connect()
            
            if check_connect:
                balance = await self.quotex_client.get_balance()
                logger.info(f"Connected to Quotex. Balance: ${balance}")
                return True
            else:
                logger.error(f"Failed to connect to Quotex: {message}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to Quotex: {e}")
            return False
    
    async def connect_telegram(self):
        """Connect to Telegram"""
        try:
            self.telegram_client = TelegramClient(TELEGRAM_SESSION, TELEGRAM_API_ID, TELEGRAM_API_HASH)
            await self.telegram_client.start()
            logger.info("Connected to Telegram successfully")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Telegram: {e}")
            return False
    
    def is_signal_message(self, message_text):
        """Check if message contains signal indicators"""
        if not message_text:
            return False
        
        # Key signal indicators that must be present
        signal_indicators = [
            'Time Zone',
            'minutes expiry',
            '1ST GALE',
            '2ND GALE',
            "Don't know how to trade yet",
            'TIME TO',
            'GALE',
            'expiry',
            'USD/BRL',
            'EUR/USD',
            'GBP/USD'
        ]
        
        # Check if message contains at least 3 of the key indicators
        found_indicators = 0
        for indicator in signal_indicators:
            if indicator.lower() in message_text.lower():
                found_indicators += 1
        
        # Message is likely a signal if it contains at least 2 indicators
        return found_indicators >= 2
    
    def parse_signal(self, message_text):
        """Parse trading signal from Telegram message"""
        try:
            # First check if this message is likely a signal
            if not self.is_signal_message(message_text):
                return None
            
            # Extract asset pair (e.g., USD/BRL)
            asset_match = re.search(r'([A-Z]{3}/[A-Z]{3})', message_text)
            if not asset_match:
                logger.debug(f"No asset pair found in signal message")
                return None
            
            asset = asset_match.group(1)
            
            # Extract direction (PUT or CALL)
            direction_match = re.search(r'(PUT|CALL)', message_text, re.IGNORECASE)
            if not direction_match:
                logger.debug(f"No direction (PUT/CALL) found in signal message")
                return None
            
            direction = direction_match.group(1).lower()
            
            # Extract expiry time (e.g., 5 minutes)
            expiry_match = re.search(r'(\d+)\s*minutes?\s*expiry', message_text, re.IGNORECASE)
            if not expiry_match:
                logger.debug(f"No expiry time found in signal message")
                return None
            
            expiry_minutes = int(expiry_match.group(1))
            
            # Extract time information for gale levels
            time_matches = re.findall(r'TIME TO (\d{2}:\d{2})', message_text)
            
            logger.info(f"[OK] Successfully parsed signal: {asset} {direction} {expiry_minutes}m")
            
            return {
                'asset': asset,
                'direction': direction,
                'expiry_minutes': expiry_minutes,
                'gale_times': time_matches,
                'raw_text': message_text
            }
        except Exception as e:
            logger.error(f"Error parsing signal: {e}")
            return None
    
    def is_message_processed(self, message_id):
        """Check if message has already been processed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM processed_messages WHERE message_id = ?', (str(message_id),))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def mark_message_processed(self, message_id):
        """Mark message as processed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO processed_messages (message_id) VALUES (?)', (str(message_id),))
        conn.commit()
        conn.close()
    
    def save_trade(self, message_id, signal_data, amount, gale_level=0):
        """Save trade to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades (message_id, signal_text, asset, direction, expiry_minutes, amount, gale_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(message_id),
            signal_data['raw_text'],
            signal_data['asset'],
            signal_data['direction'],
            signal_data['expiry_minutes'],
            amount,
            gale_level
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trade_id
    
    async def place_trade(self, signal_data, amount, gale_level=0):
        """Place trade on Quotex"""
        try:
            if TEST_MODE:
                logger.info(f"[TEST MODE] Would place trade: {amount} USD on {signal_data['asset']} {signal_data['direction']} for {signal_data['expiry_minutes']} minutes")
                return True
            
            if not self.quotex_client:
                logger.error("Quotex client not connected")
                return False
            
            # Convert asset format (USD/BRL -> USDBRL)
            asset = signal_data['asset'].replace('/', '')
            
            # Get asset data
            asset_name, asset_data = await self.quotex_client.get_available_asset(asset, force_open=True)
            
            if not asset_name:
                logger.error(f"Asset {asset} not available")
                return False
            
            # Calculate expiry time in seconds
            expiry_seconds = signal_data['expiry_minutes'] * 60
            
            logger.info(f"Placing trade: {amount} USD on {asset_name} {signal_data['direction']} for {signal_data['expiry_minutes']} minutes")
            
            # Place the trade
            status, buy_info = await self.quotex_client.buy(amount, asset_name, signal_data['direction'], expiry_seconds)
            
            if status:
                logger.info(f"Trade placed successfully: {buy_info}")
                return True
            else:
                logger.error(f"Failed to place trade: {buy_info}")
                return False
                
        except Exception as e:
            logger.error(f"Error placing trade: {e}")
            return False
    
    async def fetch_new_messages(self):
        """Fetch new messages from Telegram channel"""
        try:
            if not self.telegram_client:
                return []
            
            messages = []
            async for message in self.telegram_client.iter_messages(
                TELEGRAM_CHAT, 
                offset_date=datetime.now() - timedelta(minutes=5),
                reverse=True,
                limit=10
            ):
                if message.text and not self.is_message_processed(message.id):
                    messages.append({
                        'id': message.id,
                        'text': message.text,
                        'date': message.date
                    })
            
            return messages
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return []
    
    async def process_signals(self):
        """Main signal processing loop with session management"""
        logger.info("Starting signal processing with session management...")
        
        check_count = 0
        while True:
            try:
                check_count += 1
                
                # Get session status
                session_status = self.get_session_status()
                logger.info(f"Session status: {session_status['message']}")
                
                if session_status['status'] == 'sunday':
                    logger.info("[STOP] Sunday - No trading today. Waiting 1 hour before next check...")
                    await asyncio.sleep(3600)  # Wait 1 hour
                    continue
                
                elif session_status['status'] == 'waiting':
                    # Calculate wait time until session starts
                    next_session = session_status['next_session']
                    if next_session:
                        wait_seconds = (next_session - datetime.now(SESSION_TIMEZONE)).total_seconds()
                        if wait_seconds > 0:
                            logger.info(f"[CLOCK] Waiting for session to start in {wait_seconds/3600:.1f} hours...")
                            await asyncio.sleep(min(wait_seconds, 3600))  # Wait max 1 hour
                            continue
                
                elif session_status['status'] == 'ended':
                    logger.info("[FINISH] Today's session has ended. Waiting until tomorrow...")
                    # Wait until next day
                    tomorrow = datetime.now(SESSION_TIMEZONE) + timedelta(days=1)
                    tomorrow = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
                    wait_seconds = (tomorrow - datetime.now(SESSION_TIMEZONE)).total_seconds()
                    await asyncio.sleep(min(wait_seconds, 3600))  # Wait max 1 hour
                    continue
                
                elif session_status['status'] == 'active':
                    logger.info(f"[ROCKET] Session active! Checking for new messages... (check #{check_count})")
                    
                    # Fetch new messages
                    messages = await self.fetch_new_messages()
                    
                    if messages:
                        logger.info(f"Found {len(messages)} new message(s)")
                    else:
                        logger.info("No new messages found")
                    
                    for message in messages:
                        # First check if this message is likely a signal
                        if self.is_signal_message(message['text']):
                            logger.info(f"[SEARCH] Processing potential signal message {message['id']}: {message['text'][:100]}...")
                            
                            # Parse signal
                            signal_data = self.parse_signal(message['text'])
                            
                            if signal_data:
                                logger.info(f"[OK] Signal parsed: {signal_data['asset']} {signal_data['direction']} {signal_data['expiry_minutes']}m")
                                
                                # Mark message as processed
                                self.mark_message_processed(message['id'])
                                
                                # Save initial trade
                                trade_id = self.save_trade(message['id'], signal_data, DEFAULT_AMOUNT)
                                
                                # Place initial trade
                                success = await self.place_trade(signal_data, DEFAULT_AMOUNT)
                                
                                if success:
                                    logger.info(f"[OK] Initial trade placed successfully (ID: {trade_id})")
                                else:
                                    logger.error(f"[ERROR] Failed to place initial trade (ID: {trade_id})")
                                
                                # Schedule gale trades if times are provided
                                if signal_data['gale_times']:
                                    logger.info(f"[CALENDAR] Scheduling {len(signal_data['gale_times'])} gale trades")
                                    await self.schedule_gale_trades(message['id'], signal_data, signal_data['gale_times'])
                            else:
                                logger.warning(f"[WARNING] Message {message['id']} looked like a signal but couldn't parse it")
                        else:
                            # Skip non-signal messages silently
                            logger.debug(f"Skipping non-signal message {message['id']}")
                
                # Wait before next check
                logger.info(f"Waiting {CHECK_INTERVAL} seconds before next check...")
                await asyncio.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in signal processing loop: {e}")
                await asyncio.sleep(CHECK_INTERVAL)
    
    async def schedule_gale_trades(self, message_id, signal_data, gale_times):
        """Schedule gale trades based on provided times"""
        for i, gale_time in enumerate(gale_times, 1):
            try:
                # Parse gale time (format: HH:MM)
                hour, minute = map(int, gale_time.split(':'))
                gale_datetime = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If time has passed, schedule for next day
                if gale_datetime < datetime.now():
                    gale_datetime += timedelta(days=1)
                
                # Calculate delay until gale time
                delay = (gale_datetime - datetime.now()).total_seconds()
                
                if delay > 0:
                    logger.info(f"Scheduling gale trade {i} for {gale_time} (in {delay/60:.1f} minutes)")
                    
                    # Schedule the gale trade
                    asyncio.create_task(self.execute_gale_trade(message_id, signal_data, i, delay))
                    
            except Exception as e:
                logger.error(f"Error scheduling gale trade {i}: {e}")
    
    async def execute_gale_trade(self, message_id, signal_data, gale_level, delay):
        """Execute a gale trade after delay"""
        try:
            await asyncio.sleep(delay)
            
            # Calculate gale amount
            gale_amount = DEFAULT_AMOUNT * (GALE_MULTIPLIER ** gale_level)
            
            logger.info(f"Executing gale trade {gale_level}: {gale_amount} USD")
            
            # Save gale trade
            trade_id = self.save_trade(message_id, signal_data, gale_amount, gale_level)
            
            # Place gale trade
            success = await self.place_trade(signal_data, gale_amount, gale_level)
            
            if success:
                logger.info(f"Gale trade {gale_level} placed successfully (ID: {trade_id})")
            else:
                logger.error(f"Failed to place gale trade {gale_level} (ID: {trade_id})")
                
        except Exception as e:
            logger.error(f"Error executing gale trade {gale_level}: {e}")
    
    async def test_recent_messages(self):
        """Test function to fetch and parse recent messages"""
        try:
            logger.info("Testing recent messages from channel...")
            
            if not self.telegram_client:
                logger.error("Telegram client not connected")
                return
            
            messages = []
            async for message in self.telegram_client.iter_messages(
                TELEGRAM_CHAT, 
                limit=5,
                reverse=True
            ):
                if message.text:
                    messages.append({
                        'id': message.id,
                        'text': message.text,
                        'date': message.date
                    })
            
            logger.info(f"Found {len(messages)} recent messages")
            
            for message in messages:
                logger.info(f"📨 Message {message['id']} ({message['date']}):")
                logger.info(f"   Text: {message['text'][:200]}...")
                
                # Check if it's a signal message first
                if self.is_signal_message(message['text']):
                    logger.info(f"   [SEARCH] This looks like a signal message!")
                    
                    # Test signal parsing
                    signal_data = self.parse_signal(message['text'])
                    if signal_data:
                        logger.info(f"   [OK] Parsed: {signal_data['asset']} {signal_data['direction']} {signal_data['expiry_minutes']}m")
                        if signal_data['gale_times']:
                            logger.info(f"   [CALENDAR] Gale times: {signal_data['gale_times']}")
                    else:
                        logger.info(f"   [ERROR] Could not parse signal details")
                else:
                    logger.info(f"   [NOTE] Regular message (not a signal)")
                logger.info("")
                
        except Exception as e:
            logger.error(f"Error testing recent messages: {e}")
    
    async def run(self):
        """Main bot runner"""
        logger.info("Starting Quotex Trading Bot...")
        
        # Connect to Telegram first
        telegram_connected = await self.connect_telegram()
        
        if not telegram_connected:
            logger.error("Failed to connect to Telegram. Exiting.")
            return
        
        # Test recent messages first
        await self.test_recent_messages()
        
        # Connect to Quotex (optional in test mode)
        if TEST_MODE:
            logger.info("Running in TEST MODE - Telegram signals will be parsed but no trades will be placed")
            quotex_connected = True  # Skip Quotex connection in test mode
        else:
            quotex_connected = await self.connect_quotex()
        
        if not quotex_connected and not TEST_MODE:
            logger.error("Failed to connect to Quotex. Exiting.")
            return
        
        # Start signal processing
        await self.process_signals()

async def main():
    bot = TradingBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
