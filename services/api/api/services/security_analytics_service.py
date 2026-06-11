# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Security Analytics Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio

from .base_service import BaseService


class SecurityAnalyticsService(BaseService):
    """
    Service for security analytics and threat detection.
    
    Provides:
    - Threat detection and analysis
    - Anomaly detection in user/device behavior
    - Security event tracking and correlation
    - Failed authentication monitoring
    - API abuse detection
    - Certificate expiry monitoring
    - Security metrics and reporting
    """
    
    # Threat severity levels
    SEVERITY_CRITICAL = 'critical'
    SEVERITY_HIGH = 'high'
    SEVERITY_MEDIUM = 'medium'
    SEVERITY_LOW = 'low'
    
    # Threat types
    THREAT_FAILED_AUTH = 'failed_authentication'
    THREAT_BRUTE_FORCE = 'brute_force_attempt'
    THREAT_API_ABUSE = 'api_abuse'
    THREAT_SUSPICIOUS_IP = 'suspicious_ip'
    THREAT_CERT_EXPIRY = 'certificate_expiry'
    THREAT_ANOMALY = 'behavioral_anomaly'
    THREAT_RATE_LIMIT = 'rate_limit_violation'
    
    async def validate_permissions(
        self, 
        user_role: str, 
        org_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: str = 'read'
    ) -> bool:
        """
        Validate user permissions for security analytics access.
        
        Only admins and platform admins can view security analytics.
        """
        if action != 'read':
            # Security analytics are read-only through this service
            return False
            
        return user_role in ['admin', 'super_admin', 'platform_admin']
    
    @BaseService.timing_decorator
    async def get_security_overview(
        self, 
        org_id: Optional[str] = None,
        timeframe: str = 'day'
    ) -> Dict[str, Any]:
        """
        Get comprehensive security overview.
        
        Args:
            org_id: Organization ID for filtering
            timeframe: Time period ('hour', 'day', 'week', 'month')
            
        Returns:
            Security overview with threats, anomalies, and metrics
        """
        cache_key = f"security:overview:{org_id or 'all'}:{timeframe}"
        
        async def compute():
            # Run all security checks in parallel
            results = await asyncio.gather(
                self.get_threat_summary(org_id, timeframe),
                self.get_anomaly_detection(org_id),
                self.get_failed_auth_analysis(org_id, timeframe),
                self.get_api_abuse_detection(org_id),
                self.get_certificate_status(org_id),
                self.get_security_events(org_id, limit=10),
                return_exceptions=True
            )
            
            # Handle results
            overview = {
                'threat_summary': results[0] if not isinstance(results[0], Exception) else {},
                'anomalies': results[1] if not isinstance(results[1], Exception) else [],
                'failed_auth': results[2] if not isinstance(results[2], Exception) else {},
                'api_abuse': results[3] if not isinstance(results[3], Exception) else {},
                'certificates': results[4] if not isinstance(results[4], Exception) else {},
                'recent_events': results[5] if not isinstance(results[5], Exception) else [],
                'generated_at': datetime.utcnow().isoformat(),
                'timeframe': timeframe
            }
            
            # Calculate overall security score
            overview['security_score'] = self._calculate_security_score(overview)
            
            return overview
        
        return await self.get_cached_or_compute(cache_key, compute, ttl=300)
    
    @BaseService.timing_decorator
    async def get_threat_summary(
        self, 
        org_id: Optional[str] = None,
        timeframe: str = 'day'
    ) -> Dict[str, Any]:
        """
        Get threat detection summary.
        
        Args:
            org_id: Organization ID for filtering
            timeframe: Time period for analysis
            
        Returns:
            Threat summary with counts by severity and type
        """
        hours = self._timeframe_to_hours(timeframe)
        since = datetime.utcnow() - timedelta(hours=hours)
        
        cache_key = f"threats:{org_id or 'all'}:{timeframe}"
        
        async def compute():
            if self.db is None:
                return self._get_default_threat_summary()
                
            try:
                # Build filter
                threat_filter = {'created_at': {'$gte': since}}
                if org_id:
                    threat_filter['organization_id'] = org_id
                
                # Get threats by severity
                severity_pipeline = [
                    {'$match': threat_filter},
                    {'$group': {
                        '_id': '$severity',
                        'count': {'$sum': 1}
                    }}
                ]
                
                severity_results = await self.db.security_events.aggregate(
                    severity_pipeline
                ).to_list(length=10)
                
                threats_by_severity = {
                    self.SEVERITY_CRITICAL: 0,
                    self.SEVERITY_HIGH: 0,
                    self.SEVERITY_MEDIUM: 0,
                    self.SEVERITY_LOW: 0
                }
                
                for result in severity_results:
                    if result['_id'] in threats_by_severity:
                        threats_by_severity[result['_id']] = result['count']
                
                # Get top threat types
                type_pipeline = [
                    {'$match': threat_filter},
                    {'$group': {
                        '_id': '$threat_type',
                        'count': {'$sum': 1}
                    }},
                    {'$sort': {'count': -1}},
                    {'$limit': 5}
                ]
                
                threat_types = await self.db.security_events.aggregate(
                    type_pipeline
                ).to_list(length=5)
                
                # Get threat trend
                trend = await self._calculate_threat_trend(threat_filter, hours)
                
                return {
                    'total_threats': sum(threats_by_severity.values()),
                    'critical_threats': threats_by_severity[self.SEVERITY_CRITICAL],
                    'high_threats': threats_by_severity[self.SEVERITY_HIGH],
                    'medium_threats': threats_by_severity[self.SEVERITY_MEDIUM],
                    'low_threats': threats_by_severity[self.SEVERITY_LOW],
                    'top_threat_types': [
                        {
                            'type': tt['_id'],
                            'count': tt['count'],
                            'percentage': (tt['count'] / sum(threats_by_severity.values()) * 100)
                            if sum(threats_by_severity.values()) > 0 else 0
                        }
                        for tt in threat_types
                    ],
                    'trend': trend,
                    'period': {
                        'start': since.isoformat(),
                        'end': datetime.utcnow().isoformat(),
                        'hours': hours
                    }
                }
                
            except Exception as e:
                self.logger.error(f"Error computing threat summary: {e}")
                return self._get_default_threat_summary()
        
        return await self.get_cached_or_compute(cache_key, compute, ttl=300)
    
    @BaseService.timing_decorator
    async def get_anomaly_detection(
        self, 
        org_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies in user and device behavior.
        
        Args:
            org_id: Organization ID for filtering
            
        Returns:
            List of detected anomalies
        """
        cache_key = f"anomalies:{org_id or 'all'}"
        
        async def compute():
            anomalies = []
            
            # Run various anomaly detection algorithms
            anomaly_checks = await asyncio.gather(
                self._detect_unusual_login_patterns(org_id),
                self._detect_unusual_device_activity(org_id),
                self._detect_api_usage_anomalies(org_id),
                self._detect_geographic_anomalies(org_id),
                return_exceptions=True
            )
            
            # Combine all anomalies
            for check_result in anomaly_checks:
                if isinstance(check_result, list):
                    anomalies.extend(check_result)
                elif isinstance(check_result, Exception):
                    self.logger.error(f"Anomaly detection error: {check_result}")
            
            # Sort by severity and timestamp
            anomalies.sort(key=lambda x: (
                self._severity_to_priority(x.get('severity', self.SEVERITY_LOW)),
                x.get('timestamp', datetime.utcnow())
            ), reverse=True)
            
            return anomalies[:50]  # Limit to top 50 anomalies
        
        return await self.get_cached_or_compute(cache_key, compute, ttl=60)
    
    @BaseService.timing_decorator
    async def get_failed_auth_analysis(
        self, 
        org_id: Optional[str] = None,
        timeframe: str = 'day'
    ) -> Dict[str, Any]:
        """
        Analyze failed authentication attempts.
        
        Args:
            org_id: Organization ID for filtering
            timeframe: Time period for analysis
            
        Returns:
            Failed authentication analysis
        """
        hours = self._timeframe_to_hours(timeframe)
        since = datetime.utcnow() - timedelta(hours=hours)
        
        cache_key = f"failed_auth:{org_id or 'all'}:{timeframe}"
        
        async def compute():
            if self.db is None:
                return self._get_default_failed_auth_analysis()
                
            try:
                # Build filter
                auth_filter = {
                    'action': 'login_failed',
                    'created_at': {'$gte': since}
                }
                if org_id:
                    auth_filter['organization_id'] = org_id
                
                # Get total failed attempts
                total_failed = await self.db.audit_logs.count_documents(auth_filter)
                
                # Get failed attempts by user
                user_pipeline = [
                    {'$match': auth_filter},
                    {'$group': {
                        '_id': '$user_email',
                        'count': {'$sum': 1},
                        'last_attempt': {'$max': '$created_at'}
                    }},
                    {'$sort': {'count': -1}},
                    {'$limit': 10}
                ]
                
                top_failed_users = await self.db.audit_logs.aggregate(
                    user_pipeline
                ).to_list(length=10)
                
                # Get failed attempts by IP
                ip_pipeline = [
                    {'$match': auth_filter},
                    {'$group': {
                        '_id': '$ip_address',
                        'count': {'$sum': 1},
                        'unique_users': {'$addToSet': '$user_email'}
                    }},
                    {'$sort': {'count': -1}},
                    {'$limit': 10}
                ]
                
                top_failed_ips = await self.db.audit_logs.aggregate(
                    ip_pipeline
                ).to_list(length=10)
                
                # Detect potential brute force attacks
                brute_force_candidates = []
                for ip_data in top_failed_ips:
                    if ip_data['count'] > 10:  # More than 10 failed attempts
                        brute_force_candidates.append({
                            'ip_address': ip_data['_id'],
                            'failed_attempts': ip_data['count'],
                            'targeted_users': len(ip_data['unique_users']),
                            'threat_level': self._calculate_brute_force_threat_level(
                                ip_data['count'],
                                len(ip_data['unique_users'])
                            )
                        })
                
                return {
                    'total_failed_attempts': total_failed,
                    'average_per_hour': self.sanitize_numeric_value(
                        total_failed / hours if hours > 0 else 0, 0
                    ),
                    'top_failed_users': [
                        {
                            'user_email': user['_id'],
                            'failed_attempts': user['count'],
                            'last_attempt': user['last_attempt'].isoformat()
                        }
                        for user in top_failed_users
                    ],
                    'top_failed_ips': [
                        {
                            'ip_address': ip['_id'],
                            'failed_attempts': ip['count'],
                            'unique_users_targeted': len(ip['unique_users'])
                        }
                        for ip in top_failed_ips
                    ],
                    'brute_force_indicators': brute_force_candidates,
                    'period': {
                        'start': since.isoformat(),
                        'end': datetime.utcnow().isoformat(),
                        'hours': hours
                    }
                }
                
            except Exception as e:
                self.logger.error(f"Error analyzing failed auth: {e}")
                return self._get_default_failed_auth_analysis()
        
        return await self.get_cached_or_compute(cache_key, compute, ttl=300)
    
    @BaseService.timing_decorator
    async def get_api_abuse_detection(
        self, 
        org_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect potential API abuse patterns.
        
        Args:
            org_id: Organization ID for filtering
            
        Returns:
            API abuse detection results
        """
        cache_key = f"api_abuse:{org_id or 'all'}"
        
        async def compute():
            if self.db is None:
                return self._get_default_api_abuse_detection()
                
            try:
                # Time window for analysis (last hour)
                since = datetime.utcnow() - timedelta(hours=1)
                
                # Build filter
                api_filter = {
                    'timestamp': {'$gte': since},
                    'type': 'api_request'
                }
                if org_id:
                    api_filter['organization_id'] = org_id
                
                # Get API usage by key
                key_pipeline = [
                    {'$match': api_filter},
                    {'$group': {
                        '_id': '$api_key',
                        'request_count': {'$sum': 1},
                        'unique_endpoints': {'$addToSet': '$endpoint'},
                        'error_count': {
                            '$sum': {'$cond': [{'$gte': ['$status_code', 400]}, 1, 0]}
                        }
                    }},
                    {'$sort': {'request_count': -1}},
                    {'$limit': 20}
                ]
                
                api_key_usage = await self.db.api_logs.aggregate(
                    key_pipeline
                ).to_list(length=20)
                
                # Detect abuse patterns
                abuse_indicators = []
                rate_limit_violations = []
                
                for key_data in api_key_usage:
                    requests_per_minute = key_data['request_count'] / 60
                    error_rate = (key_data['error_count'] / key_data['request_count'] * 100) \
                        if key_data['request_count'] > 0 else 0
                    
                    # Check for rate limit violations (assuming 100 req/min limit)
                    if requests_per_minute > 100:
                        rate_limit_violations.append({
                            'api_key': key_data['_id'][:12] + '...',  # Partial key for security
                            'requests_per_minute': self.sanitize_numeric_value(
                                requests_per_minute, 0
                            ),
                            'violation_severity': self._calculate_rate_limit_severity(
                                requests_per_minute
                            )
                        })
                    
                    # Check for suspicious patterns
                    if error_rate > 50 or len(key_data['unique_endpoints']) > 50:
                        abuse_indicators.append({
                            'api_key': key_data['_id'][:12] + '...',
                            'indicators': {
                                'high_error_rate': error_rate > 50,
                                'endpoint_scanning': len(key_data['unique_endpoints']) > 50,
                                'request_flooding': requests_per_minute > 200
                            },
                            'risk_score': self._calculate_api_risk_score(
                                error_rate,
                                len(key_data['unique_endpoints']),
                                requests_per_minute
                            )
                        })
                
                return {
                    'monitoring_period': {
                        'start': since.isoformat(),
                        'end': datetime.utcnow().isoformat()
                    },
                    'total_api_keys_active': len(api_key_usage),
                    'rate_limit_violations': rate_limit_violations,
                    'abuse_indicators': abuse_indicators,
                    'recommendations': self._generate_api_security_recommendations(
                        rate_limit_violations,
                        abuse_indicators
                    )
                }
                
            except Exception as e:
                self.logger.error(f"Error detecting API abuse: {e}")
                return self._get_default_api_abuse_detection()
        
        return await self.get_cached_or_compute(cache_key, compute, ttl=60)
    
    @BaseService.timing_decorator
    async def get_certificate_status(
        self, 
        org_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get certificate expiry and health status.
        
        Args:
            org_id: Organization ID for filtering
            
        Returns:
            Certificate status and expiry information
        """
        cache_key = f"certificates:{org_id or 'all'}"
        
        async def compute():
            if self.db is None:
                return self._get_default_certificate_status()
                
            try:
                # Build filter
                cert_filter = {}
                if org_id:
                    cert_filter['organization_id'] = org_id
                
                # Get all certificates
                certificates = await self.db.certificates.find(cert_filter).to_list(length=None)
                
                now = datetime.utcnow()
                expiring_soon = []
                expired = []
                healthy = []
                
                for cert in certificates:
                    expiry_date = cert.get('expiry_date')
                    if not expiry_date:
                        continue
                        
                    days_until_expiry = (expiry_date - now).days
                    
                    cert_info = {
                        'name': cert.get('name', 'Unknown'),
                        'type': cert.get('type', 'Unknown'),
                        'expiry_date': expiry_date.isoformat(),
                        'days_until_expiry': days_until_expiry
                    }
                    
                    if days_until_expiry < 0:
                        expired.append(cert_info)
                    elif days_until_expiry < 30:
                        expiring_soon.append(cert_info)
                    else:
                        healthy.append(cert_info)
                
                # Sort by expiry date
                expiring_soon.sort(key=lambda x: x['days_until_expiry'])
                
                return {
                    'total_certificates': len(certificates),
                    'healthy_certificates': len(healthy),
                    'expiring_soon': expiring_soon,
                    'expired': expired,
                    'certificate_health_score': self._calculate_cert_health_score(
                        len(healthy),
                        len(expiring_soon),
                        len(expired)
                    ),
                    'next_expiry': expiring_soon[0] if expiring_soon else None,
                    'recommendations': self._generate_cert_recommendations(
                        expiring_soon,
                        expired
                    )
                }
                
            except Exception as e:
                self.logger.error(f"Error checking certificate status: {e}")
                return self._get_default_certificate_status()
        
        return await self.get_cached_or_compute(cache_key, compute, ttl=3600)
    
    @BaseService.timing_decorator
    async def get_security_events(
        self, 
        org_id: Optional[str] = None,
        limit: int = 20,
        severity_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent security events.
        
        Args:
            org_id: Organization ID for filtering
            limit: Maximum number of events to return
            severity_filter: Filter by severity level
            
        Returns:
            List of recent security events
        """
        cache_key = f"events:{org_id or 'all'}:{severity_filter or 'all'}:{limit}"
        
        async def compute():
            if self.db is None:
                return []
                
            try:
                # Build filter
                event_filter = {}
                if org_id:
                    event_filter['organization_id'] = org_id
                if severity_filter:
                    event_filter['severity'] = severity_filter
                
                # Get recent events
                events = await self.db.security_events.find(
                    event_filter
                ).sort('created_at', -1).limit(limit).to_list(length=limit)
                
                # Format events
                formatted_events = []
                for event in events:
                    formatted_events.append({
                        'id': str(event['_id']),
                        'timestamp': event.get('created_at', datetime.utcnow()).isoformat(),
                        'severity': event.get('severity', self.SEVERITY_LOW),
                        'threat_type': event.get('threat_type', 'unknown'),
                        'description': event.get('description', 'No description'),
                        'source': event.get('source', {}),
                        'affected_resources': event.get('affected_resources', []),
                        'status': event.get('status', 'new'),
                        'tags': event.get('tags', [])
                    })
                
                return formatted_events
                
            except Exception as e:
                self.logger.error(f"Error fetching security events: {e}")
                return []
        
        return await self.get_cached_or_compute(cache_key, compute, ttl=60)
    
    # Helper methods for anomaly detection
    
    async def _detect_unusual_login_patterns(
        self, 
        org_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Detect unusual login patterns."""
        anomalies = []
        
        try:
            # Check for excessive login attempts
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            login_filter = {
                'action': {'$in': ['login', 'login_failed']},
                'created_at': {'$gte': hour_ago}
            }
            if org_id:
                login_filter['organization_id'] = org_id
            
            # Group by user
            user_logins = await self.db.audit_logs.aggregate([
                {'$match': login_filter},
                {'$group': {
                    '_id': '$user_email',
                    'total_attempts': {'$sum': 1},
                    'failed_attempts': {
                        '$sum': {'$cond': [{'$eq': ['$action', 'login_failed']}, 1, 0]}
                    },
                    'unique_ips': {'$addToSet': '$ip_address'},
                    'last_attempt': {'$max': '$created_at'}
                }}
            ]).to_list(length=None)
            
            for user_data in user_logins:
                # Check for excessive attempts
                if user_data['total_attempts'] > 20:
                    anomalies.append({
                        'type': self.THREAT_ANOMALY,
                        'subtype': 'excessive_login_attempts',
                        'severity': self.SEVERITY_MEDIUM,
                        'user_email': user_data['_id'],
                        'details': f"{user_data['total_attempts']} login attempts in the last hour",
                        'metadata': {
                            'failed_attempts': user_data['failed_attempts'],
                            'unique_ips': len(user_data['unique_ips'])
                        },
                        'timestamp': user_data['last_attempt']
                    })
                
                # Check for multiple IPs
                if len(user_data['unique_ips']) > 5:
                    anomalies.append({
                        'type': self.THREAT_ANOMALY,
                        'subtype': 'multiple_login_locations',
                        'severity': self.SEVERITY_HIGH,
                        'user_email': user_data['_id'],
                        'details': f"Login attempts from {len(user_data['unique_ips'])} different IPs",
                        'metadata': {
                            'ip_addresses': list(user_data['unique_ips'])[:10]
                        },
                        'timestamp': user_data['last_attempt']
                    })
            
        except Exception as e:
            self.logger.error(f"Error detecting login anomalies: {e}")
        
        return anomalies
    
    async def _detect_unusual_device_activity(
        self, 
        org_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Detect unusual device activity patterns."""
        anomalies = []
        
        try:
            # Check for devices with unusual telemetry patterns
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            # Get device telemetry stats
            telemetry_filter = {'timestamp': {'$gte': hour_ago}}
            
            device_stats = await self.db.telemetry.aggregate([
                {'$match': telemetry_filter},
                {'$group': {
                    '_id': '$device_id',
                    'message_count': {'$sum': 1},
                    'unique_types': {'$addToSet': '$type'},
                    'avg_interval': {'$avg': {
                        '$subtract': ['$timestamp', '$previous_timestamp']
                    }}
                }}
            ]).to_list(length=None)
            
            for device_data in device_stats:
                # Check for message flooding
                messages_per_minute = device_data['message_count'] / 60
                if messages_per_minute > 10:  # More than 10 messages per minute
                    anomalies.append({
                        'type': self.THREAT_ANOMALY,
                        'subtype': 'device_message_flooding',
                        'severity': self.SEVERITY_MEDIUM,
                        'device_id': str(device_data['_id']),
                        'details': f"Device sending {messages_per_minute:.1f} messages per minute",
                        'metadata': {
                            'message_count': device_data['message_count'],
                            'message_types': list(device_data['unique_types'])
                        },
                        'timestamp': datetime.utcnow()
                    })
            
        except Exception as e:
            self.logger.error(f"Error detecting device anomalies: {e}")
        
        return anomalies
    
    async def _detect_api_usage_anomalies(
        self, 
        org_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in API usage patterns."""
        anomalies = []
        
        try:
            # Check for unusual API usage patterns
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            api_filter = {
                'timestamp': {'$gte': hour_ago},
                'type': 'api_request'
            }
            if org_id:
                api_filter['organization_id'] = org_id
            
            # Analyze API patterns
            api_patterns = await self.db.api_logs.aggregate([
                {'$match': api_filter},
                {'$group': {
                    '_id': {
                        'api_key': '$api_key',
                        'endpoint': '$endpoint'
                    },
                    'request_count': {'$sum': 1},
                    'error_count': {
                        '$sum': {'$cond': [{'$gte': ['$status_code', 400]}, 1, 0]}
                    },
                    'unique_ips': {'$addToSet': '$ip_address'}
                }},
                {'$match': {
                    '$or': [
                        {'request_count': {'$gt': 1000}},
                        {'error_count': {'$gt': 100}}
                    ]
                }}
            ]).to_list(length=50)
            
            for pattern in api_patterns:
                if pattern['request_count'] > 1000:
                    anomalies.append({
                        'type': self.THREAT_API_ABUSE,
                        'subtype': 'excessive_api_calls',
                        'severity': self.SEVERITY_HIGH,
                        'api_key': pattern['_id']['api_key'][:12] + '...',
                        'details': f"{pattern['request_count']} calls to {pattern['_id']['endpoint']} in last hour",
                        'metadata': {
                            'endpoint': pattern['_id']['endpoint'],
                            'unique_ips': len(pattern['unique_ips'])
                        },
                        'timestamp': datetime.utcnow()
                    })
            
        except Exception as e:
            self.logger.error(f"Error detecting API anomalies: {e}")
        
        return anomalies
    
    async def _detect_geographic_anomalies(
        self, 
        org_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Detect geographic anomalies in access patterns."""
        anomalies = []
        
        # This would integrate with IP geolocation service
        # For now, returning empty list
        return anomalies
    
    # Helper methods for calculations
    
    def _timeframe_to_hours(self, timeframe: str) -> int:
        """Convert timeframe string to hours."""
        timeframe_map = {
            'hour': 1,
            'day': 24,
            'week': 168,
            'month': 720
        }
        return timeframe_map.get(timeframe, 24)
    
    def _severity_to_priority(self, severity: str) -> int:
        """Convert severity to numeric priority."""
        priority_map = {
            self.SEVERITY_CRITICAL: 4,
            self.SEVERITY_HIGH: 3,
            self.SEVERITY_MEDIUM: 2,
            self.SEVERITY_LOW: 1
        }
        return priority_map.get(severity, 0)
    
    def _calculate_security_score(self, overview: Dict[str, Any]) -> float:
        """Calculate overall security score (0-100)."""
        score = 100.0
        
        # Deduct points for threats
        threat_summary = overview.get('threat_summary', {})
        score -= threat_summary.get('critical_threats', 0) * 10
        score -= threat_summary.get('high_threats', 0) * 5
        score -= threat_summary.get('medium_threats', 0) * 2
        score -= threat_summary.get('low_threats', 0) * 0.5
        
        # Deduct for anomalies
        anomalies = overview.get('anomalies', [])
        score -= len(anomalies) * 2
        
        # Deduct for failed auth
        failed_auth = overview.get('failed_auth', {})
        if failed_auth.get('total_failed_attempts', 0) > 100:
            score -= 10
        
        # Ensure score is between 0 and 100
        return max(0, min(100, score))
    
    def _calculate_brute_force_threat_level(
        self, 
        failed_attempts: int, 
        targeted_users: int
    ) -> str:
        """Calculate threat level for potential brute force attack."""
        if failed_attempts > 100 or targeted_users > 10:
            return self.SEVERITY_CRITICAL
        elif failed_attempts > 50 or targeted_users > 5:
            return self.SEVERITY_HIGH
        elif failed_attempts > 20:
            return self.SEVERITY_MEDIUM
        else:
            return self.SEVERITY_LOW
    
    def _calculate_rate_limit_severity(self, requests_per_minute: float) -> str:
        """Calculate severity of rate limit violation."""
        if requests_per_minute > 1000:
            return self.SEVERITY_CRITICAL
        elif requests_per_minute > 500:
            return self.SEVERITY_HIGH
        elif requests_per_minute > 200:
            return self.SEVERITY_MEDIUM
        else:
            return self.SEVERITY_LOW
    
    def _calculate_api_risk_score(
        self, 
        error_rate: float, 
        unique_endpoints: int,
        requests_per_minute: float
    ) -> float:
        """Calculate API abuse risk score (0-100)."""
        score = 0.0
        
        # Factor in error rate
        if error_rate > 80:
            score += 40
        elif error_rate > 50:
            score += 25
        elif error_rate > 20:
            score += 10
        
        # Factor in endpoint scanning
        if unique_endpoints > 100:
            score += 30
        elif unique_endpoints > 50:
            score += 20
        elif unique_endpoints > 20:
            score += 10
        
        # Factor in request rate
        if requests_per_minute > 500:
            score += 30
        elif requests_per_minute > 200:
            score += 20
        elif requests_per_minute > 100:
            score += 10
        
        return min(100, score)
    
    def _calculate_cert_health_score(
        self, 
        healthy: int, 
        expiring: int, 
        expired: int
    ) -> float:
        """Calculate certificate health score (0-100)."""
        total = healthy + expiring + expired
        if total == 0:
            return 100.0
        
        score = (healthy / total) * 100
        score -= (expiring / total) * 20
        score -= (expired / total) * 50
        
        return max(0, score)
    
    async def _calculate_threat_trend(
        self, 
        threat_filter: Dict[str, Any], 
        hours: int
    ) -> Dict[str, Any]:
        """Calculate threat trend over time."""
        try:
            # Get current period count
            current_count = await self.db.security_events.count_documents(threat_filter)
            
            # Get previous period count
            previous_start = threat_filter['created_at']['$gte'] - timedelta(hours=hours)
            previous_filter = {
                **threat_filter,
                'created_at': {
                    '$gte': previous_start,
                    '$lt': threat_filter['created_at']['$gte']
                }
            }
            previous_count = await self.db.security_events.count_documents(previous_filter)
            
            # Calculate trend
            if previous_count == 0:
                trend_percentage = 100 if current_count > 0 else 0
            else:
                trend_percentage = ((current_count - previous_count) / previous_count) * 100
            
            return {
                'current_period': current_count,
                'previous_period': previous_count,
                'trend_percentage': self.sanitize_numeric_value(trend_percentage, 0),
                'trend_direction': 'increasing' if trend_percentage > 0 else 'decreasing'
            }
            
        except Exception:
            return {
                'current_period': 0,
                'previous_period': 0,
                'trend_percentage': 0,
                'trend_direction': 'stable'
            }
    
    def _generate_api_security_recommendations(
        self,
        rate_violations: List[Dict[str, Any]],
        abuse_indicators: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate API security recommendations."""
        recommendations = []
        
        if rate_violations:
            recommendations.append(
                "Consider implementing stricter rate limiting or upgrading API plans for frequent violators"
            )
        
        if abuse_indicators:
            recommendations.append(
                "Review and potentially revoke API keys showing abuse patterns"
            )
        
        if len(abuse_indicators) > 5:
            recommendations.append(
                "Implement automated API abuse detection and blocking mechanisms"
            )
        
        return recommendations
    
    def _generate_cert_recommendations(
        self,
        expiring: List[Dict[str, Any]],
        expired: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate certificate management recommendations."""
        recommendations = []
        
        if expired:
            recommendations.append(
                f"URGENT: {len(expired)} certificate(s) have expired and need immediate renewal"
            )
        
        if expiring:
            recommendations.append(
                f"Plan renewal for {len(expiring)} certificate(s) expiring within 30 days"
            )
        
        if len(expiring) > 3:
            recommendations.append(
                "Consider implementing automated certificate renewal to prevent expiry"
            )
        
        return recommendations
    
    # Default response methods
    
    def _get_default_threat_summary(self) -> Dict[str, Any]:
        """Get default threat summary when DB is unavailable."""
        return {
            'total_threats': 0,
            'critical_threats': 0,
            'high_threats': 0,
            'medium_threats': 0,
            'low_threats': 0,
            'top_threat_types': [],
            'trend': {
                'current_period': 0,
                'previous_period': 0,
                'trend_percentage': 0,
                'trend_direction': 'stable'
            }
        }
    
    def _get_default_failed_auth_analysis(self) -> Dict[str, Any]:
        """Get default failed auth analysis when DB is unavailable."""
        return {
            'total_failed_attempts': 0,
            'average_per_hour': 0,
            'top_failed_users': [],
            'top_failed_ips': [],
            'brute_force_indicators': []
        }
    
    def _get_default_api_abuse_detection(self) -> Dict[str, Any]:
        """Get default API abuse detection when DB is unavailable."""
        return {
            'total_api_keys_active': 0,
            'rate_limit_violations': [],
            'abuse_indicators': [],
            'recommendations': []
        }
    
    def _get_default_certificate_status(self) -> Dict[str, Any]:
        """Get default certificate status when DB is unavailable."""
        return {
            'total_certificates': 0,
            'healthy_certificates': 0,
            'expiring_soon': [],
            'expired': [],
            'certificate_health_score': 100.0,
            'next_expiry': None,
            'recommendations': []
        }