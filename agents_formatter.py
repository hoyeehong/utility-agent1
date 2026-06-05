"""
Formatter Agent - Format responses for Telegram and audit logs
"""

from datetime import datetime
from typing import Dict, Any
from schemas import CalculatorResponse, BillRecord, WorkflowState


def format_bill_response(
    tenant_name: str,
    bill: CalculatorResponse,
) -> str:
    """
    Format calculated bill for messaging (Telegram/WhatsApp)
    Returns human-readable text message
    """
    message = f"""
🧾 *Utility Bill Calculation*

*Tenant:* {tenant_name}
*Period:* {bill.billing_period}

*Electricity:* ${bill.electricity_charge:.2f}
*Water:* ${bill.water_charge:.2f}

*💰 Total Bill: ${bill.total_bill:.2f}* ({bill.currency})

---
"""
    
    if bill.breakdown:
        message += "\n📊 *Breakdown:*\n"
        
        if bill.breakdown.electricity:
            elec = bill.breakdown.electricity
            if "usage" in elec and "unit_rate" in elec:
                message += f"  • Electricity: {elec['usage']:.2f} kWh × ${elec['unit_rate']:.2f} = ${elec['charge']:.2f}\n"
        
        if bill.breakdown.water:
            water = bill.breakdown.water
            if "usage" in water and "unit_rate" in water:
                message += f"  • Water: {water['usage']:.2f} m³ × ${water['unit_rate']:.2f} = ${water['charge']:.2f}\n"
        
        if bill.breakdown.taxes:
            message += f"  • Taxes: ${bill.breakdown.taxes:.2f}\n"
        
        if bill.breakdown.discounts:
            message += f"  • Discounts: -${bill.breakdown.discounts:.2f}\n"
    
    message += "\n✅ Calculation completed successfully"
    
    return message


# Keep old name for backward compatibility
format_bill_for_whatsapp = format_bill_response


def format_error_message(error_code: str, error_message: str) -> str:
    """
    Format error message for WhatsApp
    """
    error_messages = {
        "NO_INPUT": "❌ No images or PDF provided. Please send meter photos.",
        "OCR_ERROR": "❌ Could not read the meter image. Please try again with a clearer photo.",
        "PDF_ERROR": "⚠️ Error reading PDF file.",
        "VALIDATION_ERROR": "❌ Meter reading validation failed. Please verify the readings.",
        "CALCULATION_ERROR": "❌ Error calculating the bill.",
        "NO_READINGS_EXTRACTED": "❌ Could not extract meter readings from images or PDF.",
    }
    
    formatted_message = error_messages.get(error_code, error_message)
    
    return f"{formatted_message}\n\n_Error: {error_code}_"


def format_bill_for_audit_log(
    workflow_state: WorkflowState,
    bill: CalculatorResponse,
) -> Dict[str, Any]:
    """
    Format bill for audit log storage
    """
    return {
        "workflow_id": workflow_state.id,
        "tenant_id": workflow_state.tenant_id,
        "billing_period": bill.billing_period,
        "electricity_charge": bill.electricity_charge,
        "water_charge": bill.water_charge,
        "total_bill": bill.total_bill,
        "currency": bill.currency,
        "breakdown": bill.breakdown.model_dump() if bill.breakdown else None,
        "sources": workflow_state.input_sources,
        "created_at": datetime.utcnow().isoformat(),
    }
