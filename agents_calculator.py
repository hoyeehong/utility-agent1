"""
Calculation Agent - Calculate utility bills from meter readings
Handles multi-month usage calculation with Singapore tariff rates
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from supabase import create_client
from logger import logger

# Singapore tariff rates (update as needed)
# Source: SP Group & PUB Singapore
# Note: These are approximate rates as of 2024
# Update ACTUAL_TARIFF_RATES in tariff_rates table regularly

DEFAULT_TARIFF_RATES = {
    "electricity_rate": 0.2674,  # SGD/kWh (typical residential rate)
    "water_rate": 1.17,          # SGD/m³ (typical residential rate)
    "tax_percentage": 9.0,       # GST 9%
}


class CalculationAgent:
    """
    Handles bill calculation from meter readings
    - Fetches previous month readings
    - Calculates usage difference
    - Applies tariff rates and taxes
    - Handles anomalies (meter resets, etc)
    """
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize with Supabase credentials"""
        self.supabase = create_client(supabase_url, supabase_key)
        logger.info("CalculationAgent initialized")
    
    def get_previous_month_reading(self, tenant_id: str, billing_month: str) -> Optional[Dict[str, float]]:
        """
        Get previous month's meter readings from database
        
        Args:
            tenant_id: e.g., "tenant_001"
            billing_month: e.g., "2024-06" (current month)
        
        Returns:
            {electricity_reading, water_reading} or None if not found
        """
        try:
            # Convert "2024-06" to previous month date
            current = datetime.strptime(billing_month, "%Y-%m")
            previous = current - timedelta(days=30)
            previous_month_str = previous.strftime("%Y-%m-01")
            
            result = self.supabase.table("meter_readings").select(
                "electricity_reading, water_reading"
            ).eq(
                "tenant_id", tenant_id
            ).eq(
                "billing_month", previous_month_str
            ).execute()
            
            if result.data and len(result.data) > 0:
                reading = result.data[0]
                logger.info(f"Previous month reading found for {tenant_id}", {
                    "month": previous_month_str,
                    "electricity": reading["electricity_reading"],
                    "water": reading["water_reading"],
                })
                return {
                    "electricity": float(reading["electricity_reading"]),
                    "water": float(reading["water_reading"]),
                }
            else:
                logger.warn(f"Previous month reading not found for {tenant_id}", {
                    "month": previous_month_str,
                })
                return None
        
        except Exception as e:
            logger.error(f"Error fetching previous reading: {str(e)}")
            return None
    
    def calculate_usage(
        self,
        current_reading: Dict[str, float],
        previous_reading: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calculate consumption: current - previous
        Detect anomalies (meter resets, negative usage)
        
        Args:
            current_reading: {electricity, water} - current month readings
            previous_reading: {electricity, water} - previous month readings
        
        Returns:
            {
                electricity_usage,
                water_usage,
                has_anomaly,
                anomaly_details
            }
        """
        elec_usage = current_reading["electricity"] - previous_reading["electricity"]
        water_usage = current_reading["water"] - previous_reading["water"]
        
        has_anomaly = False
        anomaly_details = []
        
        # Detect electricity meter reset or negative usage
        if elec_usage < 0:
            has_anomaly = True
            anomaly_details.append({
                "type": "negative_electricity",
                "message": f"Electricity reading decreased from {previous_reading['electricity']} to {current_reading['electricity']} kWh",
                "previous": previous_reading["electricity"],
                "current": current_reading["electricity"],
                "difference": elec_usage,
            })
            logger.warn("Electricity meter anomaly detected", {
                "previous": previous_reading["electricity"],
                "current": current_reading["electricity"],
                "difference": elec_usage,
            })
        
        # Detect water meter reset or negative usage
        if water_usage < 0:
            has_anomaly = True
            anomaly_details.append({
                "type": "negative_water",
                "message": f"Water reading decreased from {previous_reading['water']} to {current_reading['water']} m³",
                "previous": previous_reading["water"],
                "current": current_reading["water"],
                "difference": water_usage,
            })
            logger.warn("Water meter anomaly detected", {
                "previous": previous_reading["water"],
                "current": current_reading["water"],
                "difference": water_usage,
            })
        
        # Detect unusually high usage (optional - flag if > 50 units)
        if elec_usage > 50:
            anomaly_details.append({
                "type": "high_electricity_usage",
                "message": f"Unusually high electricity usage: {elec_usage} kWh",
                "usage": elec_usage,
            })
            logger.warn(f"High electricity usage detected: {elec_usage} kWh")
        
        if water_usage > 10:
            anomaly_details.append({
                "type": "high_water_usage",
                "message": f"Unusually high water usage: {water_usage} m³",
                "usage": water_usage,
            })
            logger.warn(f"High water usage detected: {water_usage} m³")
        
        return {
            "electricity_usage": max(0, elec_usage),
            "water_usage": max(0, water_usage),
            "has_anomaly": has_anomaly,
            "anomaly_details": anomaly_details,
        }
    
    def get_tariff_rates(self) -> Dict[str, float]:
        """
        Get current tariff rates from Supabase
        Falls back to defaults if not available
        
        Returns:
            {
                electricity_rate,    # SGD/kWh
                water_rate,          # SGD/m³
                tax_percentage       # %
            }
        """
        try:
            result = self.supabase.table("tariff_rates").select(
                "electricity_rate, water_rate, tax_percentage"
            ).order(
                "effective_date", desc=True
            ).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                rates = result.data[0]
                logger.info("Tariff rates fetched from database", {
                    "electricity_rate": rates["electricity_rate"],
                    "water_rate": rates["water_rate"],
                    "tax_percentage": rates["tax_percentage"],
                })
                return {
                    "electricity_rate": float(rates["electricity_rate"]),
                    "water_rate": float(rates["water_rate"]),
                    "tax_percentage": float(rates["tax_percentage"]),
                }
        except Exception as e:
            logger.error(f"Error fetching tariff rates: {str(e)}")
        
        # Use default fallback rates
        logger.warn("Using default fallback tariff rates", DEFAULT_TARIFF_RATES)
        return DEFAULT_TARIFF_RATES
    
    def calculate_bill(
        self,
        usage: Dict[str, float],
        rates: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Apply tariff rates and calculate charges with GST
        
        Args:
            usage: {electricity_usage, water_usage}
            rates: {electricity_rate, water_rate, tax_percentage}
        
        Returns:
            {
                electricity_usage,
                electricity_rate,
                electricity_charge,
                water_usage,
                water_rate,
                water_charge,
                subtotal,
                gst_amount,
                total_charge,
            }
        """
        # Calculate charges
        elec_charge = usage["electricity_usage"] * rates["electricity_rate"]
        water_charge = usage["water_usage"] * rates["water_rate"]
        subtotal = elec_charge + water_charge
        
        # Apply GST
        tax_rate = rates["tax_percentage"] / 100
        gst_amount = subtotal * tax_rate
        total = subtotal + gst_amount
        
        result = {
            "electricity_usage": usage["electricity_usage"],
            "electricity_rate": rates["electricity_rate"],
            "electricity_charge": round(elec_charge, 2),
            "water_usage": usage["water_usage"],
            "water_rate": rates["water_rate"],
            "water_charge": round(water_charge, 2),
            "subtotal": round(subtotal, 2),
            "gst_percentage": rates["tax_percentage"],
            "gst_amount": round(gst_amount, 2),
            "total_charge": round(total, 2),
        }
        
        logger.info("Bill calculated", {
            "electricity_charge": result["electricity_charge"],
            "water_charge": result["water_charge"],
            "gst": result["gst_amount"],
            "total": result["total_charge"],
        })
        
        return result
    
    def save_meter_reading(
        self,
        tenant_id: str,
        billing_month: str,
        reading: Dict[str, Any]
    ) -> bool:
        """
        Save current month's meter reading to database
        
        Args:
            tenant_id: Tenant identifier
            billing_month: "2024-06"
            reading: {electricity, water, source, confidence}
        
        Returns:
            True if saved successfully
        """
        try:
            self.supabase.table("meter_readings").insert({
                "tenant_id": tenant_id,
                "billing_month": f"{billing_month}-01",
                "electricity_reading": float(reading.get("electricity", 0)),
                "water_reading": float(reading.get("water", 0)),
                "reading_source": reading.get("source", "combined"),
                "confidence_score": float(reading.get("confidence", 0.95)),
            }).execute()
            
            logger.info(f"Meter reading saved for {tenant_id}", {
                "month": billing_month,
                "electricity": reading.get("electricity"),
                "water": reading.get("water"),
            })
            return True
        
        except Exception as e:
            logger.error(f"Error saving meter reading: {str(e)}")
            return False
    
    def save_bill(
        self,
        tenant_id: str,
        billing_month: str,
        workflow_id: str,
        bill_data: Dict[str, Any]
    ) -> bool:
        """
        Save calculated bill to database
        
        Args:
            tenant_id: Tenant identifier
            billing_month: "2024-06"
            workflow_id: For tracking
            bill_data: Complete bill calculation result
        
        Returns:
            True if saved successfully
        """
        try:
            self.supabase.table("bills").insert({
                "tenant_id": tenant_id,
                "billing_month": f"{billing_month}-01",
                "electricity_usage": float(bill_data.get("electricity_usage", 0)),
                "water_usage": float(bill_data.get("water_usage", 0)),
                "electricity_rate": float(bill_data.get("electricity_rate", 0)),
                "water_rate": float(bill_data.get("water_rate", 0)),
                "electricity_charge": float(bill_data.get("electricity_charge", 0)),
                "water_charge": float(bill_data.get("water_charge", 0)),
                "gst_amount": float(bill_data.get("gst_amount", 0)),
                "total_charge": float(bill_data.get("total_charge", 0)),
                "workflow_id": workflow_id,
            }).execute()
            
            logger.info(f"Bill saved for {tenant_id}", {
                "month": billing_month,
                "total": bill_data.get("total_charge"),
            })
            return True
        
        except Exception as e:
            logger.error(f"Error saving bill: {str(e)}")
            return False
