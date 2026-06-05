"""
Vercel Serverless Function: Calculate Bill API
Calculates utility bill from meter readings
"""

import sys
import os
import json
from typing import Dict, Any
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utility_calculator import UtilityCalculator
from tariff_rate_manager import TariffRateManager
from logger import logger
from schemas import APIResponse, APIErrorResponse, APIMetadata

# Initialize calculator and tariff manager
calculator = UtilityCalculator()
tariff_manager = None

try:
    from supabase import create_client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if supabase_url and supabase_key:
        supabase_client = create_client(supabase_url, supabase_key)
        tariff_manager = TariffRateManager(supabase_client, cache_ttl_hours=24)
        logger.info("✅ Tariff manager initialized")
    else:
        tariff_manager = TariffRateManager(None)
        logger.warning("⚠️  Using fallback tariff rates")
except Exception as e:
    logger.error(f"Failed to initialize tariff manager: {e}")
    tariff_manager = TariffRateManager(None)


async def handler(request) -> Dict[str, Any]:
    """
    Calculate utility bill from meter readings
    
    POST /api/calculate
    Body:
    {
        "electricity_current": 150,
        "electricity_previous": 100,
        "water_current": 8.3,
        "water_previous": 5.0
    }
    """
    try:
        if request.method != "POST":
            return {
                "statusCode": 405,
                "body": json.dumps({"error": "Method not allowed. Use POST."})
            }
        
        body = await request.json() if hasattr(request, 'json') else json.loads(request.body)
        
        # Extract meter readings
        electricity_current = float(body.get("electricity_current"))
        electricity_previous = float(body.get("electricity_previous"))
        water_current = float(body.get("water_current"))
        water_previous = float(body.get("water_previous"))
        
        # Validate inputs
        if electricity_current <= 0 or water_current <= 0:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Current readings must be positive",
                    "status": "error"
                })
            }
        
        # Calculate bill
        bill = calculator.calculate_bill(
            electricity_usage=electricity_current - electricity_previous,
            water_usage=water_current - water_previous,
            previous_data={
                'electricity': electricity_previous,
                'water': water_previous
            }
        )
        
        # Convert Decimal to float for JSON serialization
        bill_serializable = {
            k: float(v) if isinstance(v, Decimal) else v
            for k, v in bill.items()
        }
        
        logger.info(f"✅ Bill calculated: ${bill_serializable['total_bill_with_gst']:.2f}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "data": {
                    "bill": bill_serializable,
                    "electricity_current": electricity_current,
                    "electricity_previous": electricity_previous,
                    "water_current": water_current,
                    "water_previous": water_previous
                }
            }),
            "headers": {
                "Content-Type": "application/json"
            }
        }
    
    except ValueError as e:
        logger.warning(f"⚠️  Validation error: {e}")
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": f"Invalid input: {str(e)}",
                "status": "error"
            })
        }
    
    except Exception as e:
        logger.error(f"❌ Calculate error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "status": "error"
            })
        }
