"""
Logging Utilities
Replaces lib/logger.ts with Python implementation
"""

import logging
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger
from supabase import create_client, Client
import uuid


class ContextualLogger:
    """Logger with context support"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}
        
        # Set up logging
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
    
    def set_context(self, context: Dict[str, Any]):
        """Set context for logging"""
        self.context = context
    
    def _add_context(self, extra: Dict[str, Any]) -> Dict[str, Any]:
        """Merge context with extra data"""
        return {**self.context, **extra}
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Debug log"""
        self.logger.debug(message, extra=self._add_context(extra or {}))
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Info log"""
        self.logger.info(message, extra=self._add_context(extra or {}))
    
    def warn(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Warning log"""
        self.logger.warning(message, extra=self._add_context(extra or {}))
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Error log"""
        self.logger.error(message, extra=self._add_context(extra or {}))
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Critical log"""
        self.logger.critical(message, extra=self._add_context(extra or {}))


# Global logger instance
logger = ContextualLogger("utility-bill-calculator")


class AuditLogger:
    """Handles audit logging to Supabase"""
    
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            logger.warn("Supabase credentials not configured, audit logging disabled")
            self.client: Optional[Client] = None
        else:
            self.client = create_client(self.supabase_url, self.supabase_key)
    
    async def create_audit_log(
        self,
        workflow_id: str,
        tenant_id: str,
        action: str,
        stage: str,
        status: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        pii_redacted_fields: Optional[list] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Create an audit log entry in Supabase
        Returns: True if successful, False otherwise
        """
        if not self.client:
            logger.warn("Audit logging disabled, skipping log creation")
            return False
        
        try:
            audit_entry = {
                "id": str(uuid.uuid4()),
                "workflow_id": workflow_id,
                "tenant_id": tenant_id,
                "action": action,
                "stage": stage,
                "status": status,
                "input_data": input_data,
                "output_data": output_data,
                "pii_redacted_fields": pii_redacted_fields or [],
                "error": error,
                "created_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }
            
            # Insert into Supabase
            response = self.client.table("audit_logs").insert(audit_entry).execute()
            
            logger.info(f"Audit log created: {action}", {
                "workflow_id": workflow_id,
                "tenant_id": tenant_id,
            })
            
            return True
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            return False


# Global audit logger instance
audit_logger = AuditLogger()


async def create_audit_log(
    workflow_id: str,
    tenant_id: str,
    action: str,
    stage: str,
    status: str,
    input_data: Optional[Dict[str, Any]] = None,
    output_data: Optional[Dict[str, Any]] = None,
    pii_redacted_fields: Optional[list] = None,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Create audit log entry"""
    return await audit_logger.create_audit_log(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        action=action,
        stage=stage,
        status=status,
        input_data=input_data,
        output_data=output_data,
        pii_redacted_fields=pii_redacted_fields,
        error=error,
        metadata=metadata,
    )
