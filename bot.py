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

# ---------------- TOKEN ----------------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN is not set!")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

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

# ---------------- START ----------------
def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text(
        "🚀 Welcome to Luggage Connect\n\n"
        "Use /traveler → register trip\n"
        "Use /sender → send package"
    )

# ---------------- TRAVELER FLOW ----------------
def traveler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text("🌍 Enter departure country:")
    return TR_FROM

def tr_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["from"] = update.message.text
    update.message.reply_text("🎯 Enter destination country:")
    return TR_TO

def tr_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["to"] = update.message.text
    update.message.reply_text("📅 Enter date (YYYY-MM-DD):")
    return TR_DATE

def tr_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["date"] = update.message.text
    update.message.reply_text("🧳 Free luggage space (kg):")
    return TR_SPACE

def tr_space(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["space"] = update.message.text
    update.message.reply_text("📱 Enter phone number or type skip:")
    return TR_PHONE

def tr_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    if phone.lower() == "skip":
        phone = "Not provided"

    username = update.effective_user.username
    username = f"@{username}" if username else "No username"

    conn = sqlite3.connect("luggage.db")
    c = conn.cursor()

    c.execute("""
    INSERT INTO trips
    (user_id, username, phone, from_country, to_country, date, space)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        update.effective_user.id,
        username,
        phone,
        context.user_data["from"],
        context.user_data["to"],
        context.user_data["date"],
        int(context.user_data["space"])
    ))

    trip_id = c.lastrowid
    conn.commit()
    conn.close()

    update.message.reply_text(
        f"✅ Trip Registered!\n\n"
        f"Trip ID: T{trip_id:03d}\n"
        f"{context.user_data['from']} → {context.user_data['to']}\n"
        f"Space: {context.user_data['space']} kg"
    )

    return ConversationHandler.END

# ---------------- SENDER FLOW ----------------
def sender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text("📦 Enter package origin country:")
    return SD_FROM

def sd_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["s_from"] = update.message.text
    update.message.reply_text("🎯 Enter destination country:")
    return SD_TO

def sd_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["s_to"] = update.message.text
    update.message.reply_text("⚖️ Enter weight (kg):")
    return SD_WEIGHT

def sd_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["weight"] = int(update.message.text)
    update.message.reply_text("📝 Describe item:")
    return SD_DESC

def sd_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["desc"] = update.message.text
    update.message.reply_text("📱 Enter phone number or type skip:")
    return SD_PHONE

def sd_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    if phone.lower() == "skip":
        phone = "Not provided"

    username = update.effective_user.username
    username = f"@{username}" if username else "No username"

    conn = sqlite3.connect("luggage.db")
    c = conn.cursor()

    c.execute("""
    INSERT INTO packages
    (user_id, username, phone, from_country, to_country, weight, description)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        update.effective_user.id,
        username,
        phone,
        context.user_data["s_from"],
        context.user_data["s_to"],
        context.user_data["weight"],
        context.user_data["desc"]
    ))

    # MATCHING
    c.execute("""
    SELECT username, phone, date, space
    FROM trips
    WHERE from_country=?
    AND to_country=?
    AND space>=?
    ORDER BY id DESC
    LIMIT 1
    """, (
        context.user_data["s_from"],
        context.user_data["s_to"],
        context.user_data["weight"]
    ))

    match = c.fetchone()

    conn.commit()
    conn.close()

    if match:
        update.message.reply_text(
            "✅ MATCH FOUND!\n\n"
            f"Traveler: {match[0]}\n"
            f"Phone: {match[1]}\n"
            f"Date: {match[2]}\n"
            f"Available Space: {match[3]} kg"
        )
    else:
        update.message.reply_text("❌ No match found yet.")

    return ConversationHandler.END

# ---------------- CANCEL ----------------
def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

# ---------------- INIT ----------------
init_db()

application = Application.builder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(ConversationHandler(
    entry_points=[CommandHandler("traveler", traveler)],
    states={
        TR_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, tr_from)],
        TR_TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, tr_to)],
        TR_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tr_date)],
        TR_SPACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tr_space)],
        TR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tr_phone)],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
))
application.add_handler(ConversationHandler(
    entry_points=[CommandHandler("sender", sender)],
    states={
        SD_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, sd_from)],
        SD_TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, sd_to)],
        SD_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sd_weight)],
        SD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, sd_desc)],
        SD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sd_phone)],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
))

# ---------------- FLASK APP ----------------
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

# ⭐ CORRECT WEBHOOK HANDLER FOR PTB v20
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.process_update(update)
    return "OK", 200

# ---------------- RUN ----------------
async def setup_webhook():
    await application.bot.delete_webhook()
    if WEBHOOK_URL:
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

if __name__ == "__main__":
    asyncio.run(setup_webhook())
    application.initialize()
    application.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
