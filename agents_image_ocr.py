"""
Image OCR Agent - Extract meter readings from images
Uses Google Cloud Vision API for accurate meter reading detection
Fallback to Tesseract for fully offline operation
"""

import io
import base64
import re
import json
from typing import Optional
from google.cloud import vision
from PIL import Image
import pytesseract
from logger import logger
from schemas import ImageOCRRequest, ImageOCRResponse, ImageOCRError, MeterReading


def extract_meter_readings_from_text(text: str, meter_type: Optional[str] = None) -> Optional[float]:
    """
    Parse meter reading from OCR text
    Looks for numeric patterns that represent meter readings
    """
    if not text:
        return None
    
    # Remove common OCR artifacts
    text = text.replace(',', '').replace('O', '0').replace('o', '0')
    
    # Look for patterns like "12345.67" or "12345"
    # Usually meter readings are 5-8 digit numbers with optional decimals
    patterns = [
        r'\b(\d{5,8}[\.\,]\d{1,2})\b',  # 5+ digits with decimal
        r'\b(\d{5,8})\b',                 # 5+ digits without decimal
    ]
    
    matches = []
    for pattern in patterns:
        found = re.findall(pattern, text)
        matches.extend(found)
    
    if matches:
        # Return the largest number (likely the main reading)
        try:
            values = [float(m.replace(',', '.')) for m in matches]
            return max(values)
        except ValueError:
            pass
    
    return None


def detect_meter_type_from_text(text: str) -> str:
    """Detect meter type from OCR text"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['electricity', 'kwh', 'kw·h', 'electric', 'power']):
        return 'electricity'
    elif any(word in text_lower for word in ['water', 'm³', 'm3', 'liters', 'cubic']):
        return 'water'
    
    return 'electricity'  # Default to electricity


class GoogleVisionOCRAgent:
    """Image OCR using Google Cloud Vision API"""
    
    def __init__(self):
        """Initialize Google Vision client"""
        try:
            self.client = vision.ImageAnnotatorClient()
            logger.info("Google Cloud Vision initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Vision: {str(e)}")
            self.client = None
    
    async def process(self, request: ImageOCRRequest) -> ImageOCRResponse:
        """Process image and extract meter reading"""
        try:
            if not self.client:
                logger.warn("Google Vision not available, falling back to Tesseract")
                return await tesseract_ocr_agent.process(request)
            
            logger.debug("Google Vision OCR starting", {
                "image_format": request.image_format,
            })
            
            # Create image object
            image = vision.Image(content=request.image_data)
            
            # Call Google Vision
            response = self.client.document_text_recognition(image=image)
            text_annotation = response.full_text_annotation
            
            if not text_annotation or not text_annotation.text:
                return ImageOCRResponse(
                    success=False,
                    error=ImageOCRError(
                        code="NO_TEXT_DETECTED",
                        message="No text detected in image",
                        suggestions=[
                            "Ensure image contains a clear meter display",
                            "Try a clearer or higher resolution image",
                            "Ensure meter display is visible and not obscured",
                        ]
                    )
                )
            
            text = text_annotation.text
            logger.debug("OCR text extracted", {"text_length": len(text)})
            
            # Extract meter reading from text
            reading_value = extract_meter_readings_from_text(text)
            meter_type = request.expected_meter_type or detect_meter_type_from_text(text)
            
            if reading_value is None:
                return ImageOCRResponse(
                    success=False,
                    error=ImageOCRError(
                        code="NO_READING_FOUND",
                        message="Could not extract numeric meter reading from image text",
                        suggestions=[
                            "Ensure the meter display is clearly visible",
                            "Try an image with better lighting",
                            "Ensure the entire meter display is in frame",
                        ]
                    )
                )
            
            # Calculate confidence based on text clarity
            # Google Vision provides confidence via vertices, but we estimate based on extraction success
            confidence = 0.95  # High confidence if we successfully extracted
            
            reading = MeterReading(
                meter_type=meter_type,
                reading_value=reading_value,
                unit="kWh" if meter_type == "electricity" else "m³",
                date_captured="",  # Could extract from image metadata
                confidence_score=confidence,
                source="telegram_image",
                raw_ocr_text=text,
                metadata={"full_text_annotation": len(text_annotation.text)}
            )
            
            logger.info("Image OCR successful", {
                "meter_type": meter_type,
                "reading_value": reading_value,
                "confidence": confidence,
            })
            
            return ImageOCRResponse(success=True, reading=reading)
        
        except Exception as e:
            logger.error(f"Google Vision OCR failed: {str(e)}")
            return ImageOCRResponse(
                success=False,
                error=ImageOCRError(
                    code="VISION_API_ERROR",
                    message=f"Google Vision API error: {str(e)}"
                )
            )


class TesseractOCRAgent:
    """Image OCR using local Tesseract (fully offline)"""
    
    async def process(self, request: ImageOCRRequest) -> ImageOCRResponse:
        """Process image and extract meter reading using Tesseract"""
        try:
            logger.debug("Tesseract OCR starting", {
                "image_format": request.image_format,
            })
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(request.image_data))
            
            # Preprocess image for better OCR
            # Convert to grayscale
            image = image.convert('L')
            
            # Run Tesseract
            text = pytesseract.image_to_string(
                image,
                config='--psm 6'  # PSM 6 = uniform block of text
            )
            
            logger.debug("OCR text extracted", {"text_length": len(text)})
            
            if not text or text.strip() == "":
                return ImageOCRResponse(
                    success=False,
                    error=ImageOCRError(
                        code="NO_TEXT_DETECTED",
                        message="Tesseract could not detect text in image",
                        suggestions=[
                            "Ensure image contains a clear meter display",
                            "Try a clearer or higher resolution image",
                            "Ensure meter display is not obscured",
                        ]
                    )
                )
            
            # Extract meter reading
            reading_value = extract_meter_readings_from_text(text)
            meter_type = request.expected_meter_type or detect_meter_type_from_text(text)
            
            if reading_value is None:
                return ImageOCRResponse(
                    success=False,
                    error=ImageOCRError(
                        code="NO_READING_FOUND",
                        message="Could not extract numeric meter reading from OCR text",
                    )
                )
            
            # Tesseract confidence is typically lower
            confidence = 0.85
            
            reading = MeterReading(
                meter_type=meter_type,
                reading_value=reading_value,
                unit="kWh" if meter_type == "electricity" else "m³",
                date_captured="",
                confidence_score=confidence,
                source="telegram_image",
                raw_ocr_text=text,
            )
            
            logger.info("Tesseract OCR successful", {
                "meter_type": meter_type,
                "reading_value": reading_value,
                "confidence": confidence,
            })
            
            return ImageOCRResponse(success=True, reading=reading)
        
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {str(e)}")
            return ImageOCRResponse(
                success=False,
                error=ImageOCRError(
                    code="TESSERACT_ERROR",
                    message=f"Tesseract OCR error: {str(e)}"
                )
            )


# Create agent instances
google_vision_agent = GoogleVisionOCRAgent()
tesseract_ocr_agent = TesseractOCRAgent()


async def image_ocr_agent(request: ImageOCRRequest) -> ImageOCRResponse:
    """
    Main image OCR agent
    Uses Google Vision first, falls back to Tesseract
    """
    # Try Google Vision first
    result = await google_vision_agent.process(request)
    
    # If Google Vision fails and we haven't tried Tesseract, try it
    if not result.success and google_vision_agent.client is not None:
        logger.info("Google Vision failed, trying Tesseract fallback")
        result = await tesseract_ocr_agent.process(request)
    
    return result
