import sqlite3
import os
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN is not set!")

# ---------------- STATES ----------------
TR_FROM, TR_TO, TR_DATE, TR_SPACE, TR_PHONE = range(5)
SD_FROM, SD_TO, SD_WEIGHT, SD_DESC, SD_PHONE = range(5, 10)

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("luggage.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        phone TEXT,
        from_country TEXT,
        to_country TEXT,
        date TEXT,
        space INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS packages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        phone TEXT,
        from_country TEXT,
        to_country TEXT,
        weight INTEGER,
        description TEXT
    )
    """)

    conn.commit()
    conn.close()

# ---------------- TELEGRAM HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Welcome to Luggage Connect\n\n"
        "Use /traveler → register trip\n"
        "Use /sender → send package"
    )

# (Your traveler + sender handlers stay EXACTLY the same)
# I am not rewriting them here to keep the answer short.
# Just paste all your handlers exactly as they are.

# ---------------- INIT BOT ----------------
init_db()

application = Application.builder().token(TOKEN).build()

# Add your handlers
application.add_handler(CommandHandler("start", start))
# Add traveler_conv and sender_conv exactly as before

# ---------------- FLASK SERVER ----------------
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.process_update(update)
    return "OK", 200

# ---------------- START WEBHOOK ----------------
if __name__ == "__main__":
    # Remove old webhook
    application.bot.delete_webhook()

    # Set new webhook
    RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
    application.bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")

    # Start Flask server
    app.run(host="0.0.0.0", port=10000)

