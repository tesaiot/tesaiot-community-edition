# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
API Key Usage Tracking Service for TESA IoT Platform
Records API key usage to TimescaleDB for analytics
"""

import logging
import psycopg2
from datetime import datetime
import hashlib
import time
from flask import request, g
import os

logger = logging.getLogger(__name__)

class APIKeyTrackingService:
    """Service to track API key usage in TimescaleDB"""
    
    def __init__(self):
        self.conn = None
        
    def get_connection(self):
        """Get or create TimescaleDB connection"""
        if not self.conn or self.conn.closed:
            try:
                self.conn = psycopg2.connect(
                    host=os.getenv('POSTGRES_HOST', 'tesa-timescaledb'),
                    port=os.getenv('POSTGRES_PORT', 5432),
                    database=os.getenv('POSTGRES_DB', 'tesa_telemetry'),
                    user=os.getenv('POSTGRES_USER', 'postgres'),
                    password=os.getenv('POSTGRES_PASSWORD', '')  # no default; fails closed
                )
                self.conn.autocommit = True
            except Exception as e:
                logger.error(f"Failed to connect to TimescaleDB: {e}")
                return None
        return self.conn
    
    def objectid_to_uuid(self, oid):
        """Convert MongoDB ObjectId to a consistent UUID for TimescaleDB"""
        hash_obj = hashlib.md5(str(oid).encode())
        hex_dig = hash_obj.hexdigest()
        return f"{hex_dig[:8]}-{hex_dig[8:12]}-{hex_dig[12:16]}-{hex_dig[16:20]}-{hex_dig[20:32]}"
    
    def track_api_usage(self, api_key_doc, endpoint, method, status_code, response_time_ms, 
                       request_size=0, response_size=0, error_message=None):
        """
        Track API key usage to TimescaleDB
        
        Args:
            api_key_doc: MongoDB API key document
            endpoint: API endpoint path
            method: HTTP method
            status_code: HTTP response status code
            response_time_ms: Response time in milliseconds
            request_size: Request body size in bytes
            response_size: Response body size in bytes
            error_message: Error message if any
        """
        try:
            conn = self.get_connection()
            if not conn:
                logger.error("No TimescaleDB connection available")
                return
            
            cursor = conn.cursor()
            
            # Convert ObjectId to UUID
            api_key_uuid = self.objectid_to_uuid(api_key_doc['_id'])
            org_uuid = self.objectid_to_uuid(api_key_doc['organization_id'])
            
            # Get request details
            ip_address = request.remote_addr or request.environ.get('HTTP_X_FORWARDED_FOR', '0.0.0.0')
            user_agent = request.headers.get('User-Agent', 'Unknown')
            
            # Insert usage record
            insert_query = """
                INSERT INTO api_key_usage (
                    api_key_id, timestamp, endpoint, method, status_code,
                    response_time_ms, ip_address, user_agent, 
                    request_size_bytes, response_size_bytes,
                    organization_id, error_message
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s
                )
            """
            
            cursor.execute(insert_query, (
                api_key_uuid,
                datetime.utcnow(),
                endpoint[:255],  # Truncate to fit column size
                method[:10],
                status_code,
                response_time_ms,
                ip_address[:45],
                user_agent,
                request_size,
                response_size,
                org_uuid,
                error_message[:500] if error_message else None
            ))
            
            cursor.close()
            logger.debug(f"Tracked API usage: {method} {endpoint} - {status_code} ({response_time_ms}ms)")
            
        except Exception as e:
            logger.error(f"Failed to track API usage: {e}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

# Global instance
api_tracking_service = APIKeyTrackingService()


def track_external_api_request(response):
    """
    Flask after_request handler to track external API usage
    Should be called for all external API endpoints
    """
    try:
        # Only track if we have API key context
        if not hasattr(g, 'api_key') or not g.api_key:
            return response
        
        # Calculate response time if available
        response_time_ms = 0
        if hasattr(g, 'request_start_time'):
            response_time_ms = int((time.time() - g.request_start_time) * 1000)
        
        # Get request and response sizes
        request_size = len(request.get_data()) if request.data else 0
        response_size = len(response.get_data()) if response.data else 0
        
        # Track the usage
        api_tracking_service.track_api_usage(
            api_key_doc=g.api_key,
            endpoint=request.path,
            method=request.method,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            request_size=request_size,
            response_size=response_size,
            error_message=None if response.status_code < 400 else response.get_data(as_text=True)[:500]
        )
        
    except Exception as e:
        logger.error(f"Error in track_external_api_request: {e}")
    
    return response


def before_request_timer():
    """Set request start time for tracking response time"""
    g.request_start_time = time.time()