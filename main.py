"""
FastAPI Main Application
Replaces Next.js API routes with FastAPI endpoints
"""

import os
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from typing import Optional, List

from logger import logger
from schemas import APIResponse, APIErrorResponse, APIMetadata
from orchestrator import orchestrate_workflow
from telegram_handler import handle_telegram_message, handle_telegram_text_message
from tariff_rate_manager import TariffRateManager

# Initialize Supabase client (optional)
try:
    from supabase import create_client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if supabase_url and supabase_key:
        supabase_client = create_client(supabase_url, supabase_key)
        tariff_manager = TariffRateManager(supabase_client, cache_ttl_hours=24)
        logger.info("✅ Tariff rate manager initialized with Supabase")
    else:
        tariff_manager = TariffRateManager(None)
        logger.warning("⚠️  Supabase not configured, using fallback rates")
except Exception as e:
    logger.error(f"Failed to initialize Supabase: {e}")
    tariff_manager = TariffRateManager(None)

# Initialize FastAPI app
app = FastAPI(
    title="Utility Bill Calculator",
    description="AI-powered utility bill calculation from Telegram",
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store tariff manager in app state for access in routes
app.state.tariff_manager = tariff_manager


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
    }


# ============================================================
# CALCULATE BILL ENDPOINT
# ============================================================

@app.post("/api/calculate-bill")
async def calculate_bill(
    tenant_id: str,
    billing_period: str,
    images: Optional[List[UploadFile]] = File(None),
    pdf: Optional[UploadFile] = File(None),
):
    """
    Calculate utility bill from images and/or PDF
    """
    try:
        logger.info("Calculate bill request received", {
            "tenant_id": tenant_id,
            "billing_period": billing_period,
            "image_count": len(images) if images else 0,
            "has_pdf": pdf is not None,
        })
        
        # Read image buffers
        image_buffers = None
        if images:
            image_buffers = []
            for image_file in images:
                content = await image_file.read()
                image_buffers.append(content)
                logger.debug(f"Read image: {image_file.filename} ({len(content)} bytes)")
        
        # Read PDF
        pdf_path = None
        if pdf:
            # Save PDF temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                content = await pdf.read()
                tmp.write(content)
                pdf_path = tmp.name
                logger.debug(f"Saved PDF to {pdf_path}")
        
        # Call orchestrator
        result = await orchestrate_workflow(
            tenant_id=tenant_id,
            billing_period=billing_period,
            image_buffers=image_buffers,
            pdf_path=pdf_path,
        )
        
        # Clean up temp PDF
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        return result.model_dump()
    
    except Exception as e:
        logger.error(f"Calculate bill error: {str(e)}")
        return APIResponse(
            success=False,
            error=APIErrorResponse(
                code="CALCULATION_ERROR",
                message=str(e),
            ),
            metadata=APIMetadata(
                request_id="unknown",
                timestamp=datetime.utcnow().isoformat(),
                duration_ms=0,
            ),
        ).model_dump()


# ============================================================
# TELEGRAM WEBHOOK
# ============================================================

@app.post("/api/webhook/telegram")
async def telegram_webhook_post(payload: dict):
    """
    Handle incoming Telegram bot updates
    Receives messages with photos and documents
    """
    try:
        logger.info("Telegram webhook received")
        
        # Check update type
        if "message" not in payload:
            logger.debug("Telegram update is not a message, ignoring")
            return {"status": "ok"}
        
        message = payload.get("message")
        
        # Handle text messages (commands)
        if "text" in message:
            await handle_telegram_text_message(message)
            return {"status": "ok"}
        
        # Handle photos and documents
        if "photo" in message or "document" in message:
            success = await handle_telegram_message(message)
            return {"status": "ok", "processed": success}
        
        # Unknown message type
        logger.debug(f"Telegram message type not supported: {message.keys()}")
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Telegram webhook error: {str(e)}")
        return {"status": "ok"}  # Always return 200 to prevent Telegram retries


# ============================================================
# DEBUG ENDPOINT (remove in production)
# ============================================================

@app.post("/api/debug/test-bill")
async def test_bill():
    """Debug endpoint to test bill calculation"""
    logger.info("Test bill calculation")
    
    result = await orchestrate_workflow(
        tenant_id="tenant_001",
        billing_period="2024-06",
        image_buffers=[],
        pdf_path=None,
    )
    
    return result.model_dump()


@app.get("/api/debug/telegram-info")
async def telegram_debug_info():
    """Debug endpoint to get Telegram bot info"""
    from telegram_utils import get_telegram_api
    
    api = get_telegram_api()
    bot_info = await api.get_me()
    
    if bot_info:
        return {
            "status": "ok",
            "bot": bot_info,
            "webhook_url": f"https://your-domain.com/api/webhook/telegram",
        }
    else:
        return {
            "status": "error",
            "message": "Failed to get bot info. Check TELEGRAM_BOT_TOKEN.",
        }


@app.post("/api/debug/telegram-webhook-set")
async def telegram_set_webhook(webhook_url: str):
    """Debug endpoint to set Telegram webhook"""
    from telegram_utils import get_telegram_api
    
    api = get_telegram_api()
    success = await api.set_webhook(webhook_url)
    
    return {
        "status": "ok" if success else "error",
        "webhook_url": webhook_url,
        "success": success,
    }


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Utility Bill Calculator",
        "version": "2.0.0",
        "messaging": "Telegram",
        "endpoints": {
            "health": "/health",
            "telegram_webhook": "/api/webhook/telegram",
            "calculate_bill": "/api/calculate-bill",
        },
    }


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
            },
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
            },
        },
    )


# ============================================================
# STARTUP/SHUTDOWN
# ============================================================

@app.on_event("startup")
async def startup():
    """Run on startup"""
    logger.info("Application starting up")


@app.on_event("shutdown")
async def shutdown():
    """Run on shutdown"""
    logger.info("Application shutting down")


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("ENV") == "development",
    )
