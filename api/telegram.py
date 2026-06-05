"""
Vercel Serverless Function: Telegram Webhook
Handles incoming Telegram messages and calls the orchestrator
"""

import sys
import os
import json
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram_handler import handle_telegram_message
from logger import logger
from schemas import APIResponse, APIErrorResponse, APIMetadata

async def handler(request) -> Dict[str, Any]:
    """
    Vercel serverless function for Telegram webhook
    
    Expected payload:
    {
        "message": {
            "message_id": 123,
            "chat": {"id": 456},
            "text": "...",
            "photo": [...],
            ...
        },
        ...
    }
    """
    try:
        if request.method == "GET":
            # Webhook verification
            return {
                "statusCode": 200,
                "body": json.dumps({"status": "ok"})
            }
        
        if request.method == "POST":
            body = await request.json() if hasattr(request, 'json') else json.loads(request.body)
            
            logger.info(f"📱 Telegram webhook received: {body}")
            
            # Handle the message
            result = await handle_telegram_message(body)
            
            return {
                "statusCode": 200,
                "body": json.dumps(result or {"status": "processed"})
            }
        
        return {
            "statusCode": 405,
            "body": json.dumps({"error": "Method not allowed"})
        }
    
    except Exception as e:
        logger.error(f"❌ Telegram webhook error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "status": "error"
            })
        }
