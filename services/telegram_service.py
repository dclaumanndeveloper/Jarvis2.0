import os
import logging
import telebot
from PyQt6.QtCore import QThread, pyqtSignal
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class TelegramService(QThread):
    """
    Bridge for Telegram communication.
    Receives commands from the bot and sends proactive alerts to the user.
    """
    command_received = pyqtSignal(str) # Relays messages to AIService

    def __init__(self):
        super().__init__()
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.bot = None
        self.running = False

        if self.token and self.token != "insira_seu_token_aqui":
            try:
                self.bot = telebot.TeleBot(self.token)
                self._setup_handlers()
                logger.info("TelegramService: Bot initialized.")
            except Exception as e:
                logger.error(f"TelegramService: Failed to init bot: {e}")
        else:
            logger.warning("TelegramService: Bot Token not set or invalid.")

    def _setup_handlers(self):
        @self.bot.message_handler(func=lambda message: True)
        def handle_all_messages(message):
            # Only respond to the authorized user
            if str(message.chat.id) == self.chat_id:
                logger.info(f"Telegram: Command received: {message.text}")
                self.command_received.emit(message.text)
            else:
                logger.warning(f"Telegram: Unauthorized message from {message.chat.id}")
                self.bot.reply_to(message, "⚠️ Acesso negado. Apenas o proprietário pode interagir com este JARVIS.")

    def run(self):
        if self.bot:
            self.running = True
            logger.info("TelegramService: Starting polling...")
            try:
                self.bot.infinity_polling()
            except Exception as e:
                logger.error(f"TelegramService: Polling error: {e}")
                self.running = False

    def send_message(self, text):
        """Send a message to the authorized user (proactivity)"""
        if self.bot and self.chat_id and self.chat_id != "insira_seu_id_aqui":
            try:
                self.bot.send_message(self.chat_id, text)
                logger.info(f"Telegram: Alert sent to user.")
            except Exception as e:
                logger.error(f"TelegramService: Failed to send message: {e}")

    def stop(self):
        self.running = False
        if self.bot:
            self.bot.stop_polling()
        self.wait()
