from telethon.sync import TelegramClient
from telethon import functions, types

import asyncio
from pyquotex.config import credentials
from pyquotex.stable_api import Quotex

from flask import Flask, render_template, request, jsonify

import datetime
import pandas as pd

from functions import fetch_channel_messages

# Replace with your API ID and hash
api_id = 26500165
api_hash = '119c983b9aee401c4411b140bf11f463'
session_name = 'my_session' # Or use a StringSession, etc.

chat = "https://t.me/+MJeq2boHo5gxNGVh"

app = Flask(__name__)


# Home page (renders template if you add templates/index.html)
@app.route("/")
def index():
    return render_template("index.html")



@app.route("/scrape_gram", methods=["GET"])
def scrape_gram():

	data = fetch_channel_messages(chat, session_name, api_id, api_hash)

	return jsonify(data), 200


@app.route("/place_order", methods=["POST"])
def place_order():
    amount = request.form.get("amount")
    asset = request.form.get("asset")
    direction = request.form.get("direction")
    duration = request.form.get("duration")

    async def place_order_async():
        client = Quotex(email="courageokaka9@gmail.com", password="quotexPass9@", lang="en")

        check_connect, message = await client.connect()

        print(check_connect)
        if check_connect:
            # Use the variables from outer scope
            duration_seconds = int(duration)  # in seconds
            balance = await client.get_balance()
            initial_balance = balance
            martingale_quantity = 2
            print("Initial Balance: ", balance)
            asset_name, asset_data = await client.get_available_asset(asset, force_open=True)

            
            print(f"Betting ${amount} on asset {asset_name} in the {direction} direction for {int(duration_seconds/60)}m \n")
            status, buy_info = await client.buy(amount, asset_name, direction, duration_seconds)
            print(status, buy_info)
            return {"status": "success", "message": "Order placed successfully!"}
        else:
            return {"status": "error", "message": "Failed to connect to Quotex"}

    # Run the async function in a sync context
    result = asyncio.run(place_order_async())
    return jsonify(result), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
