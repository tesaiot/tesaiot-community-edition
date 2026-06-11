# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Logging Configuration
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



Security contact: see SECURITY.md in the distribution root.
"""

import logging
import sys
import json
from datetime import datetime

try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False

if HAS_JSON_LOGGER:
    class CustomJsonFormatter(jsonlogger.JsonFormatter):
        """Custom JSON formatter with additional fields."""
        
        def add_fields(self, log_record, record, message_dict):
            super().add_fields(log_record, record, message_dict)
            
            # Add timestamp
            log_record['timestamp'] = datetime.utcnow().isoformat()
            
            # Add log level
            log_record['level'] = record.levelname
            
            # Add module info
            log_record['module'] = record.module
            log_record['function'] = record.funcName
            log_record['line'] = record.lineno
            
            # Add service info
            log_record['service'] = 'tesa-iot-api'
            log_record['version'] = 'v2025.08-rc.3'
else:
    # Fallback formatter when pythonjsonlogger is not available
    class CustomJsonFormatter(logging.Formatter):
        """Simple JSON formatter fallback."""
        
        def format(self, record):
            log_obj = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
                'message': record.getMessage(),
                'service': 'tesa-iot-api',
                'version': 'v2025.08-rc.3'
            }
            return json.dumps(log_obj)

def setup_logging(app):
    """
    Setup structured logging for the application.
    
    Args:
        app: Flask application instance
    """
    import os
    from logging.handlers import RotatingFileHandler
    
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    log_dir = app.config.get('LOG_DIR', '/app/logs')
    
    # Create log directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    json_formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    console_handler.setFormatter(json_formatter)
    
    # Configure root logger
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.addHandler(console_handler)
    
    # Configure Flask logger
    app.logger.setLevel(getattr(logging, log_level))
    
    # Configure specialized loggers for audit, security, etc.
    audit_loggers = {
        'audit': os.path.join(log_dir, 'audit.log'),
        'security': os.path.join(log_dir, 'security.log'),
        'admin': os.path.join(log_dir, 'admin.log'),
        'auth': os.path.join(log_dir, 'auth.log'),
        'api': os.path.join(log_dir, 'api.log')
    }
    
    for logger_name, log_file in audit_loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        
        # Add file handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)
        
        # Also add console handler for visibility
        logger.addHandler(console_handler)
    
    # Silence noisy libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('hvac').setLevel(logging.WARNING)
    
    app.logger.info("Logging configured", extra={
        'log_level': log_level,
        'handlers': ['console', 'file'],
        'log_dir': log_dir,
        'audit_loggers': list(audit_loggers.keys())
    })

class StructuredLogger:
    """Structured logger with context support."""
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
    
    def _log(self, level, message, context=None, **kwargs):
        """Log with structured context."""
        extra = {'context': context or {}}
        extra.update(kwargs)
        getattr(self.logger, level)(message, extra=extra)
    
    def debug(self, message, context=None, **kwargs):
        """Log debug message."""
        self._log('debug', message, context, **kwargs)
    
    def info(self, message, context=None, **kwargs):
        """Log info message."""
        self._log('info', message, context, **kwargs)
    
    def warning(self, message, context=None, **kwargs):
        """Log warning message."""
        self._log('warning', message, context, **kwargs)
    
    def error(self, message, context=None, **kwargs):
        """Log error message."""
        self._log('error', message, context, **kwargs)
    
    def critical(self, message, context=None, **kwargs):
        """Log critical message."""
        self._log('critical', message, context, **kwargs)