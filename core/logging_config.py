"""
Structured Logging Configuration for AI Gatekeeper
Provides JSON logging, correlation IDs, and audit trails
"""

import logging
import json
import sys
import os
from datetime import datetime
from typing import Any, Dict
from contextvars import ContextVar

# Request context variables for correlation
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')
session_id_var: ContextVar[str] = ContextVar('session_id', default='')


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'thread_name': record.threadName
        }

        # Add request context
        request_id = request_id_var.get()
        if request_id:
            log_data['request_id'] = request_id

        user_id = user_id_var.get()
        if user_id:
            log_data['user_id'] = user_id

        session_id = session_id_var.get()
        if session_id:
            log_data['session_id'] = session_id

        # Add exception info
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }

        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data

        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record in human-readable format."""
        # Get request context
        request_id = request_id_var.get()
        context_str = f" [req:{request_id[:8]}]" if request_id else ""

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

        # Build message
        message = f"{timestamp} - {record.levelname:8s} - {record.name}{context_str} - {record.getMessage()}"

        # Add exception if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


def setup_logging(
    log_level: str = None,
    json_logs: bool = None,
    log_file: str = None
):
    """
    Setup application logging.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Use JSON formatted logs (default: True in production)
        log_file: Optional log file path
    """
    # Determine configuration from environment
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO')

    if json_logs is None:
        # Use JSON in production, human-readable in development
        environment = os.getenv('ENVIRONMENT', 'development')
        json_logs = environment == 'production'

    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)

    # Set formatter
    if json_logs:
        formatter = StructuredFormatter()
    else:
        formatter = HumanReadableFormatter()

    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    logging.info(f"Logging configured: level={log_level}, json={json_logs}")


class AuditLogger:
    """Audit logging for security and compliance."""

    def __init__(self, log_dir: str = None):
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)

        # Separate audit log file
        if log_dir is None:
            log_dir = os.getenv('LOG_DIR', '/var/log/ai-gatekeeper')

        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        # Add file handler for audit logs
        audit_file = os.path.join(log_dir, 'audit.log')
        handler = logging.FileHandler(audit_file)
        handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(handler)

        # Also log to console in development
        if os.getenv('ENVIRONMENT', 'development') == 'development':
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(HumanReadableFormatter())
            self.logger.addHandler(console_handler)

    def log_authentication(
        self,
        user_id: str,
        method: str,
        success: bool,
        ip_address: str,
        details: Dict[str, Any] = None
    ):
        """Log authentication attempt."""
        self.logger.info(
            f"Authentication {'successful' if success else 'failed'}: user={user_id}, method={method}",
            extra={
                'extra_data': {
                    'event_type': 'authentication',
                    'user_id': user_id,
                    'method': method,
                    'success': success,
                    'ip_address': ip_address,
                    'details': details or {}
                }
            }
        )

    def log_authorization(
        self,
        user_id: str,
        resource: str,
        action: str,
        allowed: bool,
        reason: str = None
    ):
        """Log authorization decision."""
        self.logger.info(
            f"Authorization {'granted' if allowed else 'denied'}: user={user_id}, resource={resource}, action={action}",
            extra={
                'extra_data': {
                    'event_type': 'authorization',
                    'user_id': user_id,
                    'resource': resource,
                    'action': action,
                    'allowed': allowed,
                    'reason': reason
                }
            }
        )

    def log_data_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        success: bool
    ):
        """Log data access."""
        self.logger.info(
            f"Data access: user={user_id}, resource={resource_type}:{resource_id}, action={action}",
            extra={
                'extra_data': {
                    'event_type': 'data_access',
                    'user_id': user_id,
                    'resource_type': resource_type,
                    'resource_id': resource_id,
                    'action': action,
                    'success': success
                }
            }
        )

    def log_configuration_change(
        self,
        user_id: str,
        component: str,
        old_value: Any,
        new_value: Any,
        change_reason: str = None
    ):
        """Log configuration change."""
        self.logger.warning(
            f"Configuration changed: component={component}, by={user_id}",
            extra={
                'extra_data': {
                    'event_type': 'configuration_change',
                    'user_id': user_id,
                    'component': component,
                    'old_value': str(old_value),
                    'new_value': str(new_value),
                    'reason': change_reason
                }
            }
        )

    def log_escalation(
        self,
        ticket_id: str,
        reason: str,
        escalated_by: str,
        confidence_score: float = None,
        risk_score: float = None
    ):
        """Log ticket escalation."""
        self.logger.info(
            f"Ticket escalated: ticket={ticket_id}, reason={reason}",
            extra={
                'extra_data': {
                    'event_type': 'escalation',
                    'ticket_id': ticket_id,
                    'reason': reason,
                    'escalated_by': escalated_by,
                    'confidence_score': confidence_score,
                    'risk_score': risk_score
                }
            }
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        user_id: str = None,
        ip_address: str = None,
        details: Dict[str, Any] = None
    ):
        """Log security event."""
        log_level = {
            'critical': logging.CRITICAL,
            'high': logging.ERROR,
            'medium': logging.WARNING,
            'low': logging.INFO
        }.get(severity.lower(), logging.WARNING)

        self.logger.log(
            log_level,
            f"Security event: {event_type} - {description}",
            extra={
                'extra_data': {
                    'event_type': 'security',
                    'security_event_type': event_type,
                    'severity': severity,
                    'description': description,
                    'user_id': user_id,
                    'ip_address': ip_address,
                    'details': details or {}
                }
            }
        )


# Global audit logger instance
audit_logger = None


def init_audit_logger(log_dir: str = None) -> AuditLogger:
    """
    Initialize audit logger.

    Args:
        log_dir: Directory for audit logs

    Returns:
        AuditLogger instance
    """
    global audit_logger
    audit_logger = AuditLogger(log_dir)
    logging.info(f"Audit logger initialized: log_dir={log_dir or '/var/log/ai-gatekeeper'}")
    return audit_logger


def get_audit_logger() -> AuditLogger:
    """Get audit logger instance."""
    if audit_logger is None:
        return init_audit_logger()
    return audit_logger
