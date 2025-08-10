from telethon.sync import TelegramClient
from telethon import functions, types

import asyncio
from pyquotex.config import credentials
from pyquotex.stable_api import Quotex

import datetime

api_id = 26500165
api_hash = '119c983b9aee401c4411b140bf11f463'
session_name = 'my_session' # Or use a StringSession, etc.
chat = "https://t.me/+MJeq2boHo5gxNGVh"

def fetch_channel_messages(chat, session_name, api_id, api_hash):
    async def fetch_messages_async():
        # Replace with your API ID and hash
        data_list = []
        async with TelegramClient(session_name, api_id, api_hash) as client:
            async for message in client.iter_messages(chat, offset_date=datetime.date(2025, 8,9), reverse=True, limit=20):
                data = {"date": message.date, "text": message.text}
                data_list.append(data)

        if len(data_list) > 0:
            return {"status": "success", "message": "Messages fetched successfully", "data": data_list}
        else:
            return {"status": "error", "message": "No messages found"}

    # Run the async function in a sync context
    return asyncio.run(fetch_messages_async())


# print(fetch_channel_messages(chat, session_name, api_id, api_hash))

