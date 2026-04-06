import sqlite3
from datetime import datetime, timedelta
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

TOKEN = "8778331918:AAE5uzWflufC_AkLDz62m4A80BsblZoZtvI"
ADMIN_ID = 8289491009
BOT_USERNAME = "Afghan_Reward_bot"

# درې چینلونه (Force Join)
FORCE_CHANNELS = ["Afghan_Reward", "Nice_image1", "khanda_koor"]

# DB Setup
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0,
    invites INTEGER DEFAULT 0,
    joined TEXT,
    task_done INTEGER DEFAULT 0,
    phone TEXT,
    last_daily TEXT,
    last_weekly TEXT
)
""")

cursor.execute("CREATE TABLE IF NOT EXISTS withdraw (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, phone TEXT, amount REAL, status TEXT DEFAULT 'pending')")
cursor.execute("CREATE TABLE IF NOT EXISTS rewards (invite REAL, daily REAL, weekly REAL)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")

conn.commit()

# Auto Fix DB
def fix_db():
    cursor.execute("PRAGMA table_info(users)")
    cols = [col[1] for col in cursor.fetchall()]
    
    for col, typ in [("task_done", "INTEGER DEFAULT 0"), ("phone", "TEXT"), ("last_daily", "TEXT"), ("last_weekly", "TEXT")]:
        if col not in cols:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
    conn.commit()

fix_db()

# Default Rewards
cursor.execute("SELECT * FROM rewards")
if not cursor.fetchone():
    cursor.execute("INSERT INTO rewards VALUES (2.0, 0.5, 5.0)")  # invite=2, daily=0.5, weekly=5

conn.commit()

# ==================== MENUS ====================
def main_menu():
    return ReplyKeyboardMarkup([
        ["📊 حالت", "🎁 بونس"],
        ["👥 دعوت", "💰 پیسې زیاتول"],
        ["💳 ایزی لوډ", "📱 نمبر ثبت کړئ"],
        ["ℹ️ د ربات په اړه"]
    ], resize_keyboard=True)

def money_menu():
    return ReplyKeyboardMarkup([
        ["🎯 ټاسکونه", "👥 دعوت"],
        ["🎁 بونس", "🔙 بیرته"]
    ], resize_keyboard=True)

def admin_menu():
    return ReplyKeyboardMarkup([
        ["📊 احصایه", "👥 یوزران"],
        ["📢 برودکاست", "💰 ریوارد کنټرول"],
        ["📣 آټو پوسټ", "⚙️ سیټینګ"],
        ["🔙 بیرته"]
    ], resize_keyboard=True)

# ==================== FORCE JOIN CHECK ====================
async def check_force_join(update, context):
    uid = update.effective_user.id
    for ch in FORCE_CHANNELS:
        try:
            member = await context.bot.get_chat_member(f"@{ch}", uid)
            if member.status not in ["member", "administrator", "creator"]:
                await update.message.reply_text(
                    f"⚠️ لومړی دا چینلونه جوائن کړئ:\n\n" + 
                    "\n".join([f"https://t.me/{c}" for c in FORCE_CHANNELS]) +
                    "\n\nبیا بوټ ته /start وکړئ"
                )
                return False
        except:
            await update.message.reply_text("❌ چینل چک کولو کې ستونزه راغله. وروسته بیا هڅه وکړئ.")
            return False
    return True

# ==================== START ====================
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    cursor.execute("SELECT * FROM users WHERE id=?", (uid,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (id, username, balance, invites, joined, task_done, phone) VALUES (?,?,?,?,?,?,?)",
            (uid, user.username, 0.0, 0, str(datetime.now()), 0, "")
        )
        conn.commit()

    # Force Join Check
    if not await check_force_join(update, context):
        return

    await update.message.reply_text("🎉 ښه راغلاست! بوټ ته بریالۍ داخل شوئ.", reply_markup=main_menu())

# ==================== STATUS ====================
async def status(update, context):
    uid = update.effective_user.id
    cursor.execute("SELECT username, balance FROM users WHERE id=?", (uid,))
    u = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE joined > date('now', '-30 days')")
    monthly = cursor.fetchone()[0]

    msg1 = f"""👤 @{u[0] if u[0] else 'No Username'}
🆔 {uid}
💰 {u[1]:.1f} AFN

👥 ټول یوزران: {total}
📆 Monthly: {monthly}"""

    msg2 = f"""🤵🏻‍♂️ استعمالوونکی = {u[0] if u[0] else 'No Username'}
💳 ایډي کارن : {uid}
💵 ستاسو پيسو اندازه = {u[1]:.1f} AFN

🔗 د بیلانس زیاتولو لپاره [ 👫 کسان ] دعوت کړی، بوټ ته!"""

    await update.message.reply_text(msg1)
    await update.message.reply_text(msg2)

# ==================== INVITE ====================
async def invite(update, context):
    uid = update.effective_user.id
    link = f"https://t.me/{BOT_USERNAME}?start={uid}"

    msg = f"""🔥 خپل دوستان invite کړئ او په هر یو ۲ افغانۍ وګټئ!

👇 ستاسو ځانګړی لینک:
{link}

کله چې یو نوی کس ستاسو لینک په کارولو سره بوټ پرانیزي، تاسو ته ۲ AFN اضافه کیږي."""
    await update.message.reply_text(msg)

# ==================== BONUS ====================
async def give_bonus(update, context, bonus_type):
    uid = update.effective_user.id
    now = datetime.now().isoformat()

    cursor.execute("SELECT last_daily, last_weekly FROM users WHERE id=?", (uid,))
    row = cursor.fetchone()
    last_d, last_w = row if row else (None, None)

    if bonus_type == "daily":
        if last_d and (datetime.now() - datetime.fromisoformat(last_d)) < timedelta(hours=24):
            return await update.message.reply_text("⏰ ورځنۍ بونس سبا بیرته شتون لري!")
        amount = 0.5
        cursor.execute("UPDATE users SET last_daily=? WHERE id=?", (now, uid))
    else:  # weekly
        if last_w and (datetime.now() - datetime.fromisoformat(last_w)) < timedelta(days=7):
            return await update.message.reply_text("⏰ اوونیز بونس ۷ ورځې وروسته بیرته شتون لري!")
        amount = 5.0
        cursor.execute("UPDATE users SET last_weekly=? WHERE id=?", (now, uid))

    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, uid))
    conn.commit()
    await update.message.reply_text(f"🎉 مبارک! تاسو {amount} AFN ترلاسه کړل.")

# ==================== WITHDRAW (ایزی لوډ) ====================
async def easyload(update, context):
    uid = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE id=?", (uid,))
    bal = cursor.fetchone()[0]

    if bal < 50:
        await update.message.reply_text("⚠️ لږ تر لږه ۵۰ افغانۍ باید په خپل حساب کې ولرئ د ایزی لوډ لپاره")
        return

    context.user_data["awaiting_phone"] = True
    await update.message.reply_text("📱 خپل ۱۰ ګڼې نمبر ولیکئ (مثلاً 07xxxxxxxx):")

# ==================== TASKS (پیسې زیاتول) ====================
async def tasks(update, context):
    uid = update.effective_user.id
    if not await check_force_join(update, context):
        return

    cursor.execute("SELECT task_done FROM users WHERE id=?", (uid,))
    done = cursor.fetchone()[0] or 0

    cursor.execute("SELECT value FROM settings WHERE key='task_version'")
    version = int(cursor.fetchone()[0]) if cursor.fetchone() else 1

    if done >= version:
        await update.message.reply_text("✅ تا په بریالۍ توګه ټول ټاسکونه پوره کړل!")
        return

    # Mark as done
    cursor.execute("UPDATE users SET task_done=? WHERE id=?", (version, uid))
    conn.commit()

    await update.message.reply_text("✅ تا په بریالۍ توګه ټول ټاسکونه پوره کړل!")

# ==================== MESSAGE HANDLER ====================
async def handle_message(update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if not await check_force_join(update, context):
        return

    # Phone number input
    if context.user_data.get("awaiting_phone"):
        context.user_data["awaiting_phone"] = False
        if len(text) == 10 and text.isdigit():
            cursor.execute("UPDATE users SET phone=? WHERE id=?", (text, uid))
            conn.commit()
            await update.message.reply_text("✅ ستاسو نمبر په بریالۍ توګه ثبت شو!")
        else:
            await update.message.reply_text("❌ غلط نمبر! دقیقاً ۱۰ ګڼې شمیره ولیکئ.")
        return

    # Main Menu & Sub Menus
    if text == "🔙 بیرته":
        await update.message.reply_text("اصلي مینو", reply_markup=main_menu())

    elif text == "📊 حالت":
        await status(update, context)

    elif text == "👥 دعوت":
        await invite(update, context)

    elif text == "🎁 بونس":
        await update.message.reply_text("🎁 بونس انتخاب کړئ:", reply_markup=ReplyKeyboardMarkup([
            ["🎁 ورځنۍ بونس", "📅 اوونیز بونس"],
            ["🔙 بیرته"]
        ], resize_keyboard=True))

    elif text in ["🎁 ورځنۍ بونس", "ورځنۍ بونس"]:
        await give_bonus(update, context, "daily")

    elif text in ["📅 اوونیز بونس", "اوونیز بونس"]:
        await give_bonus(update, context, "weekly")

    elif text == "💰 پیسې زیاتول":
        await update.message.reply_text("💰 انتخاب وکړئ:", reply_markup=money_menu())

    elif text == "🎯 ټاسکونه":
        await tasks(update, context)

    elif text == "💳 ایزی لوډ":
        await easyload(update, context)

    elif text == "📱 نمبر ثبت کړئ":
        context.user_data["awaiting_phone"] = True
        await update.message.reply_text("📱 خپل ۱۰ ګڼې نمبر ولیکئ:")

    elif text == "/admin" and uid == ADMIN_ID:
        await update.message.reply_text("👑 Admin Panel", reply_markup=admin_menu())

    # Admin Commands (simple version)
    elif uid == ADMIN_ID:
        if text == "📊 احصایه":
            cursor.execute("SELECT COUNT(*) FROM users")
            total = cursor.fetchone()[0]
            await update.message.reply_text(f"📊 ټول یوزران: {total}\nورځني فعال: {total}")  # تاسو کولی شئ نور احصائیه اضافه کړئ

        elif text == "📢 برودکاست":
            await update.message.reply_text("پیغام ولیکئ چې ټولو ته ولیږل شي:")
            context.user_data["broadcast"] = True

    # Broadcast handler (simple)
    if context.user_data.get("broadcast") and uid == ADMIN_ID:
        context.user_data["broadcast"] = False
        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()
        for user_id in users:
            try:
                await context.bot.send_message(user_id[0], text)
            except:
                pass
        await update.message.reply_text("✅ برودکاست واستول شو!")

# ==================== RUN BOT ====================
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", lambda u,c: handle_message(u,c)))  # for safety
    app.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, handle_message))

    print("🚀 بوټ چالان شو...")
    app.run_polling()
