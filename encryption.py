"""
Encryption & PII Redaction Utilities
Replaces lib/encryption.ts with Python implementation
"""

import os
import re
from typing import Set
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2
import base64
import json


class EncryptionManager:
    """Handles AES-256 encryption and PII redaction"""
    
    def __init__(self):
        """Initialize encryption with environment key"""
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY environment variable not set")
        
        if len(encryption_key) != 64:
            raise ValueError("ENCRYPTION_KEY must be exactly 64 hex characters (32 bytes)")
        
        self.key = bytes.fromhex(encryption_key)
        self.redacted_fields: Set[str] = set()
    
    def encrypt_field(self, plaintext: str) -> str:
        """
        Encrypt a field using AES-256-GCM
        Returns: base64(nonce + ciphertext + tag)
        """
        # Generate random nonce (12 bytes for GCM)
        nonce = get_random_bytes(12)
        
        # Create cipher
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        
        # Encrypt
        ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
        
        # Combine: nonce + ciphertext + tag
        encrypted_data = nonce + ciphertext + tag
        
        # Return as base64
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt_field(self, encrypted_b64: str) -> str:
        """
        Decrypt a field encrypted with encrypt_field
        """
        try:
            # Decode from base64
            encrypted_data = base64.b64decode(encrypted_b64)
            
            # Extract nonce (first 12 bytes), tag (last 16 bytes), ciphertext (middle)
            nonce = encrypted_data[:12]
            tag = encrypted_data[-16:]
            ciphertext = encrypted_data[12:-16]
            
            # Create cipher and decrypt
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            
            return plaintext.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def redact_pii(self, text: str) -> str:
        """
        Redact personally identifiable information from text
        Redacts:
        - Names (capitalized words at start of lines)
        - Addresses (patterns like "123 Main Street")
        - Phone numbers
        - Email addresses
        - NRIC (Singapore ID)
        """
        redacted = text
        
        # Phone numbers (Singapore format: +65 XXXX-XXXX or 9999 9999)
        phone_pattern = r'(\+?65\s?)?[\d\s\-\(\)]{8,}(?=\s|$)'
        if re.search(phone_pattern, redacted):
            redacted = re.sub(phone_pattern, '[REDACTED PHONE]', redacted)
            self.redacted_fields.add('phone_number')
        
        # Email addresses
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        if re.search(email_pattern, redacted):
            redacted = re.sub(email_pattern, '[REDACTED EMAIL]', redacted)
            self.redacted_fields.add('email')
        
        # Addresses (lines with numbers and street keywords)
        address_pattern = r'\d+[A-Za-z0-9\s,]*(?:Street|St|Road|Rd|Avenue|Ave|Lane|Lane|Drive|Drive|Court|Crescent|Ct|Close|Grove|Park|Place|Plaza|Rise|Square|Sq|Walk|Way|Terrace|View|Villas|Wynd)\b'
        if re.search(address_pattern, redacted):
            redacted = re.sub(address_pattern, '[REDACTED ADDRESS]', redacted)
            self.redacted_fields.add('address')
        
        # Names (capitalized words at line start)
        # This is conservative to avoid over-redaction
        name_pattern = r'^([A-Z][A-Za-z]+\s)+([A-Z][A-Za-z]+)$'
        lines = redacted.split('\n')
        for i, line in enumerate(lines):
            if re.match(name_pattern, line.strip()) and len(line.strip().split()) <= 4:
                lines[i] = '[REDACTED NAME]'
                self.redacted_fields.add('name')
        redacted = '\n'.join(lines)
        
        # NRIC (Singapore format: SXXXX###X)
        nric_pattern = r'S\d{4}\d{3}[A-Z]'
        if re.search(nric_pattern, redacted):
            redacted = re.sub(nric_pattern, '[REDACTED NRIC]', redacted)
            self.redacted_fields.add('nric')
        
        return redacted
    
    def redact_dict(self, data: dict, pii_fields: list) -> dict:
        """
        Redact specific fields in a dictionary
        Args:
            data: Dictionary to redact
            pii_fields: List of field names to redact
        """
        redacted = data.copy()
        for field in pii_fields:
            if field in redacted:
                redacted[field] = '[REDACTED]'
                self.redacted_fields.add(field)
        return redacted
    
    def get_redacted_fields(self) -> list:
        """Return list of fields that were redacted"""
        return list(self.redacted_fields)
    
    def reset_redacted_fields(self):
        """Reset the redacted fields tracker"""
        self.redacted_fields.clear()


# Global instance
_encryption_manager: EncryptionManager = None


def get_encryption_manager() -> EncryptionManager:
    """Get or create global encryption manager"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def encrypt_field(plaintext: str) -> str:
    """Encrypt a field"""
    return get_encryption_manager().encrypt_field(plaintext)


def decrypt_field(encrypted_b64: str) -> str:
    """Decrypt a field"""
    return get_encryption_manager().decrypt_field(encrypted_b64)


def redact_pii(text: str) -> str:
    """Redact PII from text"""
    manager = get_encryption_manager()
    manager.reset_redacted_fields()
    return manager.redact_pii(text)


def redact_dict(data: dict, pii_fields: list) -> dict:
    """Redact specific fields in a dictionary"""
    return get_encryption_manager().redact_dict(data, pii_fields)


def get_redacted_fields() -> list:
    """Get list of redacted fields from last operation"""
    return get_encryption_manager().get_redacted_fields()
