import os
import json
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# ==================== KONFIGURASI DASAR ====================
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN", "MASUKKAN_TOKEN_BOT_KAMU_DI_SINI")

DATA_FILE = "data.json"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==================== FUNGSI BANTU ====================
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ==================== HANDLER /start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Halo! Aku bot penyimpan data dan file.\n\n"
        "Perintah yang bisa kamu gunakan:\n"
        "📝 /setdata - Simpan data diri kamu\n"
        "📋 /getdata - Lihat data yang tersimpan\n"
        "📎 /upload - Upload file untuk disimpan\n"
        "📂 /get nama_file - Ambil file yang pernah diupload"
    )


# ==================== HANDLER /setdata ====================
async def set_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Silakan kirim data kamu dalam format:\n\n`Nama, Umur, Email`", parse_mode="Markdown")
    return 1

async def save_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text
    try:
        nama, umur, email = [x.strip() for x in text.split(",")]
        data = load_data()
        if user_id not in data:
            data[user_id] = {}

        data[user_id].update({
            "nama": nama,
            "umur": umur,
            "email": email
        })
        save_data(data)
        await update.message.reply_text(f"✅ Data kamu berhasil disimpan!\n\nNama: {nama}\nUmur: {umur}\nEmail: {email}")
    except ValueError:
        await update.message.reply_text("❌ Format salah! Gunakan format: `Nama, Umur, Email`", parse_mode="Markdown")

    return ConversationHandler.END


# ==================== HANDLER /getdata ====================
async def get_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    data = load_data()

    if user_id in data:
        user = data[user_id]
        msg = f"📋 Data kamu:\n\n"
        msg += f"Nama: {user.get('nama', '-')}\n"
        msg += f"Umur: {user.get('umur', '-')}\n"
        msg += f"Email: {user.get('email', '-')}\n"

        if "files" in user and user["files"]:
            msg += f"\n📁 File tersimpan ({len(user['files'])}):"
            for i, f in enumerate(user["files"], 1):
                msg += f"\n{i}. {os.path.basename(f)}"
        else:
            msg += "\nBelum ada file tersimpan."

        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("⚠️ Kamu belum menyimpan data. Gunakan /setdata dulu.")


# ==================== HANDLER /upload ====================
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📤 Silakan kirim file (foto, dokumen, PDF, dll).")
    return 2

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    data = load_data()

    if user_id not in data:
        data[user_id] = {}

    file_name = None
    file_id = None

    if update.message.document:
        file = update.message.document
        file_name = file.file_name
        file_id = file.file_id
    elif update.message.photo:
        file = update.message.photo[-1]
        file_name = f"photo_{user_id}.jpg"
        file_id = file.file_id
    else:
        await update.message.reply_text("❌ Jenis file tidak didukung.")
        return ConversationHandler.END

    tg_file = await context.bot.get_file(file_id)
    file_path = os.path.join(UPLOAD_DIR, file_name)
    await tg_file.download_to_drive(file_path)

    if "files" not in data[user_id]:
        data[user_id]["files"] = []
    data[user_id]["files"].append(file_path)
    save_data(data)

    await update.message.reply_text(f"✅ File `{file_name}` berhasil disimpan!", parse_mode="Markdown")
    return ConversationHandler.END


# ==================== HANDLER /get ====================
async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    data = load_data()

    if len(context.args) == 0:
        await update.message.reply_text("⚠️ Gunakan format: `/get nama_file`", parse_mode="Markdown")
        return

    file_name = " ".join(context.args)
    if user_id not in data or "files" not in data[user_id]:
        await update.message.reply_text("❌ Kamu belum upload file apa pun.")
        return

    found_file = None
    for path in data[user_id]["files"]:
        if os.path.basename(path) == file_name:
            found_file = path
            break

    if found_file and os.path.exists(found_file):
        await update.message.reply_document(document=open(found_file, "rb"))
    else:
        await update.message.reply_text("⚠️ File tidak ditemukan.")


# ==================== MAIN ====================
async def main():
    app = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .build()
    )

    conv_data = ConversationHandler(
        entry_points=[CommandHandler("setdata", set_data)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_user_data)]},
        fallbacks=[],
    )

    conv_upload = ConversationHandler(
        entry_points=[CommandHandler("upload", upload_command)],
        states={2: [MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file)]},
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getdata", get_data))
    app.add_handler(CommandHandler("get", get_file))
    app.add_handler(conv_data)
    app.add_handler(conv_upload)

    print("🤖 Bot sedang berjalan 24 jam nonstop...")
    await app.run_polling(close_loop=False)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot dimatikan secara manual.")
