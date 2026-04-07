import sqlite3
import time
from telegram import *
from telegram.ext import *

TOKEN = "8778331918:AAE5uzWflufC_AkLDz62m4A80BsbIZoZtvI"
ADMIN_ID = 8289491009
BOT_USERNAME = "YourBotUsername"

CHANNELS = ["@Khanda_koor", "@Nice_image1", "@afghan_reward"]

# -------- DATABASE --------
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
balance REAL DEFAULT 0,
phone TEXT,
joined INTEGER DEFAULT 0,
last_bonus INTEGER DEFAULT 0,
weekly_bonus INTEGER DEFAULT 0,
invited_by INTEGER DEFAULT 0
)
""")
conn.commit()

# -------- FORCE JOIN --------
async def is_joined(update, context):
    user_id = update.effective_user.id

    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# -------- START --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    cursor.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (uid,))
    conn.commit()

    # Invite System
    if context.args:
        try:
            ref = int(context.args[0])
            if ref != uid:
                cursor.execute("SELECT invited_by FROM users WHERE id=?", (uid,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute("UPDATE users SET invited_by=? WHERE id=?", (ref, uid))
                    cursor.execute("UPDATE users SET balance=balance+2 WHERE id=?", (ref,))
                    conn.commit()
        except:
            pass

    # Force Join
    if not await is_joined(update, context):
        buttons = []
        for ch in CHANNELS:
            buttons.append([InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch[1:]}")])

        await update.message.reply_text(
            "⚠️ مهرباني وکړئ لومړی لاندې چینلونو ته Join شئ بیا /start ولیکئ",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    kb = [
        ["📊 حالت", "🎁 بونس"],
        ["👥 دعوت", "💰 پیسې زیاتول"],
        ["📞 نمبر داخلول", "📥 ایزیلوډ"],
        ["ℹ️ د ربات په اړه"]
    ]

    await update.message.reply_text("🏠 اصلي مینو", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))


# -------- STATUS --------
async def status(update, context):
    user = update.effective_user
    cursor.execute("SELECT balance FROM users WHERE id=?", (user.id,))
    bal = cursor.fetchone()[0]

    txt = f"""
🤵🏻‍♂️استعمالوونکی = {user.first_name}

💳 ایډي کارن : {user.id}
💵ستاسو پيسو اندازه= {bal} AFN

🔗 د بیلانس زیاتولو لپاره 👥 کسان دعوت کړی،
بوټ ته!
"""
    await update.message.reply_text(txt)


# -------- BONUS --------
async def bonus(update, context):
    uid = update.effective_user.id
    now = int(time.time())

    cursor.execute("SELECT last_bonus, weekly_bonus FROM users WHERE id=?", (uid,))
    last, week = cursor.fetchone()

    # Daily
    if now - last >= 86400:
        cursor.execute("UPDATE users SET balance=balance+0.5, last_bonus=? WHERE id=?", (now, uid))
        conn.commit()
        await update.message.reply_text("🎁 0.5 AFN Daily Bonus ترلاسه شو!")
    else:
        await update.message.reply_text("⏳ Daily Bonus مخکې اخیستل شوی")

    # Weekly
    if now - week >= 604800:
        cursor.execute("UPDATE users SET balance=balance+5, weekly_bonus=? WHERE id=?", (now, uid))
        conn.commit()
        await update.message.reply_text("🎉 5 AFN Weekly Bonus ترلاسه شو!")


# -------- INVITE --------
async def invite(update, context):
    uid = update.effective_user.id
    link = f"https://t.me/{BOT_USERNAME}?start={uid}"

    await update.message.reply_text(f"""
👥 خپل ځانګړی لینک:

{link}

✔️ هر Invite = 2 AFN
""")


# -------- EASYLOAD --------
async def easyload(update, context):
    uid = update.effective_user.id

    cursor.execute("SELECT balance FROM users WHERE id=?", (uid,))
    bal = cursor.fetchone()[0]

    if bal < 50:
        await update.message.reply_text("⚠️ لږ تر لږه پنځوس افغانۍ بايد په خپل حساب کې ولرئ
