"""
Telegram Bot Utilities
Helper functions for Telegram API integration
"""

import os
import aiohttp
import io
from typing import Optional, Tuple
from logger import logger


class TelegramAPI:
    """Telegram Bot API wrapper"""
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            logger.warn("TELEGRAM_BOT_TOKEN not configured")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    async def get_file(self, file_id: str) -> Optional[dict]:
        """Get file info from Telegram"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/getFile"
                async with session.post(url, json={"file_id": file_id}) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        return data.get("result")
                    else:
                        logger.error(f"Telegram getFile error: {data.get('description')}")
                        return None
        except Exception as e:
            logger.error(f"Failed to get Telegram file info: {str(e)}")
            return None
    
    async def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file from Telegram"""
        try:
            # Get file path
            file_info = await self.get_file(file_id)
            if not file_info:
                return None
            
            file_path = file_info.get("file_path")
            if not file_path:
                logger.error("No file_path in Telegram response")
                return None
            
            # Download file
            download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as resp:
                    if resp.status == 200:
                        file_data = await resp.read()
                        logger.debug(f"Downloaded file from Telegram: {len(file_data)} bytes")
                        return file_data
                    else:
                        logger.error(f"Failed to download file: HTTP {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Failed to download from Telegram: {str(e)}")
            return None
    
    async def send_message(self, chat_id: int, text: str) -> bool:
        """Send message via Telegram"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                }
                async with session.post(url, json=payload) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        logger.info(f"Message sent to Telegram chat {chat_id}")
                        return True
                    else:
                        logger.error(f"Telegram sendMessage error: {data.get('description')}")
                        return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            return False
    
    async def send_message_with_reply_markup(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict,
    ) -> bool:
        """Send message with reply markup (buttons)"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "reply_markup": reply_markup,
                }
                async with session.post(url, json=payload) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        return True
                    else:
                        logger.error(f"Failed to send message with markup: {data.get('description')}")
                        return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message with markup: {str(e)}")
            return False
    
    async def set_webhook(self, webhook_url: str) -> bool:
        """Set webhook for Telegram bot"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/setWebhook"
                payload = {"url": webhook_url}
                async with session.post(url, json=payload) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        logger.info(f"Telegram webhook set to {webhook_url}")
                        return True
                    else:
                        logger.error(f"Failed to set webhook: {data.get('description')}")
                        return False
        except Exception as e:
            logger.error(f"Failed to set Telegram webhook: {str(e)}")
            return False
    
    async def get_me(self) -> Optional[dict]:
        """Get bot info"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/getMe"
                async with session.get(url) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        return data.get("result")
                    else:
                        logger.error(f"Failed to get bot info: {data.get('description')}")
                        return None
        except Exception as e:
            logger.error(f"Failed to get Telegram bot info: {str(e)}")
            return None


# Global instance
_telegram_api: Optional[TelegramAPI] = None


def get_telegram_api() -> TelegramAPI:
    """Get or create Telegram API instance"""
    global _telegram_api
    if _telegram_api is None:
        _telegram_api = TelegramAPI()
    return _telegram_api


async def download_telegram_image(file_id: str) -> Optional[bytes]:
    """Download image from Telegram"""
    api = get_telegram_api()
    return await api.download_file(file_id)


async def download_telegram_file(file_id: str) -> Optional[bytes]:
    """Download file (PDF, etc) from Telegram"""
    api = get_telegram_api()
    return await api.download_file(file_id)


async def send_telegram_message(chat_id: int, text: str) -> bool:
    """Send message to Telegram chat"""
    api = get_telegram_api()
    return await api.send_message(chat_id, text)
