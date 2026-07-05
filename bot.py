# main.py
import os
import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ConversationHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN=os.environ["BOT_TOKEN"]
WEBHOOK_URL=os.environ["WEBHOOK_URL"]

TR_FROM,TR_TO,TR_DATE,TR_SPACE,TR_PHONE=range(5)
SD_FROM,SD_TO,SD_WEIGHT,SD_DESC,SD_PHONE=range(5,10)

def init_db():
    con=sqlite3.connect("luggage.db")
    c=con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS trips(id INTEGER PRIMARY KEY,user_id INTEGER,username TEXT,phone TEXT,from_country TEXT,to_country TEXT,date TEXT,space INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS packages(id INTEGER PRIMARY KEY,user_id INTEGER,username TEXT,phone TEXT,from_country TEXT,to_country TEXT,weight INTEGER,description TEXT)")
    con.commit(); con.close()

async def start(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Welcome!\n/traveler\n/sender")

async def traveler(update,ctx):
    await update.message.reply_text("Departure country:")
    return TR_FROM
async def tr_from(update,ctx):
    ctx.user_data["from"]=update.message.text; await update.message.reply_text("Destination:"); return TR_TO
async def tr_to(update,ctx):
    ctx.user_data["to"]=update.message.text; await update.message.reply_text("Date YYYY-MM-DD:"); return TR_DATE
async def tr_date(update,ctx):
    ctx.user_data["date"]=update.message.text; await update.message.reply_text("Space kg:"); return TR_SPACE
async def tr_space(update,ctx):
    ctx.user_data["space"]=int(update.message.text); await update.message.reply_text("Phone or skip:"); return TR_PHONE
async def tr_phone(update,ctx):
    phone=update.message.text
    if phone.lower()=="skip": phone="Not provided"
    u=update.effective_user
    con=sqlite3.connect("luggage.db"); c=con.cursor()
    c.execute("INSERT INTO trips(user_id,username,phone,from_country,to_country,date,space) VALUES(?,?,?,?,?,?,?)",
              (u.id, "@"+u.username if u.username else "No username", phone, ctx.user_data["from"],ctx.user_data["to"],ctx.user_data["date"],ctx.user_data["space"]))
    tid=c.lastrowid; con.commit(); con.close()
    await update.message.reply_text(f"Trip registered T{tid:03d}")
    return ConversationHandler.END

async def sender(update,ctx):
    await update.message.reply_text("Origin:"); return SD_FROM
async def sd_from(update,ctx):
    ctx.user_data["sf"]=update.message.text; await update.message.reply_text("Destination:"); return SD_TO
async def sd_to(update,ctx):
    ctx.user_data["st"]=update.message.text; await update.message.reply_text("Weight:"); return SD_WEIGHT
async def sd_weight(update,ctx):
    ctx.user_data["w"]=int(update.message.text); await update.message.reply_text("Description:"); return SD_DESC
async def sd_desc(update,ctx):
    ctx.user_data["d"]=update.message.text; await update.message.reply_text("Phone or skip:"); return SD_PHONE
async def sd_phone(update,ctx):
    phone=update.message.text
    if phone.lower()=="skip": phone="Not provided"
    u=update.effective_user
    con=sqlite3.connect("luggage.db"); c=con.cursor()
    c.execute("INSERT INTO packages(user_id,username,phone,from_country,to_country,weight,description) VALUES(?,?,?,?,?,?,?)",
              (u.id,"@"+u.username if u.username else "No username",phone,ctx.user_data["sf"],ctx.user_data["st"],ctx.user_data["w"],ctx.user_data["d"]))
    c.execute("SELECT username,phone,date,space FROM trips WHERE from_country=? AND to_country=? AND space>=? ORDER BY id DESC LIMIT 1",
              (ctx.user_data["sf"],ctx.user_data["st"],ctx.user_data["w"]))
    m=c.fetchone(); con.commit(); con.close()
    if m: await update.message.reply_text(f"Match!\nTraveler:{m[0]}\nPhone:{m[1]}\nDate:{m[2]}\nSpace:{m[3]}")
    else: await update.message.reply_text("No match yet.")
    return ConversationHandler.END

async def cancel(update,ctx):
    await update.message.reply_text("Cancelled"); return ConversationHandler.END

application=Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start",start))
application.add_handler(ConversationHandler(entry_points=[CommandHandler("traveler",traveler)],states={
TR_FROM:[MessageHandler(filters.TEXT & ~filters.COMMAND,tr_from)],
TR_TO:[MessageHandler(filters.TEXT & ~filters.COMMAND,tr_to)],
TR_DATE:[MessageHandler(filters.TEXT & ~filters.COMMAND,tr_date)],
TR_SPACE:[MessageHandler(filters.TEXT & ~filters.COMMAND,tr_space)],
TR_PHONE:[MessageHandler(filters.TEXT & ~filters.COMMAND,tr_phone)]},fallbacks=[CommandHandler("cancel",cancel)]))
application.add_handler(ConversationHandler(entry_points=[CommandHandler("sender",sender)],states={
SD_FROM:[MessageHandler(filters.TEXT & ~filters.COMMAND,sd_from)],
SD_TO:[MessageHandler(filters.TEXT & ~filters.COMMAND,sd_to)],
SD_WEIGHT:[MessageHandler(filters.TEXT & ~filters.COMMAND,sd_weight)],
SD_DESC:[MessageHandler(filters.TEXT & ~filters.COMMAND,sd_desc)],
SD_PHONE:[MessageHandler(filters.TEXT & ~filters.COMMAND,sd_phone)]},fallbacks=[CommandHandler("cancel",cancel)]))

@asynccontextmanager
async def lifespan(app):
    init_db()
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")
    yield
    await application.stop()
    await application.shutdown()

app=FastAPI(lifespan=lifespan)

@app.get("/")
async def root(): return {"status":"ok"}

@app.post("/{token}")
async def webhook(token:str, request:Request):
    if token!=TOKEN: return {"ok":False}
    update=Update.de_json(await request.json(), application.bot)
    await application.process_update(update)
    return {"ok":True}
