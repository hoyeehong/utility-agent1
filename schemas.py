"""
Core Pydantic Models for Utility Bill Calculator
Replaces TypeScript interfaces with Python type hints
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# ============================================================
# METER & READING TYPES
# ============================================================

MeterType = Literal['electricity', 'water']
ReadingSource = Literal['telegram_image', 'pdf', 'manual', 'api']
WorkflowStatus = Literal['pending', 'processing', 'validating', 'calculating', 'completed', 'failed', 'escalated']
Severity = Literal['info', 'warning', 'error', 'critical']


class MeterReading(BaseModel):
    """Single meter reading from OCR or PDF"""
    meter_type: MeterType
    reading_value: float
    unit: Literal['kWh', 'm³']
    date_captured: str
    confidence_score: float
    source: ReadingSource
    raw_ocr_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MeterReadingPair(BaseModel):
    """Pair of electricity and water readings"""
    electricity: Optional[MeterReading] = None
    water: Optional[MeterReading] = None


# ============================================================
# BILL & CALCULATION TYPES
# ============================================================

class CalculationBreakdown(BaseModel):
    """Detailed breakdown of charges"""
    electricity: Optional[Dict[str, float]] = None
    water: Optional[Dict[str, float]] = None
    taxes: Optional[float] = None
    discounts: Optional[float] = None


class CalculatorRequest(BaseModel):
    """Request to calculator API"""
    electricity_kwh: Optional[float] = None
    water_m3: Optional[float] = None
    tenant_id: str
    billing_period: str
    source: List[ReadingSource]
    metadata: Optional[Dict[str, Any]] = None


class CalculatorResponse(BaseModel):
    """Response from calculator API"""
    electricity_charge: float
    water_charge: float
    total_bill: float
    breakdown: Optional[CalculationBreakdown] = None
    currency: str = "SGD"
    billing_period: str


class BillRecord(BaseModel):
    """Bill stored in database"""
    id: str
    tenant_id: str
    billing_period: str
    electricity_kwh: Optional[float] = None
    water_m3: Optional[float] = None
    calculated_bill: float
    sources: List[ReadingSource]
    created_at: str
    updated_at: str


# ============================================================
# WORKFLOW STATE TYPES
# ============================================================

class WorkflowError(BaseModel):
    """Single error in workflow"""
    code: str
    message: str
    stage: str
    severity: Severity
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class WorkflowState(BaseModel):
    """Complete workflow state"""
    id: str
    tenant_id: str
    status: WorkflowStatus
    current_stage: str
    input_sources: List[ReadingSource]
    readings: MeterReadingPair
    calculation: Optional[CalculatorResponse] = None
    errors: List[WorkflowError] = Field(default_factory=list)
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]] = None


# ============================================================
# AGENT REQUEST/RESPONSE TYPES
# ============================================================

class ImageOCRRequest(BaseModel):
    """Request to image OCR agent"""
    image_data: bytes
    image_format: Literal['jpg', 'png', 'jpeg', 'webp']
    expected_meter_type: Optional[MeterType] = None


class ImageOCRError(BaseModel):
    """Error response from OCR"""
    code: str
    message: str
    suggestions: Optional[List[str]] = None


class ImageOCRResponse(BaseModel):
    """Response from image OCR agent"""
    success: bool
    reading: Optional[MeterReading] = None
    error: Optional[ImageOCRError] = None


class PDFExtractionRequest(BaseModel):
    """Request to PDF extraction agent"""
    pdf_path: str
    encrypt_pii: bool = True


class PDFExtractionError(BaseModel):
    """Error response from PDF extraction"""
    code: str
    message: str


class PDFExtractionResponse(BaseModel):
    """Response from PDF extraction agent"""
    success: bool
    readings: Optional[MeterReadingPair] = None
    redacted_fields: Optional[List[str]] = None
    error: Optional[PDFExtractionError] = None


# ============================================================
# VALIDATION TYPES
# ============================================================

class ValidationIssue(BaseModel):
    """Single validation issue"""
    field: str
    issue: str
    severity: Literal['warning', 'error']
    suggestion: Optional[str] = None


class Reconciliation(BaseModel):
    """Reconciliation details"""
    discrepancy_percentage: float
    recommended_action: Literal['use_image', 'use_pdf', 'use_average', 'request_user_input']


class ValidationRequest(BaseModel):
    """Request to validation agent"""
    readings: MeterReadingPair
    pdf_readings: Optional[MeterReadingPair] = None


class ValidationResponse(BaseModel):
    """Response from validation agent"""
    valid: bool
    issues: List[ValidationIssue] = Field(default_factory=list)
    reconciliation: Optional[Reconciliation] = None


# ============================================================
# AUDIT LOG TYPES
# ============================================================

class AuditLogEntry(BaseModel):
    """Audit log entry"""
    id: str
    workflow_id: str
    tenant_id: str
    action: str
    stage: str
    status: Literal['success', 'failure', 'escalation']
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    pii_redacted_fields: Optional[List[str]] = None
    error: Optional[str] = None
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


# ============================================================
# TENANT & CONFIGURATION TYPES
# ============================================================

class Tenant(BaseModel):
    """Tenant information"""
    id: str
    name: str
    email: Optional[str] = None
    billing_period: Literal['monthly', 'quarterly']
    created_at: str
    updated_at: str
    is_active: bool


class TenantQuota(BaseModel):
    """Tenant usage quota"""
    tenant_id: str
    bills_per_day: int
    bills_this_month: int
    last_bill_date: Optional[str] = None


# ============================================================
# API RESPONSE TYPES
# ============================================================

class APIErrorResponse(BaseModel):
    """Error in API response"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class APIMetadata(BaseModel):
    """Metadata in API response"""
    request_id: str
    timestamp: str
    duration_ms: int


class APIResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[APIErrorResponse] = None
    metadata: Optional[APIMetadata] = None


# ============================================================
# DISCREPANCY TYPES
# ============================================================

class RecommendedReading(BaseModel):
    """Recommended reading for discrepancy"""
    value: float
    source: ReadingSource
    reason: str


class DiscrepancyReport(BaseModel):
    """Discrepancy analysis report"""
    electricity_discrepancy_pct: float
    water_discrepancy_pct: float
    max_discrepancy_pct: float
    requires_escalation: bool
    recommended_reading: Dict[str, RecommendedReading]
