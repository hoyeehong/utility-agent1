"""
PDF Extraction Agent - Extract meter readings from SP bill PDFs
Uses pdfplumber for PDF parsing and custom parsing for SP bill format
"""

import os
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any
import pdfplumber
from logger import logger
from encryption import redact_pii, get_redacted_fields
from schemas import (
    PDFExtractionRequest,
    PDFExtractionResponse,
    PDFExtractionError,
    MeterReadingPair,
    MeterReading,
)


def parse_sp_bill_text(text: str) -> Dict[str, Any]:
    """
    Parse SP (Singapore Power) bill format text
    Extracts electricity and water readings
    """
    data = {
        "electricity": {
            "current_reading": None,
            "previous_reading": None,
            "usage_kwh": None,
        },
        "water": {
            "current_reading": None,
            "previous_reading": None,
            "usage_m3": None,
        },
        "billing_period": {
            "start_date": None,
            "end_date": None,
        },
        "total_bill_sgd": None,
    }
    
    lines = text.split('\n')
    
    # Extract billing period
    for line in lines:
        if 'Billing period' in line or 'Period' in line:
            # Try to extract dates
            dates = re.findall(r'\d{1,2}\s+\w+\s+\d{4}', line)
            if len(dates) >= 2:
                data["billing_period"]["start_date"] = dates[0]
                data["billing_period"]["end_date"] = dates[1]
    
    # Extract electricity readings
    for i, line in enumerate(lines):
        if 'Electricity' in line or 'kWh' in line.upper():
            # Look for readings in this section
            section = '\n'.join(lines[i:min(i+10, len(lines))])
            
            # Current reading
            current_match = re.search(r'(?:Current|Present)\s+(?:reading|meter).*?[\s:](\d+[\.,]\d+|\d+)', section, re.IGNORECASE)
            if current_match:
                data["electricity"]["current_reading"] = float(current_match.group(1).replace(',', '.'))
            
            # Previous reading
            prev_match = re.search(r'(?:Previous|Prior)\s+(?:reading|meter).*?[\s:](\d+[\.,]\d+|\d+)', section, re.IGNORECASE)
            if prev_match:
                data["electricity"]["previous_reading"] = float(prev_match.group(1).replace(',', '.'))
            
            # Usage
            usage_match = re.search(r'(?:Usage|Consumption).*?[\s:](\d+[\.,]\d+|\d+)\s*(?:kWh|kwh)', section, re.IGNORECASE)
            if usage_match:
                data["electricity"]["usage_kwh"] = float(usage_match.group(1).replace(',', '.'))
    
    # Extract water readings
    for i, line in enumerate(lines):
        if 'Water' in line or 'm³' in line or 'm3' in line:
            # Look for readings in this section
            section = '\n'.join(lines[i:min(i+10, len(lines))])
            
            # Current reading
            current_match = re.search(r'(?:Current|Present)\s+(?:reading|meter).*?[\s:](\d+[\.,]\d+|\d+)', section, re.IGNORECASE)
            if current_match:
                data["water"]["current_reading"] = float(current_match.group(1).replace(',', '.'))
            
            # Previous reading
            prev_match = re.search(r'(?:Previous|Prior)\s+(?:reading|meter).*?[\s:](\d+[\.,]\d+|\d+)', section, re.IGNORECASE)
            if prev_match:
                data["water"]["previous_reading"] = float(prev_match.group(1).replace(',', '.'))
            
            # Usage
            usage_match = re.search(r'(?:Usage|Consumption).*?[\s:](\d+[\.,]\d+|\d+)\s*(?:m³|m3)', section, re.IGNORECASE)
            if usage_match:
                data["water"]["usage_m3"] = float(usage_match.group(1).replace(',', '.'))
    
    # Extract total bill
    for line in lines:
        if 'Total' in line and ('$' in line or 'SGD' in line):
            amount_match = re.search(r'\$?\s*(\d+[\.,]\d{2})', line)
            if amount_match:
                data["total_bill_sgd"] = float(amount_match.group(1).replace(',', '.'))
    
    return data


def extract_readings_from_pdf_data(pdf_data: Dict[str, Any]) -> MeterReadingPair:
    """Convert parsed PDF data to MeterReadingPair"""
    readings = MeterReadingPair()
    
    # Electricity reading (prefer usage)
    if pdf_data["electricity"]["usage_kwh"]:
        readings.electricity = MeterReading(
            meter_type="electricity",
            reading_value=pdf_data["electricity"]["usage_kwh"],
            unit="kWh",
            date_captured=pdf_data["billing_period"]["end_date"] or "",
            confidence_score=0.95,
            source="pdf",
            metadata=pdf_data["electricity"],
        )
    elif pdf_data["electricity"]["current_reading"]:
        readings.electricity = MeterReading(
            meter_type="electricity",
            reading_value=pdf_data["electricity"]["current_reading"],
            unit="kWh",
            date_captured=pdf_data["billing_period"]["end_date"] or "",
            confidence_score=0.90,
            source="pdf",
            metadata=pdf_data["electricity"],
        )
    
    # Water reading (prefer usage)
    if pdf_data["water"]["usage_m3"]:
        readings.water = MeterReading(
            meter_type="water",
            reading_value=pdf_data["water"]["usage_m3"],
            unit="m³",
            date_captured=pdf_data["billing_period"]["end_date"] or "",
            confidence_score=0.95,
            source="pdf",
            metadata=pdf_data["water"],
        )
    elif pdf_data["water"]["current_reading"]:
        readings.water = MeterReading(
            meter_type="water",
            reading_value=pdf_data["water"]["current_reading"],
            unit="m³",
            date_captured=pdf_data["billing_period"]["end_date"] or "",
            confidence_score=0.90,
            source="pdf",
            metadata=pdf_data["water"],
        )
    
    return readings


async def pdf_extraction_agent(request: PDFExtractionRequest) -> PDFExtractionResponse:
    """
    Main PDF extraction agent
    Extracts meter readings from SP bill PDF
    """
    try:
        logger.debug("PDF Extraction Agent starting", {
            "pdf_path": request.pdf_path,
            "encrypt_pii": request.encrypt_pii,
        })
        
        # Check file exists
        if not os.path.exists(request.pdf_path):
            return PDFExtractionResponse(
                success=False,
                error=PDFExtractionError(
                    code="PDF_NOT_FOUND",
                    message=f"PDF file not found: {request.pdf_path}",
                )
            )
        
        # Check file is readable
        if not os.access(request.pdf_path, os.R_OK):
            return PDFExtractionResponse(
                success=False,
                error=PDFExtractionError(
                    code="PDF_NOT_READABLE",
                    message=f"PDF file not readable: {request.pdf_path}",
                )
            )
        
        # Extract text from PDF
        extracted_text = ""
        page_count = 0
        
        try:
            with pdfplumber.open(request.pdf_path) as pdf:
                page_count = len(pdf.pages)
                
                # Extract from first page (usually has billing info)
                for i, page in enumerate(pdf.pages[:3]):  # Check first 3 pages
                    page_text = page.extract_text() or ""
                    extracted_text += page_text + "\n"
                    
                    # Also try to extract tables
                    tables = page.extract_tables()
                    for table in tables or []:
                        for row in table:
                            extracted_text += " | ".join([str(cell) for cell in row]) + "\n"
        
        except Exception as e:
            logger.error(f"Failed to read PDF: {str(e)}")
            return PDFExtractionResponse(
                success=False,
                error=PDFExtractionError(
                    code="PDF_READ_ERROR",
                    message=f"Failed to read PDF: {str(e)}",
                )
            )
        
        if not extracted_text or extracted_text.strip() == "":
            return PDFExtractionResponse(
                success=False,
                error=PDFExtractionError(
                    code="PDF_NO_TEXT",
                    message="Could not extract text from PDF",
                )
            )
        
        logger.debug("PDF text extracted", {
            "pages": page_count,
            "text_length": len(extracted_text),
        })
        
        # Redact PII before parsing
        if request.encrypt_pii:
            redacted_text = redact_pii(extracted_text)
            redacted_fields = get_redacted_fields()
        else:
            redacted_text = extracted_text
            redacted_fields = []
        
        # Parse SP bill format
        pdf_data = parse_sp_bill_text(redacted_text)
        
        # Extract readings
        readings = extract_readings_from_pdf_data(pdf_data)
        
        # Check if we got any readings
        if not readings.electricity and not readings.water:
            logger.warn("No meter readings found in PDF", {
                "pdf_path": request.pdf_path,
                "extracted_data": pdf_data,
            })
            return PDFExtractionResponse(
                success=False,
                error=PDFExtractionError(
                    code="NO_READINGS_FOUND",
                    message="Could not extract electricity and water readings from PDF",
                )
            )
        
        logger.info("PDF extraction successful", {
            "electricity_reading": readings.electricity.reading_value if readings.electricity else None,
            "water_reading": readings.water.reading_value if readings.water else None,
            "redacted_fields": len(redacted_fields),
        })
        
        return PDFExtractionResponse(
            success=True,
            readings=readings,
            redacted_fields=redacted_fields,
        )
    
    except Exception as e:
        logger.error(f"PDF extraction failed: {str(e)}")
        return PDFExtractionResponse(
            success=False,
            error=PDFExtractionError(
                code="PDF_EXTRACTION_ERROR",
                message=f"PDF extraction error: {str(e)}",
            )
        )
