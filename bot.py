import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import asyncio
import logging

logging.basicConfig(level=logging.INFO)


# ====== TOKEN BOT ======
TOKEN = "8316724268:AAFK_45LrEPum0Ub4qQYNONMy9zQ0hGSfVM"

# ====== FILE PENYIMPAN DATA ======
DATA_FILE = "data.json"
UPLOAD_DIR = "uploads"

# Pastikan folder uploads ada
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ====== Fungsi bantu ======
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ====== /start ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Aku bot penyimpan data dan file 🤖\n\n"
        "Perintah yang tersedia:\n"
        "/setdata - Simpan data diri\n"
        "/getdata - Lihat data diri\n"
        "/upload - Kirim file ke bot untuk disimpan"
    )

# ====== /setdata ======
async def set_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Silakan kirim datamu dengan format:\n\nNama, Umur, Email")
    return 1

async def save_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.message.from_user.id)

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
        await update.message.reply_text(f"✅ Data kamu disimpan!\nNama: {nama}\nUmur: {umur}\nEmail: {email}")
    except ValueError:
        await update.message.reply_text("❌ Format salah! Gunakan format: Nama, Umur, Email")

    return ConversationHandler.END

# ====== /getdata ======
async def get_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    data = load_data()

    if user_id in data:
        user = data[user_id]
        msg = f"📋 Data Kamu:\n"
        msg += f"Nama: {user.get('nama', '-')}\n"
        msg += f"Umur: {user.get('umur', '-')}\n"
        msg += f"Email: {user.get('email', '-')}\n"

        # Jika ada file tersimpan
        if "files" in user and user["files"]:
            msg += f"\n📁 File yang kamu simpan ({len(user['files'])}):"
            for idx, f in enumerate(user["files"], 1):
                msg += f"\n{idx}. {f}"
        else:
            msg += "\nBelum ada file tersimpan."

        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("❌ Kamu belum menyimpan data. Gunakan /setdata dulu.")

# ====== /upload ======
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Silakan kirim file (foto, PDF, atau dokumen).")
    return 2

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    data = load_data()

    # Cek apakah user punya data sebelumnya
    if user_id not in data:
        data[user_id] = {}

    # Ambil file
    file_name = None
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

    # Unduh file ke folder uploads/
    tg_file = await context.bot.get_file(file_id)
    file_path = os.path.join(UPLOAD_DIR, file_name)
    await tg_file.download_to_drive(file_path)

    # Simpan path file ke data.json
    if "files" not in data[user_id]:
        data[user_id]["files"] = []
    data[user_id]["files"].append(file_path)

    save_data(data)

    await update.message.reply_text(f"✅ File '{file_name}' berhasil disimpan!")
    return ConversationHandler.END

# ====== /get ======
async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    data = load_data()

    if len(context.args) == 0:
        await update.message.reply_text("⚠️ Gunakan format: /get nama_file (contoh: /get laporan.pdf)")
        return

    file_name = " ".join(context.args)
    if user_id not in data or "files" not in data[user_id]:
        await update.message.reply_text("❌ Kamu belum mengupload file apa pun.")
        return

    # Cari file berdasarkan nama
    user_files = data[user_id]["files"]
    found_file = None
    for path in user_files:
        if path.endswith(file_name):
            found_file = path
            break

    if found_file and os.path.exists(found_file):
        await update.message.reply_document(document=open(found_file, "rb"))
    else:
        await update.message.reply_text("⚠️ File tidak ditemukan.")


# ====== MAIN ======
def main():
    app = Application.builder().token(TOKEN).connect_timeout(30).read_timeout(30).build()

    # Conversation untuk set data
    conv_data = ConversationHandler(
        entry_points=[CommandHandler("setdata", set_data)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_user_data)]},
        fallbacks=[],
    )

    # Conversation untuk upload file
    conv_upload = ConversationHandler(
        entry_points=[CommandHandler("upload", upload_command)],
        states={2: [MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file)]},
        fallbacks=[],
    )

    # Handler utama
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getdata", get_data))
    app.add_handler(CommandHandler("get", get_file))
    app.add_handler(conv_data)
    app.add_handler(conv_upload)

    print("🤖 Bot penyimpan data dan file berjalan...")
    try:
        app.run_polling()
    except Exception as e:
        print(f"❌ Terjadi kesalahan koneksi: {e}")
        asyncio.run(asyncio.sleep(5))
        print("🔁 Mencoba ulang...")
        main()

if __name__ == "__main__":
    main()
