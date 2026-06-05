"""
Validation Agent - Validates and reconciles meter readings
Compares image-based vs PDF-based readings
"""

import re
from typing import Dict
from logger import logger
from schemas import (
    ValidationRequest,
    ValidationResponse,
    ValidationIssue,
    Reconciliation,
    MeterReadingPair,
)


def calculate_discrepancy_percentage(value1: float, value2: float) -> float:
    """Calculate percentage discrepancy between two values"""
    if value1 == 0 and value2 == 0:
        return 0.0
    
    max_val = max(abs(value1), abs(value2))
    if max_val == 0:
        return 0.0
    
    return abs(value1 - value2) / max_val * 100


def reconcile_readings(
    image_readings: MeterReadingPair,
    pdf_readings: MeterReadingPair,
) -> Reconciliation:
    """
    Reconcile image and PDF readings
    Determine which reading is more reliable
    """
    issues = []
    max_discrepancy = 0.0
    
    # Reconcile electricity
    if image_readings.electricity and pdf_readings.electricity:
        elec_discrepancy = calculate_discrepancy_percentage(
            image_readings.electricity.reading_value,
            pdf_readings.electricity.reading_value
        )
        max_discrepancy = max(max_discrepancy, elec_discrepancy)
        
        if elec_discrepancy < 2:
            # Very close match, use average
            recommended_action = "use_average"
        elif elec_discrepancy <= 5:
            # Close match, prefer image (more recent)
            recommended_action = "use_image"
        elif elec_discrepancy <= 10:
            # Moderate discrepancy, flag for review but prefer image
            recommended_action = "use_image"
        else:
            # Large discrepancy, require user input
            recommended_action = "request_user_input"
    elif image_readings.electricity:
        recommended_action = "use_image"
    elif pdf_readings.electricity:
        recommended_action = "use_pdf"
    else:
        recommended_action = "request_user_input"
    
    return Reconciliation(
        discrepancy_percentage=max_discrepancy,
        recommended_action=recommended_action,
    )


async def validation_agent(request: ValidationRequest) -> ValidationResponse:
    """
    Validate meter readings and reconcile differences
    """
    try:
        logger.debug("Validation Agent starting", {
            "has_electricity": bool(request.readings.electricity),
            "has_water": bool(request.readings.water),
            "has_pdf_readings": bool(request.pdf_readings),
        })
        
        issues = []
        is_valid = True
        
        # ============================================================
        # VALIDATE METER READINGS EXIST
        # ============================================================
        
        if not request.readings.electricity and not request.readings.water:
            issues.append(ValidationIssue(
                field="readings",
                issue="No meter readings provided",
                severity="error",
                suggestion="Provide at least one meter reading (electricity or water)",
            ))
            is_valid = False
        
        # ============================================================
        # VALIDATE ELECTRICITY READINGS
        # ============================================================
        
        if request.readings.electricity:
            elec = request.readings.electricity
            
            # Check reading value is reasonable
            if elec.reading_value < 0:
                issues.append(ValidationIssue(
                    field="electricity.reading_value",
                    issue="Electricity reading cannot be negative",
                    severity="error",
                ))
                is_valid = False
            elif elec.reading_value > 99999:
                issues.append(ValidationIssue(
                    field="electricity.reading_value",
                    issue="Electricity reading seems unusually high (>99,999 kWh)",
                    severity="warning",
                    suggestion="Verify the reading is correct",
                ))
            
            # Check confidence score
            if elec.confidence_score < 0.6:
                issues.append(ValidationIssue(
                    field="electricity.confidence_score",
                    issue=f"Low confidence score ({elec.confidence_score:.0%}) in electricity reading",
                    severity="warning",
                    suggestion="Consider re-capturing the electricity meter image",
                ))
        
        # ============================================================
        # VALIDATE WATER READINGS
        # ============================================================
        
        if request.readings.water:
            water = request.readings.water
            
            # Check reading value is reasonable
            if water.reading_value < 0:
                issues.append(ValidationIssue(
                    field="water.reading_value",
                    issue="Water reading cannot be negative",
                    severity="error",
                ))
                is_valid = False
            elif water.reading_value > 99999:
                issues.append(ValidationIssue(
                    field="water.reading_value",
                    issue="Water reading seems unusually high (>99,999 m³)",
                    severity="warning",
                    suggestion="Verify the reading is correct",
                ))
            
            # Check confidence score
            if water.confidence_score < 0.6:
                issues.append(ValidationIssue(
                    field="water.confidence_score",
                    issue=f"Low confidence score ({water.confidence_score:.0%}) in water reading",
                    severity="warning",
                    suggestion="Consider re-capturing the water meter image",
                ))
        
        # ============================================================
        # RECONCILE IMAGE vs PDF
        # ============================================================
        
        reconciliation = None
        
        if request.pdf_readings and (request.readings.electricity or request.readings.water):
            reconciliation = reconcile_readings(request.readings, request.pdf_readings)
            
            # Check for significant discrepancies
            if reconciliation.discrepancy_percentage > 10:
                issues.append(ValidationIssue(
                    field="reconciliation",
                    issue=f"Large discrepancy ({reconciliation.discrepancy_percentage:.1f}%) between image and PDF readings",
                    severity="warning",
                    suggestion="Review both images/PDF and verify which reading is correct",
                ))
            elif reconciliation.discrepancy_percentage > 20:
                issues.append(ValidationIssue(
                    field="reconciliation",
                    issue=f"Very large discrepancy ({reconciliation.discrepancy_percentage:.1f}%) detected",
                    severity="error",
                    suggestion="Manual review required - readings may be from different meters or dates",
                ))
                is_valid = False
        
        # ============================================================
        # CHECK FOR CRITICAL ERRORS
        # ============================================================
        
        critical_errors = [issue for issue in issues if issue.severity == "error"]
        if critical_errors:
            is_valid = False
        
        logger.info("Validation complete", {
            "valid": is_valid,
            "issue_count": len(issues),
            "error_count": len(critical_errors),
        })
        
        return ValidationResponse(
            valid=is_valid,
            issues=issues,
            reconciliation=reconciliation,
        )
    
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        return ValidationResponse(
            valid=False,
            issues=[
                ValidationIssue(
                    field="validation",
                    issue=f"Validation error: {str(e)}",
                    severity="error",
                )
            ],
        )
