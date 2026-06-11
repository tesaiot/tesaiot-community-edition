# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - WebSocket Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Version: v2025.06-beta
Module: WebSocket Service for Real-time Notifications
"""

import logging
import json
from typing import Dict, Set, Any
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)

class WebSocketService:
    """Service for managing WebSocket connections and real-time notifications"""
    
    def __init__(self):
        self.connections: Dict[str, Set[Any]] = {}  # user_id -> set of websocket connections
        self.connection_lock = Lock()
        
    def add_connection(self, user_id: str, websocket) -> None:
        """Add a WebSocket connection for a user"""
        with self.connection_lock:
            if user_id not in self.connections:
                self.connections[user_id] = set()
            self.connections[user_id].add(websocket)
            logger.info(f"Added WebSocket connection for user {user_id}")
    
    def remove_connection(self, user_id: str, websocket) -> None:
        """Remove a WebSocket connection for a user"""
        with self.connection_lock:
            if user_id in self.connections:
                self.connections[user_id].discard(websocket)
                if not self.connections[user_id]:
                    del self.connections[user_id]
            logger.info(f"Removed WebSocket connection for user {user_id}")
    
    def send_to_user(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to all connections for a specific user"""
        if user_id not in self.connections:
            return False
            
        message_json = json.dumps(message)
        connections_to_remove = set()
        
        with self.connection_lock:
            for websocket in self.connections[user_id].copy():
                try:
                    websocket.send(message_json)
                except Exception as e:
                    logger.warning(f"Failed to send message to {user_id}: {e}")
                    connections_to_remove.add(websocket)
            
            # Remove failed connections
            for websocket in connections_to_remove:
                self.connections[user_id].discard(websocket)
            
            if not self.connections[user_id]:
                del self.connections[user_id]
        
        return len(connections_to_remove) == 0
    
    def send_notification(self, notification: Dict[str, Any], recipient_ids: list = None) -> None:
        """Send a notification to specified users or all connected users"""
        message = {
            'type': 'notification',
            'data': notification,
            'timestamp': datetime.now().isoformat()
        }
        
        if recipient_ids:
            # Send to specific users
            for user_id in recipient_ids:
                self.send_to_user(user_id, message)
        else:
            # Send to all connected users
            with self.connection_lock:
                for user_id in list(self.connections.keys()):
                    self.send_to_user(user_id, message)
    
    def send_ai_ml_notification(self, notification_type: str, metadata: Dict[str, Any], recipient_ids: list = None) -> None:
        """Send AI/ML specific notification"""
        notification = {
            'id': f"ai_ml_{datetime.now().timestamp()}",
            'type': 'ai_ml',
            'category': 'AI/ML',
            'subtype': notification_type,
            'title': self._get_ai_ml_title(notification_type, metadata),
            'message': self._get_ai_ml_message(notification_type, metadata),
            'status': 'unread',
            'priority': metadata.get('priority', 'medium'),
            'created_at': datetime.now().isoformat(),
            'metadata': metadata,
            'actions': self._get_ai_ml_actions(notification_type, metadata)
        }
        
        self.send_notification(notification, recipient_ids)
    
    def send_provisioning_notification(self, notification_type: str, metadata: Dict[str, Any], recipient_ids: list = None) -> None:
        """Send provisioning specific notification"""
        notification = {
            'id': f"provisioning_{datetime.now().timestamp()}",
            'type': 'provisioning',
            'category': 'Device Provisioning',
            'subtype': notification_type,
            'title': self._get_provisioning_title(notification_type, metadata),
            'message': self._get_provisioning_message(notification_type, metadata),
            'status': 'unread',
            'priority': metadata.get('priority', 'medium'),
            'created_at': datetime.now().isoformat(),
            'metadata': metadata,
            'actions': self._get_provisioning_actions(notification_type, metadata)
        }
        
        self.send_notification(notification, recipient_ids)
    
    def send_provisioning_progress(self, session_id: str, progress_data: Dict[str, Any], recipient_ids: list = None) -> None:
        """Send real-time provisioning progress updates"""
        message = {
            'type': 'provisioning_progress',
            'session_id': session_id,
            'data': progress_data,
            'timestamp': datetime.now().isoformat()
        }
        
        if recipient_ids:
            for user_id in recipient_ids:
                self.send_to_user(user_id, message)
        else:
            with self.connection_lock:
                for user_id in list(self.connections.keys()):
                    self.send_to_user(user_id, message)
    
    def send_key_generation_status(self, operation_id: str, status_data: Dict[str, Any], recipient_ids: list = None) -> None:
        """Send key generation status updates"""
        message = {
            'type': 'key_generation_status',
            'operation_id': operation_id,
            'data': status_data,
            'timestamp': datetime.now().isoformat()
        }
        
        if recipient_ids:
            for user_id in recipient_ids:
                self.send_to_user(user_id, message)
        else:
            with self.connection_lock:
                for user_id in list(self.connections.keys()):
                    self.send_to_user(user_id, message)
    
    def send_device_discovery_event(self, device_data: Dict[str, Any], organization_id: str, recipient_ids: list = None) -> None:
        """Send zero-touch provisioning device discovery events"""
        message = {
            'type': 'device_discovery',
            'organization_id': organization_id,
            'data': device_data,
            'timestamp': datetime.now().isoformat()
        }
        
        if recipient_ids:
            for user_id in recipient_ids:
                self.send_to_user(user_id, message)
        else:
            # Send to all users in the organization
            with self.connection_lock:
                for user_id in list(self.connections.keys()):
                    self.send_to_user(user_id, message)
    
    def _get_ai_ml_title(self, notification_type: str, metadata: Dict[str, Any]) -> str:
        """Generate title for AI/ML notifications"""
        titles = {
            'model_training_complete': f"Model Training Complete: {metadata.get('model_name', 'Unknown')}",
            'anomaly_detected': f"Anomaly Detected: {metadata.get('device_name', 'Unknown Device')}",
            'predictive_maintenance': f"Maintenance Required: {metadata.get('device_name', 'Unknown Device')}",
            'performance_optimization': f"Optimization Opportunity: {metadata.get('system_name', 'System')}",
            'model_accuracy_update': f"Accuracy Update: {metadata.get('model_name', 'Unknown Model')}",
            'system_health_ai_alert': f"AI Health Alert: {metadata.get('component', 'System')}"
        }
        return titles.get(notification_type, f"AI/ML Event: {notification_type}")
    
    def _get_ai_ml_message(self, notification_type: str, metadata: Dict[str, Any]) -> str:
        """Generate message for AI/ML notifications"""
        messages = {
            'model_training_complete': f"Model '{metadata.get('model_name', 'Unknown')}' completed training with {metadata.get('accuracy', 'N/A')}% accuracy.",
            'anomaly_detected': f"Anomaly detected on {metadata.get('device_name', 'device')} with score {metadata.get('anomaly_score', 'N/A')}.",
            'predictive_maintenance': f"Maintenance predicted for {metadata.get('component', 'component')} with {metadata.get('confidence', 'N/A')}% confidence.",
            'performance_optimization': f"Potential {metadata.get('improvement_percentage', 'N/A')}% performance improvement identified.",
            'model_accuracy_update': f"Model accuracy updated to {metadata.get('current_accuracy', 'N/A')}%.",
            'system_health_ai_alert': f"AI detected {metadata.get('issue_description', 'system issue')} requiring attention."
        }
        return messages.get(notification_type, metadata.get('message', 'AI/ML event occurred'))
    
    def _get_ai_ml_actions(self, notification_type: str, metadata: Dict[str, Any]) -> list:
        """Generate actions for AI/ML notifications"""
        actions = {
            'model_training_complete': [
                {'label': 'View Model', 'action': 'view', 'variant': 'default'},
                {'label': 'Deploy Model', 'action': 'deploy', 'variant': 'default'}
            ],
            'anomaly_detected': [
                {'label': 'Investigate', 'action': 'view', 'variant': 'default'},
                {'label': 'Acknowledge', 'action': 'acknowledge', 'variant': 'outline'}
            ],
            'predictive_maintenance': [
                {'label': 'Schedule Maintenance', 'action': 'schedule', 'variant': 'default'},
                {'label': 'View Details', 'action': 'view', 'variant': 'outline'}
            ],
            'performance_optimization': [
                {'label': 'Apply Optimization', 'action': 'apply', 'variant': 'default'},
                {'label': 'Review Suggestions', 'action': 'view', 'variant': 'outline'}
            ]
        }
        return actions.get(notification_type, [
            {'label': 'View Details', 'action': 'view', 'variant': 'default'}
        ])
    
    def _get_provisioning_title(self, notification_type: str, metadata: Dict[str, Any]) -> str:
        """Generate title for provisioning notifications"""
        titles = {
            'bulk_import_started': f"Bulk Import Started: {metadata.get('device_count', 0)} devices",
            'bulk_import_progress': f"Bulk Import Progress: {metadata.get('progress', 0)}%",
            'bulk_import_completed': f"Bulk Import Completed: {metadata.get('successful', 0)}/{metadata.get('total', 0)} devices",
            'bulk_import_failed': f"Bulk Import Failed: {metadata.get('error_message', 'Unknown error')}",
            'device_provisioning_started': f"Device Provisioning Started: {metadata.get('device_id', 'Unknown')}",
            'device_provisioning_completed': f"Device Provisioned: {metadata.get('device_name', 'Unknown Device')}",
            'device_provisioning_failed': f"Provisioning Failed: {metadata.get('device_id', 'Unknown')}",
            'key_generation_started': f"Key Generation Started: {metadata.get('key_type', 'Unknown')}",
            'key_generation_completed': f"Key Generated: {metadata.get('key_type', 'Unknown')}",
            'key_generation_failed': f"Key Generation Failed: {metadata.get('error_message', 'Unknown error')}",
            'zero_touch_discovery': f"Device Discovered: {metadata.get('device_id', 'Unknown')}",
            'certificate_generated': f"Certificate Generated: {metadata.get('serial_number', 'Unknown')}",
            'certificate_distribution': f"Certificate Distributed: {metadata.get('device_id', 'Unknown')}",
            'provisioning_error': f"Provisioning Error: {metadata.get('error_message', 'Unknown error')}",
            'provisioning_alert': f"Provisioning Alert: {metadata.get('alert_message', 'Unknown alert')}"
        }
        return titles.get(notification_type, f"Provisioning Event: {notification_type}")
    
    def _get_provisioning_message(self, notification_type: str, metadata: Dict[str, Any]) -> str:
        """Generate message for provisioning notifications"""
        messages = {
            'bulk_import_started': f"Started bulk import of {metadata.get('device_count', 0)} devices using template '{metadata.get('template_name', 'Default')}'.",
            'bulk_import_progress': f"Processing device {metadata.get('current_device', 0)} of {metadata.get('total_devices', 0)}. {metadata.get('successful', 0)} successful, {metadata.get('failed', 0)} failed.",
            'bulk_import_completed': f"Bulk import completed successfully. {metadata.get('successful', 0)} devices provisioned, {metadata.get('failed', 0)} failed.",
            'bulk_import_failed': f"Bulk import failed: {metadata.get('error_message', 'Unknown error')}. {metadata.get('processed', 0)} devices processed.",
            'device_provisioning_started': f"Started provisioning device '{metadata.get('device_id', 'Unknown')}' with {metadata.get('auth_type', 'unknown')} authentication.",
            'device_provisioning_completed': f"Device '{metadata.get('device_name', 'Unknown')}' successfully provisioned with {metadata.get('auth_type', 'unknown')} authentication.",
            'device_provisioning_failed': f"Failed to provision device '{metadata.get('device_id', 'Unknown')}': {metadata.get('error_message', 'Unknown error')}.",
            'key_generation_started': f"Started generating {metadata.get('key_type', 'unknown')} key for device '{metadata.get('device_id', 'Unknown')}'.",
            'key_generation_completed': f"Successfully generated {metadata.get('key_type', 'unknown')} key for device '{metadata.get('device_id', 'Unknown')}'.",
            'key_generation_failed': f"Failed to generate {metadata.get('key_type', 'unknown')} key: {metadata.get('error_message', 'Unknown error')}.",
            'zero_touch_discovery': f"Discovered device '{metadata.get('device_id', 'Unknown')}' via zero-touch provisioning. Ready for enrollment.",
            'certificate_generated': f"Generated certificate with serial number {metadata.get('serial_number', 'Unknown')} for device '{metadata.get('device_id', 'Unknown')}'.",
            'certificate_distribution': f"Distributed certificate to device '{metadata.get('device_id', 'Unknown')}' successfully.",
            'provisioning_error': f"Provisioning error occurred: {metadata.get('error_message', 'Unknown error')}. Device: {metadata.get('device_id', 'Unknown')}.",
            'provisioning_alert': f"Provisioning alert: {metadata.get('alert_message', 'Unknown alert')}. Attention required."
        }
        return messages.get(notification_type, metadata.get('message', 'Provisioning event occurred'))
    
    def _get_provisioning_actions(self, notification_type: str, metadata: Dict[str, Any]) -> list:
        """Generate actions for provisioning notifications"""
        actions = {
            'bulk_import_started': [
                {'label': 'View Progress', 'action': 'view_progress', 'variant': 'default'},
                {'label': 'Cancel Import', 'action': 'cancel', 'variant': 'outline'}
            ],
            'bulk_import_progress': [
                {'label': 'View Details', 'action': 'view_details', 'variant': 'default'},
                {'label': 'Cancel Import', 'action': 'cancel', 'variant': 'outline'}
            ],
            'bulk_import_completed': [
                {'label': 'View Results', 'action': 'view_results', 'variant': 'default'},
                {'label': 'Download Report', 'action': 'download_report', 'variant': 'outline'}
            ],
            'bulk_import_failed': [
                {'label': 'View Error Details', 'action': 'view_errors', 'variant': 'default'},
                {'label': 'Retry Import', 'action': 'retry', 'variant': 'outline'}
            ],
            'device_provisioning_completed': [
                {'label': 'View Device', 'action': 'view_device', 'variant': 'default'},
                {'label': 'Test Connection', 'action': 'test_connection', 'variant': 'outline'}
            ],
            'device_provisioning_failed': [
                {'label': 'View Error', 'action': 'view_error', 'variant': 'default'},
                {'label': 'Retry Provisioning', 'action': 'retry', 'variant': 'outline'}
            ],
            'key_generation_completed': [
                {'label': 'View Key Details', 'action': 'view_key', 'variant': 'default'},
                {'label': 'Download Certificate', 'action': 'download_cert', 'variant': 'outline'}
            ],
            'key_generation_failed': [
                {'label': 'View Error', 'action': 'view_error', 'variant': 'default'},
                {'label': 'Retry Generation', 'action': 'retry', 'variant': 'outline'}
            ],
            'zero_touch_discovery': [
                {'label': 'Enroll Device', 'action': 'enroll', 'variant': 'default'},
                {'label': 'View Details', 'action': 'view_details', 'variant': 'outline'}
            ],
            'certificate_generated': [
                {'label': 'View Certificate', 'action': 'view_cert', 'variant': 'default'},
                {'label': 'Download Certificate', 'action': 'download_cert', 'variant': 'outline'}
            ],
            'provisioning_error': [
                {'label': 'View Error Details', 'action': 'view_error', 'variant': 'default'},
                {'label': 'Retry Operation', 'action': 'retry', 'variant': 'outline'}
            ]
        }
        return actions.get(notification_type, [
            {'label': 'View Details', 'action': 'view', 'variant': 'default'}
        ])
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        with self.connection_lock:
            return sum(len(connections) for connections in self.connections.values())
    
    def get_user_count(self) -> int:
        """Get number of users with active connections"""
        with self.connection_lock:
            return len(self.connections)
    
    def send_device_log_event(self, log_data: Dict[str, Any], organization_id: str = None) -> None:
        """Send device log event to connected users"""
        message = {
            'type': 'device:log:new',
            'data': log_data,
            'timestamp': datetime.now().isoformat()
        }
        
        if organization_id:
            # Send to users in specific organization
            # This would require tracking user organization associations
            self.send_notification({'message': message}, recipient_ids=None)
        else:
            # Send to all connected users
            with self.connection_lock:
                for user_id in list(self.connections.keys()):
                    self.send_to_user(user_id, message)
    
    def send_device_connectivity_event(self, device_id: str, device_name: str, status: str, organization_id: str = None) -> None:
        """Send device connectivity status change event"""
        message = {
            'type': 'device:connectivity',
            'data': {
                'device_id': device_id,
                'device_name': device_name,
                'status': status,  # 'connected' or 'disconnected'
                'timestamp': datetime.now().isoformat()
            },
            'timestamp': datetime.now().isoformat()
        }
        
        with self.connection_lock:
            for user_id in list(self.connections.keys()):
                self.send_to_user(user_id, message)
    
    def send_device_health_update(self, device_id: str, health_data: Dict[str, Any]) -> None:
        """Send device health score update"""
        message = {
            'type': 'device:health:update',
            'data': {
                'device_id': device_id,
                'health_score': health_data.get('overall_score', 0),
                'category_scores': health_data.get('category_scores', {}),
                'timestamp': datetime.now().isoformat()
            },
            'timestamp': datetime.now().isoformat()
        }
        
        with self.connection_lock:
            for user_id in list(self.connections.keys()):
                self.send_to_user(user_id, message)
    
    def send_telemetry_update(self, device_id: str, telemetry_data: Dict[str, Any], organization_id: str = None) -> None:
        """
        Send telemetry update to users who have access to the device.
        
        Args:
            device_id: The device identifier
            telemetry_data: The telemetry data
            organization_id: Optional organization ID for filtering recipients
        """
        message = {
            'type': 'telemetry_update',
            'data': {
                'device_id': device_id,
                'telemetry': telemetry_data,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # If organization_id is provided, only send to users in that organization
        if organization_id:
            # This would require tracking user organization in connections
            # For now, send to all connected users (they'll filter client-side)
            pass
        
        # Send to all connected users
        with self.connection_lock:
            for user_id in list(self.connections.keys()):
                self.send_to_user(user_id, message)
                
        logger.debug(f"Sent telemetry update for device {device_id} to {self.get_user_count()} users")

# Global WebSocket service instance
websocket_service = WebSocketService()