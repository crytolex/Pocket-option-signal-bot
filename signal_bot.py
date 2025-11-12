# signal_bot.py
import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json
import csv

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
import pandas as pd
import numpy as np

from dotenv import load_dotenv

load_dotenv()

# === CONFIG ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_IDS = [int(cid.strip()) for cid in os.getenv("ADMIN_CHAT_IDS", "").split(",") if cid.strip()]
POCKET_OPTION_LINK = os.getenv("POCKET_OPTION_LINK", "https://pocketoption.com/")
PROMO_CODE = os.getenv("PROMO_CODE", "YVE200")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "your_telegram_username")  # Change this!

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level="INFO",
)
logger = logging.getLogger(__name__)

# === DATA MODELS ===
@dataclass
class User:
    chat_id: int
    username: str = ""
    role: str = "guest"
    subscribed_pairs: List[str] = field(default_factory=list)
    verified: bool = False
    pocket_option_id: str = ""
    language: str = "en"

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
        db_user.language = "en"
        await self.main_menu(update)

    async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE = None):
        query = update.callback_query if update.callback_query else None
        if query:
            await query.answer()

        chat_id = update.effective_chat.id
        user = self.storage.get_user(chat_id)

        if not user.verified and chat_id not in ADMIN_CHAT_IDS:
            text = (
                "🔒 *Access Restricted*\n\n"
                f"To use signals, you must:\n"
                f"1. Register at [PocketOption]({POCKET_OPTION_LINK}) using promo: `{PROMO_CODE}`\n"
                f"2. Deposit minimum $10\n"
                f"3. Send your *Pocket Option ID* here\n\n"
                "✅ After deposit, send your ID — I'll verify you manually."
            )
            keyboard = [
                [InlineKeyboardButton("🔗 Register Now", url=POCKET_OPTION_LINK)],
                [InlineKeyboardButton("Contact Support", callback_data="support")]
            ]
        else:
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
            f"To start receiving signals:\n"
            f"1. Register at [PocketOption]({POCKET_OPTION_LINK}) using promo code: `{PROMO_CODE}`\n"
            f"2. Deposit minimum $10\n"
            f"3. Send your *Pocket Option ID* here (found in app profile)\n\n"
            "✅ After deposit, send your ID — I'll verify you manually."
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
            "📌 *Connection Instructions:*\n"
            f"1. Register at [PocketOption]({POCKET_OPTION_LINK}), apply promo code `{PROMO_CODE}`.\n"
            "2. Fund your new account (min $10).\n"
            "3. Launch the app and start receiving signals.\n"
            "4. If a trade is losing, increase your next trade amount to compensate.\n\n"
            "⚠️ *Never risk more than 5% of your balance per trade.*"
        )
        keyboard = [[InlineKeyboardButton("Back «", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    async def support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        text = "🆘 *SUPPORT*\n\nFor help, contact me directly on Telegram.\nI respond within 24 hours."
        keyboard = [
            [InlineKeyboardButton("💬 Message Me", url=f"https://t.me/{SUPPORT_USERNAME}")],
            [InlineKeyboardButton("Back «", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    async def handle_user_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        text = update.message.text.strip()

        user = self.storage.get_user(chat_id)
        if not user.verified:
            user.pocket_option_id = text
            user.role = "pending"

            await update.message.reply_text(
                "✅ ID received! I'll verify you shortly.\nYou'll get access once approved."
            )

            for admin_id in ADMIN_CHAT_IDS:
                await self.app.bot.send_message(
                    admin_id,
                    f"🆕 New user pending verification:\n"
                    f"Chat ID: {chat_id}\n"
                    f"Username: @{user.username}\n"
                    f"Pocket Option ID: {text}"
                )

    async def admin_verify_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        target_chat_id = int(query.data.split("_")[-1])

        user = self.storage.get_user(target_chat_id)
        user.verified = True

        await query.edit_message_text(f"✅ User {target_chat_id} verified!")
        await self.app.bot.send_message(target_chat_id, "🎉 You've been verified! Use /start to access signals.")

    async def admin_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        text = "👥 Users:\n"
        keyboard = []
        for uid, user in self.storage.users.items():
            status = "✅" if user.verified else "⏳" if user.role == "pending" else "❌"
            btn_text = f"{status} {user.username or uid}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"admin_verify_{uid}")])
        keyboard.append([InlineKeyboardButton("« Back", callback_data="admin_panel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Select user to verify:", reply_markup=reply_markup)

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if chat_id not in ADMIN_CHAT_IDS:
            await update.message.reply_text("🚫 Access denied.")
            return

        keyboard = [[InlineKeyboardButton("👥 Manage Users", callback_data="admin_users")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🔐 Admin Panel", reply_markup=reply_markup)

# === MAIN ===
async def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in secrets")

    storage = Storage()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    bot_interface = TelegramBot(app, storage)

    # Handlers
    app.add_handler(CommandHandler("start", bot_interface.start))
    app.add_handler(CommandHandler("admin", bot_interface.admin_panel))
    app.add_handler(CallbackQueryHandler(bot_interface.main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(bot_interface.get_signal, pattern="^get_signal$"))
    app.add_handler(CallbackQueryHandler(bot_interface.instruction, pattern="^instruction$"))
    app.add_handler(CallbackQueryHandler(bot_interface.support, pattern="^support$"))
    app.add_handler(CallbackQueryHandler(bot_interface.admin_users, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(bot_interface.admin_verify_user, pattern=r"^admin_verify_\d+$"))
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
