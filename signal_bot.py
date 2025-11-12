# signal_bot.py
import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, field

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from dotenv import load_dotenv

load_dotenv()

# === CONFIG ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_IDS = [int(cid.strip()) for cid in os.getenv("ADMIN_CHAT_IDS", "").split(",") if cid.strip()]
POCKET_OPTION_LINK = os.getenv("POCKET_OPTION_LINK", "https://pocketoption.com/")
PROMO_CODE = os.getenv("PROMO_CODE", "YVE200")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "your_telegram_username")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level="INFO",
)
logger = logging.getLogger(__name__)

# === DATA CLASS ===
@dataclass
class User:
    chat_id: int
    username: str = ""
    verified: bool = False
    pocket_option_id: str = ""

# === STORAGE ===
class Storage:
    def __init__(self):
        self.users: Dict[int, User] = {}

    def get_user(self, chat_id: int) -> User:
        if chat_id not in self.users:
            self.users[chat_id] = User(chat_id=chat_id)
        return self.users[chat_id]

# === TELEGRAM BOT ===
class TelegramBot:
    def __init__(self, app: Application, storage: Storage):
        self.app = app
        self.storage = storage

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = user.id
        db_user = self.storage.get_user(chat_id)
        db_user.username = user.username or str(user.id)
        await self.main_menu(update)

    async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE = None):
        query = update.callback_query if update.callback_query else None
        if query:
            await query.answer()

        chat_id = update.effective_chat.id
        user = self.storage.get_user(chat_id)

        # 👑 ADMIN: Show full menu + admin panel
        if chat_id in ADMIN_CHAT_IDS:
            text = "👑 *BOSS MENU*\n\nYou are the owner!\nAccess everything below:"
            keyboard = [
                [InlineKeyboardButton("GET SIGNAL 📈", callback_data="get_signal")],
                [InlineKeyboardButton("INSTRUCTION 📄", callback_data="instruction")],
                [InlineKeyboardButton("SUPPORT 🆘", callback_data="support")],
                [InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if query:
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
            return

        # 🚪 NON-ADMIN: Show registration if not verified
        if not user.verified:
            text = (
                "🔒 *Access Restricted*\n\n"
                f"To use signals:\n"
                f"1. Register at [Pocket Option]({POCKET_OPTION_LINK}) with promo: `{PROMO_CODE}`\n"
                f"2. Deposit $10+\n"
                f"3. Send your *Pocket Option ID* here\n\n"
                "✅ I'll verify you manually!"
            )
            keyboard = [
                [InlineKeyboardButton("🔗 Register Now", url=POCKET_OPTION_LINK)],
                [InlineKeyboardButton("Contact Support", callback_data="support")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if query:
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
            return

        # 🟢 VERIFIED USER: Show normal menu
        text = "💎 *MAIN MENU*\n\nChoose an option:"
        keyboard = [
            [InlineKeyboardButton("GET SIGNAL 📈", callback_data="get_signal")],
            [InlineKeyboardButton("INSTRUCTION 📄", callback_data="instruction"),
             InlineKeyboardButton("SUPPORT 🆘", callback_data="support")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if query:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    async def get_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        text = (
            f"🚀 *GET YOUR SIGNALS*\n\n"
            f"1. Register at [Pocket Option]({POCKET_OPTION_LINK})\n"
            f"2. Use promo code: `{PROMO_CODE}`\n"
            f"3. Deposit $10+\n"
            f"4. Send your Pocket Option ID to me\n\n"
            "I'll verify you and unlock signals!"
        )
        keyboard = [
            [InlineKeyboardButton("🔗 Register Now", url=POCKET_OPTION_LINK)],
            [InlineKeyboardButton("Back «", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    async def instruction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        text = (
            "📘 *INSTRUCTION*\n\n"
            "📌 How to use:\n"
            f"1. Register at [Pocket Option]({POCKET_OPTION_LINK}) with promo `{PROMO_CODE}`\n"
            "2. Deposit $10+\n"
            "3. Send your ID to me\n"
            "4. Once verified, use signals to trade\n\n"
            "⚠️ Never risk more than 5% per trade."
        )
        keyboard = [[InlineKeyboardButton("Back «", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    async def support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        text = "🆘 *SUPPORT*\n\nNeed help? Message me directly!"
        keyboard = [
            [InlineKeyboardButton("💬 Message Me", url=f"https://t.me/{SUPPORT_USERNAME}")],
            [InlineKeyboardButton("Back «", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if query:
            await query.answer()
        chat_id = update.effective_chat.id
        if chat_id not in ADMIN_CHAT_IDS:
            await update.message.reply_text("🚫 Access denied.")
            return
        text = "🔐 *Admin Panel*\n\nManage users:"
        keyboard = [[InlineKeyboardButton("👥 View Users", callback_data="view_users")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if query:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    async def view_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        text = "👥 *Users*:\n"
        for uid, user in self.storage.users.items():
            status = "✅ Verified" if user.verified else "⏳ Pending"
            text += f"\n{uid} ({user.username}) — {status}"
        keyboard = [[InlineKeyboardButton("« Back", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    async def handle_user_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        text = update.message.text.strip()
        user = self.storage.get_user(chat_id)
        if not user.verified:
            user.pocket_option_id = text
            # Notify admin
            for admin_id in ADMIN_CHAT_IDS:
                await self.app.bot.send_message(
                    admin_id,
                    f"🆕 New ID from {chat_id}:\n{text}"
                )
            await update.message.reply_text("✅ ID received! I'll verify you soon.")

# === MAIN ===
async def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in secrets")

    storage = Storage()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    bot_interface = TelegramBot(app, storage)

    app.add_handler(CommandHandler("start", bot_interface.start))
    app.add_handler(CommandHandler("admin", bot_interface.admin_panel))
    app.add_handler(CallbackQueryHandler(bot_interface.main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(bot_interface.get_signal, pattern="^get_signal$"))
    app.add_handler(CallbackQueryHandler(bot_interface.instruction, pattern="^instruction$"))
    app.add_handler(CallbackQueryHandler(bot_interface.support, pattern="^support$"))
    app.add_handler(CallbackQueryHandler(bot_interface.admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(bot_interface.view_users, pattern="^view_users$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_interface.handle_user_id))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("✅ Bot is running...")

    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
