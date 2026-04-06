import sqlite3
from datetime import datetime, timedelta
from telegram import *
from telegram.ext import *

TOKEN = "8778331918:AAE5uzWflufC_AkLDz62m4A80BsbIZoZtvI"
ADMIN_ID = 8289491009
BOT_USERNAME = "Afghan_Reward_bot"

FORCE_CHANNELS = ["Afghan_Reward", "Nice_image1", "khanda_koor"]

# DB
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

# CREATE TABLES
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY,
username TEXT,
balance REAL DEFAULT 0,
invites INTEGER DEFAULT 0,
joined TEXT,
task_done INTEGER DEFAULT 0
)
""")

cursor.execute("CREATE TABLE IF NOT EXISTS bonus (user_id INTEGER, daily TEXT, weekly TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS withdraw (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, phone TEXT, amount REAL, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS rewards (invite REAL, daily REAL, weekly REAL)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT, value INTEGER)")

# 🔥 AUTO FIX DB
def fix_db():
    cursor.execute("PRAGMA table_info(users)")
    cols = [i[1] for i in cursor.fetchall()]

    if "task_done" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN task_done INTEGER DEFAULT 0")

    conn.commit()

fix_db()

# DEFAULT DATA
cursor.execute("SELECT * FROM rewards")
if not cursor.fetchone():
    cursor.execute("INSERT INTO rewards VALUES (2,0.5,5)")

cursor.execute("SELECT * FROM settings WHERE key='task_version'")
if not cursor.fetchone():
    cursor.execute("INSERT INTO settings VALUES ('task_version',1)")

conn.commit()

# MENUS
def main_menu():
    return ReplyKeyboardMarkup([
        ["📊 حالت", "🎁 بونس"],
        ["👥 دعوت", "💰 پیسې زیاتول"],
        ["💳 ایزی لوډ", "ℹ️ د ربات په اړه"]
    ], resize_keyboard=True)

def bonus_menu():
    return ReplyKeyboardMarkup([
        ["🎁 ورځنۍ", "📅 اوونیز"],
        ["🔙 بیرته"]
    ], resize_keyboard=True)

def money_menu():
    return ReplyKeyboardMarkup([
        ["🎯 ټاسکونه", "👥 دعوت"],
        ["🔙 بیرته"]
    ], resize_keyboard=True)

def admin_menu():
    return ReplyKeyboardMarkup([
        ["📊 احصایه", "👥 یوزران"],
        ["📢 برودکاست", "💰 ریوارد کنټرول"],
        ["➕ چینل اضافه", "⚙️ سیټینګ"],
        ["📣 آټو پوسټ", "🔙 بیرته"]
    ], resize_keyboard=True)

# TASK SYSTEM
async def check_tasks(update, context):
    uid = update.effective_user.id

    cursor.execute("SELECT task_done FROM users WHERE id=?", (uid,))
    u = cursor.fetchone()

    cursor.execute("SELECT value FROM settings WHERE key='task_version'")
    v = cursor.fetchone()[0]

    if u and u[0] == v:
        return True

    for ch in FORCE_CHANNELS:
        try:
            m = await context.bot.get_chat_member(f"@{ch}", uid)
            if m.status not in ["member", "administrator", "creator"]:
                await update.message.reply_text(f"📢 دا چینل join کړه:\nhttps://t.me/{ch}")
                return False
        except:
            return False

    cursor.execute("UPDATE users SET task_done=? WHERE id=?", (v, uid))
    conn.commit()

    await update.message.reply_text("✅ تا ټول ټاسکونه پوره کړل!")
    return True

# START
async def start(update, context):
    user = update.effective_user
    uid = user.id

    cursor.execute("SELECT * FROM users WHERE id=?", (uid,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (id,username,balance,invites,joined,task_done) VALUES (?,?,?,?,?,?)",
                       (uid, user.username, 0, 0, str(datetime.now()), 0))
        conn.commit()

    if not await check_tasks(update, context):
        return

    await update.message.reply_text("ښه راغلاست 👋", reply_markup=main_menu())

# STATUS
async def status(update, context):
    uid = update.effective_user.id
    cursor.execute("SELECT username, balance FROM users WHERE id=?", (uid,))
    u = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    msg = f"""👤 @{u[0]}
🆔 {uid}
💰 {u[1]} AFN

👥 ټول یوزران: {total}
📆 Monthly: 380"""
    await update.message.reply_text(msg)

# INVITE
async def invite(update, context):
    uid = update.effective_user.id
    link = f"https://t.me/{BOT_USERNAME}?start={uid}"

    msg = f"""🔥 نوی موقع!

📱 یوازې د ټیلیګرام له لارې پیسې وګټئ 💰

🎯 آسان کارونه + چټک انعام

👇 همدا اوس راشئ:
{link}"""
    await update.message.reply_text(msg)

# BONUS
async def give_bonus(update, context, type_):
    uid = update.effective_user.id
    now = datetime.now()

    cursor.execute("SELECT daily, weekly FROM bonus WHERE user_id=?", (uid,))
    d = cursor.fetchone()

    if not d:
        cursor.execute("INSERT INTO bonus VALUES (?,?,?)", (uid, "", ""))
        conn.commit()
        d = ("", "")

    last = d[0] if type_ == "daily" else d[1]

    if last:
        last = datetime.fromisoformat(last)
        if type_ == "daily" and now - last < timedelta(days=1):
            return await update.message.reply_text("⏰ سبا بیا")
        if type_ == "weekly" and now - last < timedelta(days=7):
            return await update.message.reply_text("⏰ وروسته بیا")

    cursor.execute("SELECT invite, daily, weekly FROM rewards")
    r = cursor.fetchone()

    amount = r[1] if type_ == "daily" else r[2]

    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, uid))

    if type_ == "daily":
        cursor.execute("UPDATE bonus SET daily=? WHERE user_id=?", (now.isoformat(), uid))
    else:
        cursor.execute("UPDATE bonus SET weekly=? WHERE user_id=?", (now.isoformat(), uid))

    conn.commit()
    await update.message.reply_text(f"🎉 {amount} AFN")

# WITHDRAW
async def withdraw(update, context):
    uid = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE id=?", (uid,))
    bal = cursor.fetchone()[0]

    if bal < 50:
        return await update.message.reply_text("⚠️ لږ تر لږه 50 افغانۍ باید په خپل حساب کې ولرئ")

    context.user_data["wd"] = True
    await update.message.reply_text("📱 خپل نمبر ولیکه")

# ADMIN
async def admin(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("👑 Admin Panel", reply_markup=admin_menu())

# MESSAGE HANDLER
async def msg(update, context):
    uid = update.effective_user.id
    t = update.message.text

    if not await check_tasks(update, context):
        return

    if t == "🔙 بیرته":
        return await update.message.reply_text("اصلي مینو", reply_markup=main_menu())

    if context.user_data.get("wd"):
        context.user_data["wd"] = False
        cursor.execute("SELECT balance FROM users WHERE id=?", (uid,))
        bal = cursor.fetchone()[0]

        cursor.execute("INSERT INTO withdraw (user_id, phone, amount, status) VALUES (?,?,?,?)",
                       (uid, t, bal, "pending"))
        conn.commit()

        await context.bot.send_message(ADMIN_ID, f"💳 Withdraw\n{uid}\n{t}\n{bal}")
        return await update.message.reply_text("✔️ واستول شو")

    if t == "📊 حالت": await status(update, context)
    elif t == "👥 دعوت": await invite(update, context)
    elif t == "🎁 بونس": await update.message.reply_text("انتخاب:", reply_markup=bonus_menu())
    elif t == "🎁 ورځنۍ": await give_bonus(update, context, "daily")
    elif t == "📅 اوونیز": await give_bonus(update, context, "weekly")

    elif t == "💰 پیسې زیاتول":
        await update.message.reply_text("انتخاب:", reply_markup=money_menu())

    elif t == "🎯 ټاسکونه":
        await update.message.reply_text("📢 چینلونه join کړه")

    elif t == "💳 ایزی لوډ": await withdraw(update, context)

    elif t == "ℹ️ د ربات په اړه":
        await update.message.reply_text("""🔥 اوس له ټیلیګرام څخه پیسې وګټئ زموږ د بوټ په مرسته!

💸 ملګري Invite کړئ  
🎁 ورځنۍ او اوونیز بونس واخلئ  
🎯 ټاسکونه ترسره کړئ او عاید ترلاسه کړئ  

🇦🇫 دا ربات د افغانانو لپاره جوړ شوی""")

    elif t == "/admin":
        await admin(update, context)

# RUN
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(MessageHandler(filters.TEXT, msg))

print("Bot Running...")
app.run_polling()
