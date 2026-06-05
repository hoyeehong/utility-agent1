"""
Main Orchestrator - Coordinates all agents
This is the heart of the workflow - replaces lib/orchestrator.ts
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import httpx
from logger import logger, create_audit_log
from schemas import (
    WorkflowState,
    WorkflowStatus,
    WorkflowError,
    MeterReadingPair,
    CalculatorResponse,
    APIResponse,
    APIErrorResponse,
    APIMetadata,
)
from agents_image_ocr import image_ocr_agent
from agents_pdf_extraction import pdf_extraction_agent
from agents_validation import validation_agent
from agents_formatter import format_bill_response, format_bill_for_audit_log, format_error_message
from agents_calculator import CalculationAgent
import os


def initialize_workflow(tenant_id: str, billing_period: str) -> WorkflowState:
    """Initialize workflow state"""
    workflow_id = f"workflow_{int(datetime.utcnow().timestamp() * 1000)}_{uuid.uuid4().hex[:9]}"
    
    return WorkflowState(
        id=workflow_id,
        tenant_id=tenant_id,
        status="pending",
        current_stage="initialized",
        input_sources=[],
        readings=MeterReadingPair(),
        errors=[],
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        metadata={"billing_period": billing_period},
    )


def add_error(
    workflow: WorkflowState,
    code: str,
    message: str,
    stage: str,
    severity: str = "error",
) -> None:
    """Add error to workflow"""
    workflow.errors.append(WorkflowError(
        code=code,
        message=message,
        stage=stage,
        severity=severity,
        timestamp=datetime.utcnow().isoformat(),
    ))
    logger.warn(f"Workflow error added: {code}", {"message": message, "stage": stage})


def update_status(
    workflow: WorkflowState,
    status: WorkflowStatus,
    stage: str,
) -> None:
    """Update workflow status"""
    workflow.status = status
    workflow.current_stage = stage
    workflow.updated_at = datetime.utcnow().isoformat()
    logger.debug("Workflow status updated", {
        "status": status,
        "stage": stage,
        "workflow_id": workflow.id,
    })


async def orchestrate_workflow(
    tenant_id: str,
    billing_period: str,
    image_buffers: Optional[List[bytes]] = None,
    pdf_path: Optional[str] = None,
) -> APIResponse:
    """
    Main orchestrator function
    Coordinates all agents through 7-stage workflow:
    1. Input validation
    2. Image extraction (OCR)
    3. PDF extraction
    4. Data validation & reconciliation
    5. Fetch previous month reading & calculate usage
    6. Get tariff rates & calculate bill
    7. Format & complete
    """
    # Initialize workflow
    workflow = initialize_workflow(tenant_id, billing_period)
    request_id = workflow.id
    start_time = datetime.utcnow()
    
    logger.set_context({
        "request_id": request_id,
        "workflow_id": workflow.id,
        "tenant_id": tenant_id,
    })
    
    try:
        # ============================================================
        # STAGE 1: VALIDATE INPUTS
        # ============================================================
        update_status(workflow, "processing", "input_validation")
        logger.info("Stage 1: Input validation starting")
        
        if not image_buffers and not pdf_path:
            add_error(
                workflow,
                "NO_INPUT",
                "No images or PDF provided",
                "input_validation",
                "critical",
            )
            update_status(workflow, "failed", "input_validation")
            raise ValueError("No input data provided")
        
        # ============================================================
        # STAGE 2: EXTRACT DATA FROM IMAGES
        # ============================================================
        update_status(workflow, "processing", "image_extraction")
        logger.info("Stage 2: Image extraction starting", {
            "image_count": len(image_buffers) if image_buffers else 0,
        })
        
        if image_buffers:
            for i, image_buffer in enumerate(image_buffers):
                logger.debug(f"Processing image {i + 1}/{len(image_buffers)}")
                
                from schemas import ImageOCRRequest
                ocr_request = ImageOCRRequest(
                    image_data=image_buffer,
                    image_format="jpg",
                )
                
                ocr_result = await image_ocr_agent(ocr_request)
                
                if not ocr_result.success or not ocr_result.reading:
                    add_error(
                        workflow,
                        ocr_result.error.code if ocr_result.error else "OCR_ERROR",
                        ocr_result.error.message if ocr_result.error else "Unknown OCR error",
                        "image_extraction",
                        "error",
                    )
                    continue
                
                # Store reading
                if ocr_result.reading.meter_type == "electricity":
                    workflow.readings.electricity = ocr_result.reading
                    workflow.input_sources.append("telegram_image")
                elif ocr_result.reading.meter_type == "water":
                    workflow.readings.water = ocr_result.reading
                    workflow.input_sources.append("telegram_image")
                
                logger.info("Image extraction successful", {
                    "meter_type": ocr_result.reading.meter_type,
                    "reading_value": ocr_result.reading.reading_value,
                })
                
                await create_audit_log(
                    workflow_id=workflow.id,
                    tenant_id=tenant_id,
                    action="image_extraction",
                    stage="image_extraction",
                    status="success",
                    output_data=ocr_result.reading.model_dump(),
                )
        
        # ============================================================
        # STAGE 3: EXTRACT DATA FROM PDF
        # ============================================================
        update_status(workflow, "processing", "pdf_extraction")
        pdf_readings = MeterReadingPair()
        
        if pdf_path:
            logger.info("Stage 3: PDF extraction starting")
            
            from schemas import PDFExtractionRequest
            pdf_request = PDFExtractionRequest(
                pdf_path=pdf_path,
                encrypt_pii=True,
            )
            
            pdf_result = await pdf_extraction_agent(pdf_request)
            
            if not pdf_result.success or not pdf_result.readings:
                add_error(
                    workflow,
                    pdf_result.error.code if pdf_result.error else "PDF_ERROR",
                    pdf_result.error.message if pdf_result.error else "Unknown PDF error",
                    "pdf_extraction",
                    "warning",  # PDF is optional
                )
            else:
                pdf_readings = pdf_result.readings
                workflow.input_sources.append("pdf")
                logger.info("PDF extraction successful")
                
                await create_audit_log(
                    workflow_id=workflow.id,
                    tenant_id=tenant_id,
                    action="pdf_extraction",
                    stage="pdf_extraction",
                    status="success",
                    pii_redacted_fields=pdf_result.redacted_fields,
                    output_data=pdf_result.readings.model_dump(),
                )
        
        # ============================================================
        # STAGE 4: VALIDATE & RECONCILE DATA
        # ============================================================
        update_status(workflow, "validating", "data_validation")
        logger.info("Stage 4: Data validation starting")
        
        if not workflow.readings.electricity and not workflow.readings.water:
            add_error(
                workflow,
                "NO_READINGS_EXTRACTED",
                "Could not extract any meter readings",
                "data_validation",
                "critical",
            )
            update_status(workflow, "failed", "data_validation")
            raise ValueError("No meter readings extracted")
        
        from schemas import ValidationRequest
        validation_request = ValidationRequest(
            readings=workflow.readings,
            pdf_readings=pdf_readings,
        )
        
        validation_result = await validation_agent(validation_request)
        
        if not validation_result.valid:
            critical_issues = [i for i in validation_result.issues if i.severity == "error"]
            for issue in critical_issues:
                add_error(workflow, "VALIDATION_ERROR", issue.issue, "data_validation", "error")
            update_status(workflow, "failed", "data_validation")
            raise ValueError(f"Validation failed: {validation_result.issues[0].issue if validation_result.issues else 'Unknown'}")
        
        for issue in validation_result.issues:
            if issue.severity == "warning":
                add_error(workflow, "VALIDATION_WARNING", issue.issue, "data_validation", "warning")
        
        logger.info("Data validation successful")
        
        await create_audit_log(
            workflow_id=workflow.id,
            tenant_id=tenant_id,
            action="data_validation",
            stage="data_validation",
            status="success",
        )
        
        # ============================================================
        # STAGE 5: FETCH PREVIOUS MONTH READING & CALCULATE USAGE
        # ============================================================
        update_status(workflow, "calculating", "fetch_previous_reading")
        logger.info("Stage 5: Fetching previous month reading")
        
        # Initialize calculation agent
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not configured")
        
        calc_agent = CalculationAgent(supabase_url, supabase_key)
        
        # Extract current readings
        current_reading = {
            "electricity": workflow.readings.electricity.reading_value if workflow.readings.electricity else 0,
            "water": workflow.readings.water.reading_value if workflow.readings.water else 0,
            "source": ",".join(workflow.input_sources) if workflow.input_sources else "combined",
            "confidence": min(
                workflow.readings.electricity.confidence if workflow.readings.electricity else 0,
                workflow.readings.water.confidence if workflow.readings.water else 0,
            )
        }
        
        # Save current reading
        calc_agent.save_meter_reading(tenant_id, billing_period, current_reading)
        
        # Get previous month reading
        previous_reading = calc_agent.get_previous_month_reading(tenant_id, billing_period)
        
        if not previous_reading:
            add_error(
                workflow,
                "NO_PREVIOUS_READING",
                "No previous month reading found. Please provide your previous month meter readings.",
                "fetch_previous_reading",
                "warning",
            )
            logger.warn(f"Previous reading not found for {tenant_id} - {billing_period}")
            # For now, use 0 as fallback (user should provide manually)
            previous_reading = {"electricity": 0, "water": 0}
        
        # Calculate usage
        usage_result = calc_agent.calculate_usage(current_reading, previous_reading)
        
        if usage_result["has_anomaly"]:
            for anomaly in usage_result["anomaly_details"]:
                add_error(
                    workflow,
                    f"ANOMALY_{anomaly['type'].upper()}",
                    anomaly["message"],
                    "fetch_previous_reading",
                    "warning",
                )
            logger.warn(f"Meter anomalies detected", usage_result["anomaly_details"])
        
        logger.info("Usage calculation completed", {
            "electricity_usage": usage_result["electricity_usage"],
            "water_usage": usage_result["water_usage"],
            "has_anomaly": usage_result["has_anomaly"],
        })
        
        # ============================================================
        # STAGE 6: GET TARIFF RATES & CALCULATE BILL
        # ============================================================
        update_status(workflow, "calculating", "bill_calculation")
        logger.info("Stage 6: Calculating bill with tariff rates")
        
        # Get current tariff rates
        rates = calc_agent.get_tariff_rates()
        
        # Calculate bill charges
        bill_data = calc_agent.calculate_bill(usage_result, rates)
        
        # Save bill to database
        calc_agent.save_bill(tenant_id, billing_period, workflow.id, bill_data)
        
        # Create CalculatorResponse for compatibility
        from schemas import CalculatorResponse
        calculation = CalculatorResponse(
            electricity_usage=bill_data["electricity_usage"],
            water_usage=bill_data["water_usage"],
            electricity_rate=bill_data["electricity_rate"],
            water_rate=bill_data["water_rate"],
            electricity_charge=bill_data["electricity_charge"],
            water_charge=bill_data["water_charge"],
            gst_amount=bill_data["gst_amount"],
            total_bill=bill_data["total_charge"],
        )
        workflow.calculation = calculation
        
        logger.info("Bill calculation successful", {
            "total_bill": workflow.calculation.total_bill,
        })
        
        await create_audit_log(
            workflow_id=workflow.id,
            tenant_id=tenant_id,
            action="bill_calculation",
            stage="bill_calculation",
            status="success",
            output_data=workflow.calculation.model_dump(),
        )
        
        # ============================================================
        # STAGE 7: FORMAT & COMPLETE
        # ============================================================
        update_status(workflow, "completed", "formatting")
        logger.info("Stage 7: Formatting response")
        
        # Format message for messaging service
        bill_message = format_bill_response("Tenant", workflow.calculation)
        
        # Create final audit log
        await create_audit_log(
            workflow_id=workflow.id,
            tenant_id=tenant_id,
            action="workflow_completed",
            stage="completion",
            status="success",
        )
        
        # Calculate duration
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        logger.info("Workflow completed successfully", {
            "duration_ms": duration_ms,
            "total_bill": workflow.calculation.total_bill,
        })
        
        # Return success response
        return APIResponse(
            success=True,
            data={
                "bill": workflow.calculation.model_dump(),
                "message": bill_message,
                "workflow_id": workflow.id,
            },
            metadata=APIMetadata(
                request_id=request_id,
                timestamp=datetime.utcnow().isoformat(),
                duration_ms=duration_ms,
            ),
        )
    
    except Exception as e:
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        logger.error(f"Workflow failed: {str(e)}", {
            "workflow_id": workflow.id,
            "stage": workflow.current_stage,
            "error_count": len(workflow.errors),
        })
        
        # Create failure audit log
        await create_audit_log(
            workflow_id=workflow.id,
            tenant_id=tenant_id,
            action="workflow_failed",
            stage=workflow.current_stage,
            status="failure",
            error=str(e),
        )
        
        # Return error response
        return APIResponse(
            success=False,
            error=APIErrorResponse(
                code=workflow.errors[-1].code if workflow.errors else "UNKNOWN_ERROR",
                message=str(e),
            ),
            metadata=APIMetadata(
                request_id=request_id,
                timestamp=datetime.utcnow().isoformat(),
                duration_ms=duration_ms,
            ),
        )
