# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Certificate Monitoring Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Module: certificate_monitoring_service.py
Purpose: Monitor certificate health, expiry, and generate alerts
Version: v2025.06-beta-1
Build Date: 2025-06-14
Compliance: ETSI EN 303 645, ISO/IEC 27402
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..core.database import get_db, get_vault
from .notification_acl_service import create_notification_safe

logger = logging.getLogger(__name__)

class CertificateMonitoringService:
    """Service for monitoring certificate health and generating alerts"""
    
    # Alert thresholds (days before expiry)
    EXPIRY_CRITICAL = 1
    EXPIRY_URGENT = 7
    EXPIRY_WARNING = 30
    
    def __init__(self):
        self.db = get_db()
        self.vault_client = get_vault()
    
    def get_certificate_health_overview(self) -> Dict:
        """
        Get comprehensive certificate health overview for all certificates
        
        Returns:
            dict: Certificate health statistics and metrics
        """
        try:
            now = datetime.now()
            
            # Initialize counters
            stats = {
                'total_certificates': 0,
                'valid_certificates': 0,
                'expiring_warning': 0,  # 30 days
                'expiring_urgent': 0,   # 7 days
                'expiring_critical': 0, # 1 day
                'expired': 0,
                'revoked': 0,
                'by_algorithm': {},
                'by_organization': {},
                'health_score': 0.0,
                'last_updated': now.isoformat()
            }
            
            # Get all devices with certificates
            devices = self.db.devices.find({
                'certificate_serial': {'$exists': True, '$ne': None}
            })
            
            device_certs = []
            
            for device in devices:
                cert_info = self._get_certificate_status(device)
                if cert_info:
                    device_certs.append(cert_info)
                    stats['total_certificates'] += 1
                    
                    # Count by status
                    if cert_info['status'] == 'valid':
                        stats['valid_certificates'] += 1
                    elif cert_info['status'] == 'expired':
                        stats['expired'] += 1
                    elif cert_info['status'] == 'revoked':
                        stats['revoked'] += 1
                    
                    # Count by expiry urgency
                    days_until_expiry = cert_info.get('days_until_expiry')
                    if days_until_expiry is not None:
                        if days_until_expiry <= self.EXPIRY_CRITICAL:
                            stats['expiring_critical'] += 1
                        elif days_until_expiry <= self.EXPIRY_URGENT:
                            stats['expiring_urgent'] += 1
                        elif days_until_expiry <= self.EXPIRY_WARNING:
                            stats['expiring_warning'] += 1
                    
                    # Count by algorithm
                    algorithm = cert_info.get('algorithm', 'unknown')
                    stats['by_algorithm'][algorithm] = stats['by_algorithm'].get(algorithm, 0) + 1
                    
                    # Count by organization
                    org_name = cert_info.get('organization_name', 'Unknown')
                    stats['by_organization'][org_name] = stats['by_organization'].get(org_name, 0) + 1
            
            # Calculate health score (0-100)
            if stats['total_certificates'] > 0:
                health_factors = [
                    (stats['valid_certificates'] / stats['total_certificates']) * 40,  # 40% weight
                    ((stats['total_certificates'] - stats['expired']) / stats['total_certificates']) * 20,  # 20% weight
                    ((stats['total_certificates'] - stats['revoked']) / stats['total_certificates']) * 20,  # 20% weight
                    ((stats['total_certificates'] - stats['expiring_critical']) / stats['total_certificates']) * 10,  # 10% weight
                    ((stats['total_certificates'] - stats['expiring_urgent']) / stats['total_certificates']) * 10,  # 10% weight
                ]
                stats['health_score'] = round(sum(health_factors), 1)
            else:
                stats['health_score'] = 100.0  # No certificates = no problems
            
            # Add detailed certificate list
            # Sort by days_until_expiry, putting None values at the end
            stats['certificates'] = sorted(
                device_certs,
                key=lambda x: x.get('days_until_expiry') if x.get('days_until_expiry') is not None else float('inf')
            )[:50]  # Top 50 most urgent
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting certificate health overview: {e}")
            return {
                'error': str(e),
                'last_updated': datetime.now().isoformat()
            }
    
    def _get_certificate_status(self, device: Dict) -> Optional[Dict]:
        """Get certificate status for a single device"""
        try:
            cert_serial = device.get('certificate_serial')
            if not cert_serial:
                return None
            
            # Get certificate info from device record
            cert_info = device.get('certificate_info', {})
            
            # Extract expiry date. Accept the several shapes the issuer has
            # stored over time (expires_at / validTo / valid_until / expiry_date);
            # otherwise derive it from an issue date + validity window.
            expiry_date = None
            raw_expiry = (cert_info.get('expires_at') or cert_info.get('validTo')
                          or cert_info.get('valid_until') or cert_info.get('expiry_date'))
            if raw_expiry:
                try:
                    expiry_date = (raw_expiry if isinstance(raw_expiry, datetime)
                                   else datetime.fromisoformat(str(raw_expiry).replace('Z', '+00:00')))
                except (ValueError, TypeError):
                    expiry_date = None
            if expiry_date is None:
                issued = cert_info.get('issued_at') or device.get('created_at')
                days = cert_info.get('validity_days')
                if isinstance(cert_info.get('validity_period'), dict):
                    days = cert_info['validity_period'].get('days', days)
                if issued and days:
                    try:
                        if isinstance(issued, str):
                            issued = datetime.fromisoformat(issued.replace('Z', '+00:00'))
                        expiry_date = issued + timedelta(days=int(days))
                    except (ValueError, TypeError):
                        expiry_date = None
            # The comparison below uses a naive datetime.now(); drop any tz so the
            # subtraction never raises offset-naive/aware errors.
            if expiry_date is not None and expiry_date.tzinfo is not None:
                expiry_date = expiry_date.replace(tzinfo=None)

            # Calculate days until expiry
            days_until_expiry = None
            if expiry_date:
                delta = expiry_date - datetime.now()
                days_until_expiry = delta.days
            
            # Determine status
            status = 'unknown'
            urgency = 'normal'
            
            if device.get('certificate_status') == 'revoked':
                status = 'revoked'
                urgency = 'critical'
            elif days_until_expiry is not None:
                if days_until_expiry < 0:
                    status = 'expired'
                    urgency = 'critical'
                elif days_until_expiry <= self.EXPIRY_CRITICAL:
                    status = 'expiring_critical'
                    urgency = 'critical'
                elif days_until_expiry <= self.EXPIRY_URGENT:
                    status = 'expiring_urgent'
                    urgency = 'urgent'
                elif days_until_expiry <= self.EXPIRY_WARNING:
                    status = 'expiring_warning'
                    urgency = 'warning'
                else:
                    status = 'valid'
                    urgency = 'normal'
            
            # Get organization info
            org_id = device.get('organization_id')
            org_name = 'Unknown'
            if org_id:
                org = self.db.organizations.find_one({'_id': org_id})
                if org:
                    org_name = org.get('name', 'Unknown')
            
            return {
                'device_id': device.get('device_id'),
                'device_name': device.get('name'),
                'certificate_serial': cert_serial,
                'algorithm': cert_info.get('key_algorithm') or device.get('certificate_algorithm'),
                'status': status,
                'urgency': urgency,
                'expiry_date': expiry_date.isoformat() if expiry_date else None,
                'days_until_expiry': days_until_expiry,
                'organization_id': str(org_id) if org_id else None,
                'organization_name': org_name,
                'last_seen': device.get('last_seen'),
                'certificate_created': device.get('created_at')
            }
            
        except Exception as e:
            logger.error(f"Error getting certificate status for device {device.get('device_id')}: {e}")
            return None
    
    def check_expiring_certificates(self) -> List[Dict]:
        """
        Check for certificates that are expiring soon
        
        Returns:
            list: List of expiring certificates with details
        """
        try:
            expiring_certs = []
            
            # Get all devices with certificates
            devices = self.db.devices.find({
                'certificate_serial': {'$exists': True, '$ne': None}
            })
            
            for device in devices:
                cert_status = self._get_certificate_status(device)
                if cert_status and cert_status['urgency'] in ['warning', 'urgent', 'critical']:
                    expiring_certs.append(cert_status)
            
            # Sort by urgency
            expiring_certs.sort(key=lambda x: x.get('days_until_expiry', float('inf')))
            
            return expiring_certs
            
        except Exception as e:
            logger.error(f"Error checking expiring certificates: {e}")
            return []
    
    def generate_certificate_alerts(self) -> List[Dict]:
        """
        Generate alerts for certificates that need attention
        
        Returns:
            list: List of generated alerts
        """
        try:
            alerts = []
            expiring_certs = self.check_expiring_certificates()
            
            for cert in expiring_certs:
                alert = {
                    'type': 'certificate_expiry',
                    'severity': cert['urgency'],
                    'device_id': cert['device_id'],
                    'device_name': cert['device_name'],
                    'organization_id': cert['organization_id'],
                    'organization_name': cert['organization_name'],
                    'message': self._generate_alert_message(cert),
                    'details': cert,
                    'created_at': datetime.now().isoformat()
                }
                
                # Store alert in database
                alert_id = self.db.certificate_alerts.insert_one(alert).inserted_id
                alert['_id'] = str(alert_id)
                
                alerts.append(alert)
                
                # Send notification if critical
                if cert['urgency'] == 'critical':
                    self._send_critical_alert(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error generating certificate alerts: {e}")
            return []
    
    def _generate_alert_message(self, cert: Dict) -> str:
        """Generate human-readable alert message"""
        days = cert.get('days_until_expiry', 0)
        device_name = cert.get('device_name', 'Unknown Device')
        
        if cert['status'] == 'expired':
            return f"❌ Certificate for device '{device_name}' has EXPIRED"
        elif cert['status'] == 'revoked':
            return f"🚫 Certificate for device '{device_name}' has been REVOKED"
        elif days <= self.EXPIRY_CRITICAL:
            return f"🚨 Certificate for device '{device_name}' expires in {days} day(s)"
        elif days <= self.EXPIRY_URGENT:
            return f"⚠️ Certificate for device '{device_name}' expires in {days} days"
        else:
            return f"📅 Certificate for device '{device_name}' expires in {days} days"
    
    def _send_critical_alert(self, alert: Dict):
        """Send critical alert notification"""
        try:
            # This would integrate with your notification service
            # For now, just log it
            logger.warning(f"CRITICAL ALERT: {alert['message']}")
            
            organization_id = alert.get('organization_id')
            if organization_id:
                create_notification_safe({
                    'type': 'device',
                    'subtype': 'certificate_expiry',
                    'title': 'Critical certificate alert',
                    'message': alert.get('message', 'Certificate requires immediate attention'),
                    'severity': 'critical',
                    'priority': 'high',
                    'organization_id': str(organization_id),
                    'recipient_type': 'organization',
                    'recipient_id': str(organization_id),
                    'metadata': alert
                })
            
        except Exception as e:
            logger.error(f"Error sending critical alert: {e}")
    
    def get_certificate_renewal_candidates(self) -> List[Dict]:
        """
        Get list of certificates that should be renewed
        
        Returns:
            list: Certificates eligible for renewal
        """
        try:
            candidates = []
            
            # Get certificates expiring within renewal window (30 days)
            expiring_certs = self.check_expiring_certificates()
            
            for cert in expiring_certs:
                if cert.get('days_until_expiry', 0) <= self.EXPIRY_WARNING:
                    candidates.append({
                        'device_id': cert['device_id'],
                        'device_name': cert['device_name'],
                        'current_serial': cert['certificate_serial'],
                        'algorithm': cert['algorithm'],
                        'days_until_expiry': cert['days_until_expiry'],
                        'expiry_date': cert['expiry_date'],
                        'organization_id': cert['organization_id'],
                        'renewal_priority': self._calculate_renewal_priority(cert)
                    })
            
            # Sort by priority
            candidates.sort(key=lambda x: x['renewal_priority'], reverse=True)
            
            return candidates
            
        except Exception as e:
            logger.error(f"Error getting renewal candidates: {e}")
            return []
    
    def _calculate_renewal_priority(self, cert: Dict) -> int:
        """Calculate renewal priority score (higher = more urgent)"""
        days = cert.get('days_until_expiry', 0)
        
        if days <= 0:
            return 1000  # Expired - highest priority
        elif days <= self.EXPIRY_CRITICAL:
            return 900
        elif days <= self.EXPIRY_URGENT:
            return 700
        elif days <= self.EXPIRY_WARNING:
            return 500
        else:
            return 100
    
    def get_certificate_statistics_by_organization(self, org_id: str) -> Dict:
        """Get certificate statistics for a specific organization"""
        try:
            stats = {
                'organization_id': org_id,
                'total_devices': 0,
                'certificates_issued': 0,
                'valid_certificates': 0,
                'expiring_soon': 0,
                'expired': 0,
                'by_algorithm': {},
                'last_updated': datetime.now().isoformat()
            }
            
            # Get devices for organization
            devices = self.db.devices.find({'organization_id': org_id})
            
            for device in devices:
                stats['total_devices'] += 1
                
                if device.get('certificate_serial'):
                    stats['certificates_issued'] += 1
                    
                    cert_status = self._get_certificate_status(device)
                    if cert_status:
                        if cert_status['status'] == 'valid':
                            stats['valid_certificates'] += 1
                        elif cert_status['status'] == 'expired':
                            stats['expired'] += 1
                        elif cert_status['urgency'] in ['warning', 'urgent', 'critical']:
                            stats['expiring_soon'] += 1
                        
                        # Count by algorithm
                        algorithm = cert_status.get('algorithm', 'unknown')
                        stats['by_algorithm'][algorithm] = stats['by_algorithm'].get(algorithm, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting certificate statistics for org {org_id}: {e}")
            return {}


# Create singleton instance
certificate_monitoring_service = CertificateMonitoringService()
