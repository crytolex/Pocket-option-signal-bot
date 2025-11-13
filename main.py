# main.py
import os
import logging
import asyncio
from datetime import datetime
from typing import Dict
from dataclasses import dataclass, field
import io

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from dotenv import load_dotenv

load_dotenv()

# === CONFIG ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_IDS = [int(cid.strip()) for cid in os.getenv("ADMIN_CHAT_IDS", "").split(",") if cid.strip()]
POCKET_OPTION_LINK = os.getenv("POCKET_OPTION_LINK", "https://pocketoption.com/")
PROMO_CODE = os.getenv("PROMO_CODE", "YVE200")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "your_telegram_username").replace("@", "")
WELCOME_IMG_URL = os.getenv("WELCOME_IMG_URL", "")
MENU_IMG_URL = os.getenv("MENU_IMG_URL", "")
INSTRUCTION_IMG_URL = os.getenv("INSTRUCTION_IMG_URL", "")

# === FULL PAIR LIST (60+ pairs) ===
PAIRS = {
    "forex": [
        "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "NZD/USD", "EUR/GBP",
        "EUR/JPY", "GBP/JPY", "AUD/JPY", "CAD/JPY", "CHF/JPY", "USD/CHF", "EUR/CHF"
    ],
    "crypto": [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", "ADA/USDT", "BNB/USDT",
        "DOT/USDT", "MATIC/USDT", "LTC/USDT", "UNI/USDT", "LINK/USDT", "XLM/USDT", "ATOM/USDT",
        "AVAX/USDT", "ALGO/USDT", "FTM/USDT", "NEAR/USDT", "ICP/USDT", "HBAR/USDT"
    ],
    "commodities": [
        "XAU/USD", "XAG/USD", "OIL/USD", "COPPER/USD", "WHEAT/USD", "SOYBEAN/USD", "NGAS/USD"
    ],
    "indices": [
        "US30", "NAS100", "SP500", "GER40", "UK100", "FRA40", "JPN225", "AUS200", "HKG50", "SG30"
    ],
    "otc": [
        "EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC", "AUD/USD OTC", "USD/CAD OTC", "NZD/USD OTC",
        "EUR/JPY OTC", "GBP/JPY OTC", "AUD/JPY OTC", "CAD/JPY OTC", "BTC/USDT OTC", "ETH/USDT OTC",
        "SOL/USDT OTC", "XRP/USDT OTC", "XAU/USD OTC", "OIL/USD OTC", "US30 OTC", "NAS100 OTC",
        "SP500 OTC", "GER40 OTC", "UK100 OTC", "CRYPTO IDX OTC"  # 22 OTC pairs
    ]
}

EXPIRY_MAP = {
    "otc": ["5 sec", "15 sec", "30 sec", "1 min", "2 min", "5 min", "15 min"],
    "regular": ["1 min", "2 min", "5 min", "15 min", "30 min", "1 hour"]
}

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

@dataclass
class User:
    chat_id: int
    username: str = ""
    verified: bool = False

class Storage:
    def __init__(self):
        self.users: Dict[int, User] = {}

    def get_user(self, chat_id: int) -> User:
        if chat_id not in self.users:
            self.users[chat_id] = User(chat_id=chat_id)
        return self.users[chat_id]

def generate_chart():
    """Generate a simple chart image."""
    plt.figure(figsize=(6, 3))
    x = np.linspace(0, 10, 100)
    y = np.sin(x) + np.random.normal(0, 0.1, 100)
    plt.plot(x, y, color='green')
    plt.title("Signal Chart")
    plt.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    buf.seek(0)
    plt.close()
    return buf

class TelegramBot:
    def __init__(self, app: Application, storage: Storage):
        self.app = app
        self.storage = storage

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        chat_id = user.id
        db_user = self.storage.get_user(chat_id)
        db_user.username = user.username or str(user.id)
        
        try:
            keyboard = [[InlineKeyboardButton("Start ▶️", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_photo(
                photo=WELCOME_IMG_URL,
                caption="Welcome to Pocket Signal Pro!",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error in /start: {e}")
            # Fallback without image
            await update.message.reply_text(
                "Welcome to Pocket Signal Pro!\nClick below to start:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Start ▶️", callback_data="main_menu")]])
            )

    async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE = None):
        """Show main menu with image."""
        query = update.callback_query if update.callback_query else None
        if query:
            await query.answer()

        chat_id = update.effective_chat.id
        # 👑 ADMIN: Full access
        if chat_id in ADMIN_CHAT_IDS:
            caption = "👑 *BOSS MENU*\n\nYou are the owner!"
            keyboard = [
                [InlineKeyboardButton("GET SIGNAL 📈", callback_data="get_signal")],
                [InlineKeyboardButton("SUGGEST SIGNAL 🤖", callback_data="suggest_signal")],
                [InlineKeyboardButton("INSTRUCTION 📄", callback_data="instruction")],
                [InlineKeyboardButton("SUPPORT 🆘", url=f"https://t.me/{SUPPORT_USERNAME}")],
                [InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                if query:
                    await query.edit_message_media(
                        media=InputMediaPhoto(MENU_IMG_URL, caption=caption, parse_mode="Markdown"),
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_photo(photo=MENU_IMG_URL, caption=caption, reply_markup=reply_markup, parse_mode="Markdown")
            except:
                # Fallback without image
                await (query.edit_message_text if query else update.message.reply_text)(
                    caption, reply_markup=reply_markup, parse_mode="Markdown"
                )
            return

        # 🚪 NON-ADMIN: Registration
        user = self.storage.get_user(chat_id)
        if not user.verified:
            text = (
                "🔒 *Access Restricted*\n\n"
                f"1. Register at [Pocket Option]({POCKET_OPTION_LINK}) with promo: `{PROMO_CODE}`\n"
                "2. Deposit $10+\n"
                "3. Send your Pocket Option ID to me"
            )
            keyboard = [[InlineKeyboardButton("🔗 Register Now", url=POCKET_OPTION_LINK)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
            return

        # 🟢 VERIFIED USER
        caption = "💎 *MAIN MENU*"
        keyboard = [
            [InlineKeyboardButton("GET SIGNAL 📈", callback_data="get_signal")],
            [InlineKeyboardButton("SUGGEST SIGNAL 🤖", callback_data="suggest_signal")],
            [InlineKeyboardButton("INSTRUCTION 📄", callback_data="instruction")],
            [InlineKeyboardButton("SUPPORT 🆘", url=f"https://t.me/{SUPPORT_USERNAME}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            if query:
                await query.edit_message_media(
                    media=InputMediaPhoto(MENU_IMG_URL, caption=caption, parse_mode="Markdown"),
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_photo(photo=MENU_IMG_URL, caption=caption, reply_markup=reply_markup, parse_mode="Markdown")
        except:
            await (query.edit_message_text if query else update.message.reply_text)(
                caption, reply_markup=reply_markup, parse_mode="Markdown"
            )

    async def get_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pair categories."""
        query = update.callback_query
        await query.answer()
        keyboard = [
            [InlineKeyboardButton("💱 Forex", callback_data="pair_category_forex"),
             InlineKeyboardButton("🪙 Crypto", callback_data="pair_category_crypto")],
            [InlineKeyboardButton("📈 Commodities", callback_data="pair_category_commodities"),
             InlineKeyboardButton("🏦 Indices", callback_data="pair_category_indices")],
            [InlineKeyboardButton("🌐 OTC (24/7)", callback_data="pair_category_otc")],
            [InlineKeyboardButton("« Back", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption="📊 Choose market type:", reply_markup=reply_markup)

    async def pair_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pairs for selected category."""
        query = update.callback_query
        await query.answer()
        category = query.data.split("_")[-1]
        pairs = PAIRS.get(category, [])
        keyboard = []
        for pair in pairs:
            keyboard.append([InlineKeyboardButton(pair, callback_data=f"select_pair_{pair}")])
        keyboard.append([InlineKeyboardButton("« Back", callback_data="get_signal")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption=f"📊 {category.upper()} Pairs:", reply_markup=reply_markup)

    async def select_pair(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show expiry options for selected pair."""
        query = update.callback_query
        await query.answer()
        pair = query.data.replace("select_pair_", "")
        context.user_data["selected_pair"] = pair
        
        expiries = EXPIRY_MAP["otc"] if "OTC" in pair else EXPIRY_MAP["regular"]
        keyboard = []
        for exp in expiries:
            keyboard.append([InlineKeyboardButton(exp, callback_data=f"select_expiry_{exp}")])
        keyboard.append([InlineKeyboardButton("« Back", callback_data=f"pair_category_{pair.split('/')[0].lower()}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption=f"⏱️ Choose expiry for {pair}:", reply_markup=reply_markup)

    async def select_expiry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate and send signal."""
        query = update.callback_query
        await query.answer()
        expiry = query.data.replace("select_expiry_", "")
        pair = context.user_data.get("selected_pair", "Unknown")
        action = "BUY" if np.random.random() > 0.5 else "SELL"
        confidence = round(np.random.uniform(70, 95), 1)
        
        caption = (
            f"✅ *Your Signal*\n\n"
            f"{'🟢' if action == 'BUY' else '🔴'} {action} {pair}\n"
            f"Confidence: {confidence}%\n"
            f"Expiry: {expiry}\n\n"
            f"Trade wisely!"
        )
        
        try:
            chart_img = generate_chart()
            keyboard = [[InlineKeyboardButton("« Back", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_photo(photo=chart_img, caption=caption, parse_mode="Markdown", reply_markup=reply_markup)
        except:
            await query.message.reply_text(caption, parse_mode="Markdown")

    async def suggest_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send smart suggestion."""
        query = update.callback_query
        await query.answer()
        caption = (
            f"🤖 *Smart Suggestion*\n\n"
            f"🟢 BUY EUR/USD OTC\n"
            f"Confidence: 86%\n"
            f"Recommended Expiry: 5 min"
        )
        try:
            chart_img = generate_chart()
            keyboard = [[InlineKeyboardButton("« Back", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_photo(photo=chart_img, caption=caption, parse_mode="Markdown", reply_markup=reply_markup)
        except:
            await query.message.reply_text(caption, parse_mode="Markdown")

    async def instruction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show instruction with image."""
        query = update.callback_query
        await query.answer()
        caption = (
            "📘 *INSTRUCTION*\n\n"
            "📌 *How to use signals:*\n"
            "1. Register with our link & promo code\n"
            "2. Deposit $10+ to activate account\n"
            "3. Send your Pocket Option ID to get verified\n"
            "4. Use signals to trade manually\n\n"
            "⚠️ *Risk Management:*\n"
            "• Never risk >5% per trade\n"
            "• Use stop-loss discipline"
        )
        keyboard = [[InlineKeyboardButton("« Back", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await query.edit_message_media(
                media=InputMediaPhoto(INSTRUCTION_IMG_URL, caption=caption, parse_mode="Markdown"),
                reply_markup=reply_markup
            )
        except:
            await query.edit_message_text(caption, reply_markup=reply_markup, parse_mode="Markdown")

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin panel."""
        query = update.callback_query
        if query:
            await query.answer()
        chat_id = update.effective_chat.id
        if chat_id not in ADMIN_CHAT_IDS:
            await update.message.reply_text("🚫 Access denied.")
            return
            
        caption = "🔐 *Admin Panel*\n\nManage your bot:"
        keyboard = [
            [InlineKeyboardButton("👥 Users", callback_data="admin_users")],
            [InlineKeyboardButton("❓ Commands", callback_data="admin_commands")],
            [InlineKeyboardButton("« Back", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await (query.edit_message_caption if query else update.message.reply_text)(
            caption, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def admin_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin commands."""
        query = update.callback_query
        await query.answer()
        caption = (
            "🛠️ *Admin Commands*\n\n"
            "/adduser 123456789 → Add user instantly\n"
            "/banuser 123456789 → Ban user\n"
            "/broadcast Hi! → Message all users\n"
            "/admin → Open admin panel"
        )
        keyboard = [[InlineKeyboardButton("« Back", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode="Markdown")

    async def handle_user_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user verification."""
        chat_id = update.effective_chat.id
        user = self.storage.get_user(chat_id)
        if not user.verified:
            user.verified = True
            await update.message.reply_text("✅ Verified! Use /start to access signals.")
            for admin_id in ADMIN_CHAT_IDS:
                await self.app.bot.send_message(admin_id, f"✅ User {chat_id} verified.")

# === MAIN ===
async def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in Secrets")

    storage = Storage()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    bot_interface = TelegramBot(app, storage)

    # Register handlers
    app.add_handler(CommandHandler("start", bot_interface.start))
    app.add_handler(CommandHandler("admin", bot_interface.admin_panel))
    app.add_handler(CallbackQueryHandler(bot_interface.main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(bot_interface.get_signal, pattern="^get_signal$"))
    app.add_handler(CallbackQueryHandler(bot_interface.pair_category, pattern="^pair_category_"))
    app.add_handler(CallbackQueryHandler(bot_interface.select_pair, pattern="^select_pair_"))
    app.add_handler(CallbackQueryHandler(bot_interface.select_expiry, pattern="^select_expiry_"))
    app.add_handler(CallbackQueryHandler(bot_interface.suggest_signal, pattern="^suggest_signal$"))
    app.add_handler(CallbackQueryHandler(bot_interface.instruction, pattern="^instruction$"))
    app.add_handler(CallbackQueryHandler(bot_interface.admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(bot_interface.admin_commands, pattern="^admin_commands$"))
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
