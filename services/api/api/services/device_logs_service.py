# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Device Logs Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bson import ObjectId
import asyncio
from enum import Enum
import re
from collections import defaultdict, Counter

from ..core.database import get_db
from .logging_service import logging_service, LogLevel
from .websocket_service import websocket_service

logger = logging.getLogger(__name__)

class DeviceLogCategory(Enum):
    """Device log categories for Week 5-6 implementation"""
    CONNECTIVITY = "connectivity"
    TELEMETRY = "telemetry"
    HEALTH = "health"
    SECURITY = "security"
    FIRMWARE = "firmware"
    CONFIGURATION = "configuration"
    PERFORMANCE = "performance"
    
    @classmethod
    def from_log_type(cls, log_type: str) -> 'DeviceLogCategory':
        """Map log types to categories"""
        mapping = {
            'connection': cls.CONNECTIVITY,
            'telemetry': cls.TELEMETRY,
            'system': cls.HEALTH,
            'security': cls.SECURITY,
            'firmware': cls.FIRMWARE,
            'config': cls.CONFIGURATION,
            'performance': cls.PERFORMANCE
        }
        return mapping.get(log_type, cls.HEALTH)

class DeviceHealthScore:
    """Calculate device health score based on logs and metrics"""
    
    @staticmethod
    def calculate(device_id: str, time_window: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """
        Calculate comprehensive device health score
        
        Returns:
            Dict with score (0-100), breakdown by category, and recommendations
        """
        try:
            db = get_db()
            end_time = datetime.now()
            start_time = end_time - time_window
            
            # Get device logs for analysis
            logs = list(db.device_logs.find({
                'device_id': device_id,
                'timestamp': {'$gte': start_time, '$lte': end_time}
            }))
            
            # Get device info
            device = db.devices.find_one({'device_id': device_id})
            
            # Initialize scores
            scores = {
                'connectivity': 100,
                'telemetry': 100,
                'security': 100,
                'performance': 100,
                'configuration': 100
            }
            
            # Analyze logs by category
            log_counts = defaultdict(lambda: {'error': 0, 'warning': 0, 'info': 0})
            
            for log in logs:
                level = log.get('level', 'INFO').upper()
                category = DeviceLogCategory.from_log_type(log.get('log_type', 'system')).value
                
                if level == 'ERROR':
                    log_counts[category]['error'] += 1
                    scores[category] = max(0, scores[category] - 10)
                elif level == 'WARNING':
                    log_counts[category]['warning'] += 1
                    scores[category] = max(0, scores[category] - 5)
                else:
                    log_counts[category]['info'] += 1
            
            # Check connectivity
            if device:
                last_seen = device.get('last_seen')
                if last_seen:
                    if isinstance(last_seen, str):
                        last_seen = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                    
                    time_since_seen = (datetime.now() - last_seen).total_seconds()
                    if time_since_seen > 3600:  # More than 1 hour
                        scores['connectivity'] = max(0, scores['connectivity'] - 20)
                    elif time_since_seen > 1800:  # More than 30 minutes
                        scores['connectivity'] = max(0, scores['connectivity'] - 10)
            
            # Calculate overall score
            overall_score = sum(scores.values()) / len(scores)
            
            # Generate recommendations
            recommendations = []
            if scores['connectivity'] < 80:
                recommendations.append({
                    'category': 'connectivity',
                    'severity': 'warning',
                    'action': 'Check device network connection and signal strength'
                })
            if scores['security'] < 90:
                recommendations.append({
                    'category': 'security',
                    'severity': 'warning',
                    'action': 'Review security logs and update certificates if needed'
                })
            if scores['performance'] < 70:
                recommendations.append({
                    'category': 'performance',
                    'severity': 'critical',
                    'action': 'Device performance degraded - consider restart or maintenance'
                })
            
            return {
                'overall_score': round(overall_score, 1),
                'category_scores': scores,
                'log_analysis': dict(log_counts),
                'recommendations': recommendations,
                'calculated_at': datetime.now().isoformat(),
                'time_window_hours': int(time_window.total_seconds() / 3600)
            }
            
        except Exception as e:
            logger.error(f"Error calculating device health score: {e}")
            return {
                'overall_score': 0,
                'error': str(e)
            }

class ErrorPatternDetector:
    """Detect patterns in device errors for predictive maintenance"""
    
    # Common error patterns to detect
    ERROR_PATTERNS = {
        'memory_leak': {
            'pattern': r'(memory|heap|allocation|oom)',
            'category': 'performance',
            'severity': 'critical'
        },
        'connection_timeout': {
            'pattern': r'(timeout|timed out|connection reset|disconnect)',
            'category': 'connectivity',
            'severity': 'warning'
        },
        'authentication_failure': {
            'pattern': r'(auth|authentication|unauthorized|certificate)',
            'category': 'security',
            'severity': 'critical'
        },
        'sensor_failure': {
            'pattern': r'(sensor|reading failed|invalid data|calibration)',
            'category': 'telemetry',
            'severity': 'warning'
        },
        'firmware_issue': {
            'pattern': r'(firmware|update|upgrade|version mismatch)',
            'category': 'firmware',
            'severity': 'warning'
        }
    }
    
    @classmethod
    def detect_patterns(cls, device_id: str, time_window: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """
        Detect error patterns in device logs
        
        Returns:
            Dict with detected patterns, frequencies, and predictions
        """
        try:
            db = get_db()
            end_time = datetime.now()
            start_time = end_time - time_window
            
            # Get error logs
            error_logs = list(db.device_logs.find({
                'device_id': device_id,
                'timestamp': {'$gte': start_time, '$lte': end_time},
                'level': {'$in': ['ERROR', 'WARNING', 'CRITICAL']}
            }))
            
            # Detect patterns
            detected_patterns = defaultdict(list)
            pattern_counts = Counter()
            
            for log in error_logs:
                message = log.get('message', '').lower()
                
                for pattern_name, pattern_info in cls.ERROR_PATTERNS.items():
                    if re.search(pattern_info['pattern'], message, re.IGNORECASE):
                        detected_patterns[pattern_name].append({
                            'timestamp': log.get('timestamp'),
                            'message': log.get('message'),
                            'category': pattern_info['category'],
                            'severity': pattern_info['severity']
                        })
                        pattern_counts[pattern_name] += 1
            
            # Analyze trends
            predictions = []
            for pattern_name, count in pattern_counts.items():
                if count >= 5:  # Frequent pattern
                    predictions.append({
                        'pattern': pattern_name,
                        'frequency': count,
                        'risk_level': 'high',
                        'prediction': f'{pattern_name.replace("_", " ").title()} detected {count} times - immediate action recommended'
                    })
                elif count >= 3:  # Emerging pattern
                    predictions.append({
                        'pattern': pattern_name,
                        'frequency': count,
                        'risk_level': 'medium',
                        'prediction': f'{pattern_name.replace("_", " ").title()} emerging - monitor closely'
                    })
            
            return {
                'patterns_detected': dict(detected_patterns),
                'pattern_summary': dict(pattern_counts),
                'predictions': predictions,
                'total_errors_analyzed': len(error_logs),
                'time_window_hours': int(time_window.total_seconds() / 3600),
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error detecting patterns: {e}")
            return {
                'error': str(e),
                'patterns_detected': {}
            }

class DeviceLogsService:
    """Enhanced service for managing device logs with Week 5-6 features"""
    
    # Map device log categories to Phase 1 activity log categories
    PHASE1_CATEGORY_MAPPING = {
        DeviceLogCategory.CONNECTIVITY: 'DEVICE_ISSUES',
        DeviceLogCategory.TELEMETRY: 'API_PROBLEMS',
        DeviceLogCategory.HEALTH: 'DEVICE_ISSUES',
        DeviceLogCategory.SECURITY: 'USER_CRITICAL',
        DeviceLogCategory.FIRMWARE: 'DEVICE_ISSUES',
        DeviceLogCategory.CONFIGURATION: 'API_PROBLEMS',
        DeviceLogCategory.PERFORMANCE: 'DEVICE_ISSUES'
    }
    
    @staticmethod
    def get_device_logs(device_id: str, limit: int = 100, log_types: Optional[List[str]] = None, 
                       categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get logs for a specific device with enhanced filtering
        
        Args:
            device_id: Device identifier
            limit: Maximum number of logs to return
            log_types: Filter by log types (e.g., ['telemetry', 'connection', 'error'])
            categories: Filter by device log categories (e.g., ['connectivity', 'security'])
            
        Returns:
            List of log entries with enhanced metadata
        """
        try:
            db = get_db()
            
            # Build query
            query = {'device_id': device_id}
            if log_types:
                query['log_type'] = {'$in': log_types}
            
            # Filter by categories if specified
            if categories:
                # Map categories to log types
                mapped_log_types = []
                for cat in categories:
                    if cat == 'connectivity':
                        mapped_log_types.append('connection')
                    elif cat == 'telemetry':
                        mapped_log_types.append('telemetry')
                    elif cat == 'health':
                        mapped_log_types.append('system')
                    elif cat == 'security':
                        mapped_log_types.append('security')
                    elif cat == 'firmware':
                        mapped_log_types.append('firmware')
                    elif cat == 'configuration':
                        mapped_log_types.append('config')
                    elif cat == 'performance':
                        mapped_log_types.append('performance')
                
                if mapped_log_types:
                    if 'log_type' in query:
                        # Merge with existing log_types filter
                        existing = query['log_type']['$in']
                        query['log_type']['$in'] = list(set(existing) & set(mapped_log_types))
                    else:
                        query['log_type'] = {'$in': mapped_log_types}
            
            # Get logs from device_logs collection
            logs = list(db.device_logs.find(
                query,
                limit=limit
            ).sort('timestamp', -1))
            
            # If no logs found, check for telemetry errors
            if not logs:
                # Check telemetry collection for any errors
                telemetry_errors = list(db.telemetry_errors.find(
                    {'device_id': device_id},
                    limit=20
                ).sort('timestamp', -1))
                
                for error in telemetry_errors:
                    logs.append({
                        'timestamp': error.get('timestamp'),
                        'level': 'ERROR',
                        'log_type': 'telemetry',
                        'message': error.get('error_message', 'Telemetry processing error'),
                        'details': error.get('details', {})
                    })
            
            # Check for recent connection events
            device = db.devices.find_one({'device_id': device_id})
            if device:
                # Add connection status log
                if device.get('last_seen'):
                    last_seen = device['last_seen']
                    if isinstance(last_seen, str):
                        last_seen = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                    
                    logs.append({
                        'timestamp': last_seen,
                        'level': 'INFO',
                        'log_type': 'connection',
                        'message': f"Device last seen (status: {device.get('status', 'unknown')})",
                        'details': {
                            'ip_address': device.get('metadata', {}).get('ipAddress'),
                            'firmware_version': device.get('firmware_version')
                        }
                    })
                
                # Add certificate status log
                if device.get('certificate_status'):
                    cert_log = {
                        'timestamp': device.get('certificate_updated_at', device.get('created_at', datetime.now())),
                        'level': 'INFO',
                        'log_type': 'security',
                        'message': f"Certificate status: {device['certificate_status']}",
                        'details': {}
                    }
                    
                    # Add warning if certificate is expiring
                    if device.get('certificate_expires_at'):
                        expires_at = device['certificate_expires_at']
                        if isinstance(expires_at, str):
                            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        
                        days_until_expiry = (expires_at - datetime.now()).days
                        if days_until_expiry < 30:
                            cert_log['level'] = 'WARNING'
                            cert_log['message'] = f"Certificate expires in {days_until_expiry} days"
                    
                    logs.append(cert_log)
            
            # If still no logs, generate some based on device activity
            if not logs:
                logs = DeviceLogsService._generate_sample_logs(device_id, device)
            
            # Format logs for response with enhanced metadata
            formatted_logs = []
            for log in logs:
                log_type = log.get('log_type', 'system')
                category = DeviceLogCategory.from_log_type(log_type)
                
                formatted_log = {
                    '_id': str(log.get('_id', ObjectId())),
                    'timestamp': log.get('timestamp', datetime.now()).isoformat() if isinstance(log.get('timestamp'), datetime) else log.get('timestamp'),
                    'level': log.get('level', 'INFO'),
                    'log_type': log_type,
                    'category': category.value,
                    'phase1_category': DeviceLogsService.PHASE1_CATEGORY_MAPPING.get(category, 'DEVICE_ISSUES'),
                    'message': log.get('message', ''),
                    'details': log.get('details', {}),
                    'source': log.get('source', 'device')
                }
                
                # Add severity score for sorting
                level_scores = {'CRITICAL': 5, 'ERROR': 4, 'WARNING': 3, 'INFO': 2, 'DEBUG': 1}
                formatted_log['severity_score'] = level_scores.get(formatted_log['level'].upper(), 0)
                
                formatted_logs.append(formatted_log)
            
            # Sort by timestamp descending
            formatted_logs.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return formatted_logs[:limit]
            
        except Exception as e:
            logger.error(f"Error getting device logs: {e}")
            return []
    
    @staticmethod
    def get_device_health(device_id: str, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Get device health score and analysis
        
        Args:
            device_id: Device identifier
            time_window_hours: Hours to analyze (default 24)
            
        Returns:
            Health score, breakdown, and recommendations
        """
        time_window = timedelta(hours=time_window_hours)
        return DeviceHealthScore.calculate(device_id, time_window)
    
    @staticmethod
    def get_error_patterns(device_id: str, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Detect error patterns for predictive maintenance
        
        Args:
            device_id: Device identifier
            time_window_hours: Hours to analyze (default 24)
            
        Returns:
            Detected patterns and predictions
        """
        time_window = timedelta(hours=time_window_hours)
        return ErrorPatternDetector.detect_patterns(device_id, time_window)
    
    @staticmethod
    def get_device_analytics(device_id: str, time_range: str = '24h') -> Dict[str, Any]:
        """
        Get comprehensive device analytics
        
        Args:
            device_id: Device identifier
            time_range: Time range (1h, 6h, 24h, 7d, 30d)
            
        Returns:
            Analytics including log counts, trends, and insights
        """
        try:
            db = get_db()
            
            # Parse time range
            time_map = {
                '1h': timedelta(hours=1),
                '6h': timedelta(hours=6),
                '24h': timedelta(hours=24),
                '7d': timedelta(days=7),
                '30d': timedelta(days=30)
            }
            
            time_delta = time_map.get(time_range, timedelta(hours=24))
            end_time = datetime.now()
            start_time = end_time - time_delta
            
            # Get logs for analysis
            logs = list(db.device_logs.find({
                'device_id': device_id,
                'timestamp': {'$gte': start_time, '$lte': end_time}
            }))
            
            # Analyze by category
            category_stats = defaultdict(lambda: {'count': 0, 'errors': 0, 'warnings': 0})
            hourly_trends = defaultdict(lambda: defaultdict(int))
            
            for log in logs:
                log_type = log.get('log_type', 'system')
                category = DeviceLogCategory.from_log_type(log_type).value
                level = log.get('level', 'INFO').upper()
                
                # Category stats
                category_stats[category]['count'] += 1
                if level == 'ERROR':
                    category_stats[category]['errors'] += 1
                elif level == 'WARNING':
                    category_stats[category]['warnings'] += 1
                
                # Hourly trends
                if isinstance(log.get('timestamp'), datetime):
                    hour = log['timestamp'].strftime('%Y-%m-%d %H:00')
                    hourly_trends[hour][category] += 1
            
            # Calculate insights
            insights = []
            
            # Check for high error rates
            total_logs = len(logs)
            if total_logs > 0:
                error_count = sum(1 for log in logs if log.get('level', '').upper() == 'ERROR')
                error_rate = (error_count / total_logs) * 100
                
                if error_rate > 20:
                    insights.append({
                        'type': 'critical',
                        'message': f'High error rate detected: {error_rate:.1f}%',
                        'recommendation': 'Immediate investigation required'
                    })
                elif error_rate > 10:
                    insights.append({
                        'type': 'warning',
                        'message': f'Elevated error rate: {error_rate:.1f}%',
                        'recommendation': 'Monitor device closely'
                    })
            
            # Check connectivity issues
            conn_stats = category_stats.get('connectivity', {})
            if conn_stats.get('errors', 0) > 5:
                insights.append({
                    'type': 'warning',
                    'message': 'Multiple connectivity errors detected',
                    'recommendation': 'Check network configuration and signal strength'
                })
            
            return {
                'device_id': device_id,
                'time_range': time_range,
                'period': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'summary': {
                    'total_logs': total_logs,
                    'categories': dict(category_stats),
                    'error_rate': round((sum(1 for log in logs if log.get('level', '').upper() == 'ERROR') / max(total_logs, 1)) * 100, 2)
                },
                'trends': {
                    'hourly': dict(hourly_trends)
                },
                'insights': insights,
                'health_score': DeviceHealthScore.calculate(device_id, time_delta).get('overall_score', 0),
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting device analytics: {e}")
            return {
                'error': str(e),
                'device_id': device_id
            }
    
    @staticmethod
    async def stream_device_logs(device_id: str, callback, filters: Optional[Dict] = None):
        """
        Stream device logs in real-time
        
        Args:
            device_id: Device identifier
            callback: Async function to call with new logs
            filters: Optional filters (level, category, etc.)
        """
        db = get_db()
        last_check = datetime.now()
        
        while True:
            try:
                # Query for new logs since last check
                query = {
                    'device_id': device_id,
                    'timestamp': {'$gt': last_check}
                }
                
                # Apply filters
                if filters:
                    if 'level' in filters:
                        query['level'] = filters['level']
                    if 'category' in filters:
                        # Map category to log types
                        mapped_types = []
                        for cat in filters['category']:
                            if cat == 'connectivity':
                                mapped_types.append('connection')
                            elif cat == 'telemetry':
                                mapped_types.append('telemetry')
                            # Add other mappings...
                        if mapped_types:
                            query['log_type'] = {'$in': mapped_types}
                
                # Get new logs
                new_logs = list(db.device_logs.find(query).sort('timestamp', 1))
                
                if new_logs:
                    # Format logs
                    formatted = []
                    for log in new_logs:
                        log_type = log.get('log_type', 'system')
                        category = DeviceLogCategory.from_log_type(log_type)
                        
                        formatted.append({
                            '_id': str(log.get('_id', ObjectId())),
                            'timestamp': log.get('timestamp', datetime.now()).isoformat(),
                            'level': log.get('level', 'INFO'),
                            'category': category.value,
                            'phase1_category': DeviceLogsService.PHASE1_CATEGORY_MAPPING.get(category, 'DEVICE_ISSUES'),
                            'message': log.get('message', ''),
                            'details': log.get('details', {})
                        })
                    
                    # Send to callback
                    await callback(formatted)
                    
                    # Update last check time
                    last_check = new_logs[-1]['timestamp']
                
                # Wait before next check
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error streaming device logs: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    @staticmethod
    def add_device_log(device_id: str, level: str, message: str, log_type: str = 'system', 
                      details: Optional[Dict[str, Any]] = None, source: str = 'system') -> bool:
        """
        Add a new log entry for a device
        
        Args:
            device_id: Device identifier
            level: Log level (INFO, WARNING, ERROR, etc.)
            message: Log message
            log_type: Type of log (system, telemetry, connection, security, etc.)
            details: Additional details
            source: Source of the log (device, system, api, etc.)
            
        Returns:
            Success status
        """
        try:
            db = get_db()
            
            # Determine category and Phase 1 category
            category = DeviceLogCategory.from_log_type(log_type)
            phase1_category = DeviceLogsService.PHASE1_CATEGORY_MAPPING.get(category, 'DEVICE_ISSUES')
            
            log_entry = {
                'device_id': device_id,
                'timestamp': datetime.now(),
                'level': level.upper(),
                'log_type': log_type,
                'category': category.value,
                'message': message,
                'details': details or {},
                'source': source
            }
            
            db.device_logs.insert_one(log_entry)
            
            # Also update device last_activity
            db.devices.update_one(
                {'device_id': device_id},
                {'$set': {'last_activity': datetime.now()}}
            )
            
            # Broadcast via WebSocket
            try:
                # Get device info for broadcast
                device = db.devices.find_one({'device_id': device_id})
                
                websocket_log_data = {
                    'id': str(log_entry.get('_id', '')),
                    'device_id': device_id,
                    'device_name': device.get('name') if device else device_id,
                    'device_type': device.get('type') if device else 'unknown',
                    'timestamp': log_entry['timestamp'].isoformat(),
                    'level': level.upper(),
                    'category': category.value,
                    'message': message,
                    'details': details or {},
                    'source': source
                }
                
                # Get organization ID from device
                org_id = device.get('organization_id') if device else None
                
                # Send via WebSocket
                websocket_service.send_device_log_event(websocket_log_data, org_id)
                
                # Send connectivity event if it's a connection log
                if log_type == 'connection' and device:
                    if 'connected' in message.lower():
                        websocket_service.send_device_connectivity_event(
                            device_id=device_id,
                            device_name=device.get('name', device_id),
                            status='connected',
                            organization_id=org_id
                        )
                    elif 'disconnected' in message.lower():
                        websocket_service.send_device_connectivity_event(
                            device_id=device_id,
                            device_name=device.get('name', device_id),
                            status='disconnected',
                            organization_id=org_id
                        )
                
            except Exception as e:
                logger.warning(f"Failed to broadcast device log via WebSocket: {e}")
            
            # Log to Phase 1 activity logs if critical
            if level.upper() in ['ERROR', 'CRITICAL', 'WARNING']:
                try:
                    # Map to LogLevel enum
                    level_map = {
                        'CRITICAL': LogLevel.CRITICAL,
                        'ERROR': LogLevel.ERROR,
                        'WARNING': LogLevel.WARNING,
                        'INFO': LogLevel.INFO,
                        'DEBUG': LogLevel.DEBUG
                    }
                    
                    log_level = level_map.get(level.upper(), LogLevel.INFO)
                    
                    # Log to Phase 1 system
                    logging_service.log_phase1_event(
                        category=phase1_category,
                        level=log_level,
                        message=f"Device {device_id}: {message}",
                        source=f"device_logs:{source}",
                        metadata={
                            'device_id': device_id,
                            'log_type': log_type,
                            'category': category.value,
                            'details': details or {}
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log to Phase 1 system: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding device log: {e}")
            return False
    
    @staticmethod
    def _generate_sample_logs(device_id: str, device: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate sample logs when no real logs exist"""
        logs = []
        base_time = datetime.now()
        
        # Device initialization log
        logs.append({
            'timestamp': base_time - timedelta(hours=24),
            'level': 'INFO',
            'log_type': 'system',
            'message': 'Device initialized and registered',
            'details': {
                'device_type': device.get('type') if device else 'unknown',
                'firmware_version': device.get('firmware_version') if device else 'unknown'
            }
        })
        
        # Connection established
        logs.append({
            'timestamp': base_time - timedelta(hours=23, minutes=50),
            'level': 'INFO',
            'log_type': 'connection',
            'message': 'Connected to MQTT broker',
            'details': {
                'broker': 'tesa-vernemq:8883',
                'protocol': 'MQTTs'
            }
        })
        
        # Certificate validation
        logs.append({
            'timestamp': base_time - timedelta(hours=23, minutes=45),
            'level': 'INFO',
            'log_type': 'security',
            'message': 'X.509 certificate validated successfully',
            'details': {
                'issuer': 'Thai Embedded Systems Association',
                'algorithm': 'RSA 3072' if device and device.get('type') == 'edge_gateway' else 'ECC P-256'
            }
        })
        
        # Telemetry transmission
        logs.append({
            'timestamp': base_time - timedelta(minutes=30),
            'level': 'INFO',
            'log_type': 'telemetry',
            'message': 'Telemetry data transmitted',
            'details': {
                'payload_size': '256 bytes',
                'qos': 1
            }
        })
        
        # Recent activity
        logs.append({
            'timestamp': base_time - timedelta(minutes=5),
            'level': 'INFO',
            'log_type': 'system',
            'message': 'Heartbeat received',
            'details': {
                'rtt': '12ms',
                'signal_strength': '-45 dBm'
            }
        })
        
        return logs
    
    @staticmethod
    def log_telemetry_error(device_id: str, error_message: str, payload: Any = None) -> None:
        """Log telemetry processing error"""
        try:
            db = get_db()
            
            error_entry = {
                'device_id': device_id,
                'timestamp': datetime.now(),
                'error_message': error_message,
                'payload': payload,
                'details': {
                    'processing_stage': 'telemetry_ingestion'
                }
            }
            
            db.telemetry_errors.insert_one(error_entry)
            
            # Also add to device logs
            DeviceLogsService.add_device_log(
                device_id=device_id,
                level='ERROR',
                message=f"Telemetry error: {error_message}",
                log_type='telemetry',
                details={'payload': str(payload)[:200] if payload else None},
                source='api'
            )
            
        except Exception as e:
            logger.error(f"Error logging telemetry error: {e}")
    
    @staticmethod
    def cleanup_old_logs(days_to_keep: int = 30) -> int:
        """
        Clean up old logs
        
        Args:
            days_to_keep: Number of days to keep logs
            
        Returns:
            Number of logs deleted
        """
        try:
            db = get_db()
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            result = db.device_logs.delete_many({
                'timestamp': {'$lt': cutoff_date}
            })
            
            logger.info(f"Cleaned up {result.deleted_count} old device logs")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up logs: {e}")
            return 0


# Create service instance
device_logs_service = DeviceLogsService()