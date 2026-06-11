# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Security models for the Device Management module

This module defines security-related models for device authentication,
access control, security policies, and threat detection.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum
import secrets
import hashlib


class AuthenticationType(Enum):
    """Device authentication types"""
    API_KEY = "api_key"
    CERTIFICATE = "certificate"
    OAUTH2 = "oauth2"
    MQTT_USERNAME_PASSWORD = "mqtt_username_password"
    JWT = "jwt"
    MUTUAL_TLS = "mutual_tls"
    # Enhanced MFA authentication types
    MFA_TOTP = "mfa_totp"
    MFA_HARDWARE_TOKEN = "mfa_hardware_token"
    MFA_BIOMETRIC = "mfa_biometric"
    MFA_DEVICE_ATTESTATION = "mfa_device_attestation"
    # Quantum-resistant authentication
    POST_QUANTUM_CERTIFICATE = "post_quantum_certificate"
    ZERO_TRUST_DEVICE_ID = "zero_trust_device_id"


class PermissionScope(Enum):
    """Permission scopes for devices"""
    TELEMETRY_WRITE = "telemetry:write"
    TELEMETRY_READ = "telemetry:read"
    DEVICE_READ = "device:read"
    DEVICE_UPDATE = "device:update"
    COMMAND_EXECUTE = "command:execute"
    CONFIGURATION_READ = "configuration:read"
    CONFIGURATION_UPDATE = "configuration:update"
    FIRMWARE_DOWNLOAD = "firmware:download"
    CERTIFICATE_RENEW = "certificate:renew"
    # Enhanced security permissions
    SECURITY_AUDIT = "security:audit"
    COMPLIANCE_READ = "compliance:read"
    THREAT_DETECTION = "threat:detection"
    INCIDENT_RESPONSE = "incident:response"
    KEY_MANAGEMENT = "key:management"
    ENCRYPTION_VALIDATE = "encryption:validate"
    # Administrative permissions
    ADMIN_SECURITY_POLICY = "admin:security_policy"
    ADMIN_ACCESS_CONTROL = "admin:access_control"
    ADMIN_THREAT_RULES = "admin:threat_rules"


class ThreatLevel(Enum):
    """Threat level classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """Types of security events"""
    AUTHENTICATION_SUCCESS = "auth_success"
    AUTHENTICATION_FAILURE = "auth_failure"
    AUTHORIZATION_FAILURE = "authz_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_CERTIFICATE = "invalid_certificate"
    CERTIFICATE_EXPIRED = "certificate_expired"
    ANOMALY_DETECTED = "anomaly_detected"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    API_KEY_COMPROMISED = "api_key_compromised"
    # Enhanced threat detection events
    MFA_CHALLENGE_FAILED = "mfa_challenge_failed"
    DEVICE_FINGERPRINT_MISMATCH = "device_fingerprint_mismatch"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"
    ENCRYPTION_WEAKNESS_DETECTED = "encryption_weakness_detected"
    COMPLIANCE_VIOLATION = "compliance_violation"
    CERTIFICATE_ROTATION_FAILED = "certificate_rotation_failed"
    QUANTUM_ATTACK_DETECTED = "quantum_attack_detected"
    ZERO_TRUST_POLICY_VIOLATION = "zero_trust_policy_violation"
    INCIDENT_CONTAINMENT_TRIGGERED = "incident_containment_triggered"
    AUTOMATED_RESPONSE_EXECUTED = "automated_response_executed"
    # Real-time monitoring events
    THREAT_INTELLIGENCE_MATCH = "threat_intelligence_match"
    GEOLOCATION_ANOMALY = "geolocation_anomaly"
    TIME_BASED_ACCESS_VIOLATION = "time_based_access_violation"
    DATA_EXFILTRATION_ATTEMPT = "data_exfiltration_attempt"


@dataclass
class DeviceApiKey:
    """Device API key model"""
    key_id: str
    device_id: str
    org_id: str
    name: str
    key_hash: str  # Hashed API key
    key_prefix: str  # First 8 chars for identification
    scopes: List[PermissionScope] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool = True
    usage_count: int = 0
    rate_limit: int = 1000  # Requests per hour
    allowed_ips: List[str] = field(default_factory=list)  # IP whitelist
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @staticmethod
    def generate_api_key() -> tuple[str, str]:
        """Generate a new API key and its hash"""
        # Generate a secure random API key
        api_key = f"tesa_{secrets.token_urlsafe(32)}"
        # Hash the key for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return api_key, key_hash
    
    def is_expired(self) -> bool:
        """Check if the API key has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def has_scope(self, scope: PermissionScope) -> bool:
        """Check if the API key has a specific scope"""
        return scope in self.scopes


@dataclass
class DeviceOAuthToken:
    """OAuth2 token for device authentication"""
    token_id: str
    device_id: str
    org_id: str
    access_token_hash: str
    refresh_token_hash: Optional[str] = None
    token_type: str = "Bearer"
    scopes: List[PermissionScope] = field(default_factory=list)
    expires_in: int = 3600  # Seconds
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(seconds=3600))
    client_id: Optional[str] = None
    is_revoked: bool = False
    revoked_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None


@dataclass
class DeviceCertificateAuth:
    """Certificate-based authentication details"""
    auth_id: str
    device_id: str
    org_id: str
    certificate_id: str
    certificate_fingerprint: str
    certificate_serial: str
    subject_dn: str
    issuer_dn: str
    valid_from: datetime
    valid_until: datetime
    is_revoked: bool = False
    revocation_reason: Optional[str] = None
    allowed_sans: List[str] = field(default_factory=list)  # Subject Alternative Names
    last_auth_at: Optional[datetime] = None
    auth_count: int = 0
    
    def is_valid(self) -> bool:
        """Check if the certificate is currently valid"""
        now = datetime.utcnow()
        return (not self.is_revoked and 
                self.valid_from <= now <= self.valid_until)


@dataclass
class DeviceRole:
    """Role-based access control for devices"""
    role_id: str
    org_id: str
    name: str
    description: Optional[str] = None
    permissions: List[PermissionScope] = field(default_factory=list)
    device_ids: List[str] = field(default_factory=list)
    is_system: bool = False  # System-defined role
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


@dataclass
class AccessControlPolicy:
    """Access control policy for devices"""
    policy_id: str
    org_id: str
    name: str
    resource_type: str  # e.g., "telemetry", "configuration", "command"
    resource_pattern: str  # e.g., "/telemetry/*", "/device/{device_id}/config"
    description: Optional[str] = None
    allowed_actions: List[str] = field(default_factory=list)
    denied_actions: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)  # e.g., time-based, IP-based
    device_ids: List[str] = field(default_factory=list)  # Specific devices
    device_groups: List[str] = field(default_factory=list)  # Device groups
    roles: List[str] = field(default_factory=list)  # Device roles
    priority: int = 0  # Higher priority policies override lower ones
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


@dataclass
class SecurityPolicy:
    """Security policy configuration"""
    policy_id: str
    org_id: str
    name: str
    description: Optional[str] = None
    # Authentication settings
    allowed_auth_types: List[AuthenticationType] = field(default_factory=list)
    require_mutual_tls: bool = False
    require_secure_transport: bool = True
    # Session settings
    max_session_duration: int = 86400  # Seconds
    idle_timeout: int = 3600  # Seconds
    max_concurrent_sessions: int = 1
    # Password/Key policy (for MQTT username/password)
    min_password_length: int = 12
    require_password_complexity: bool = True
    password_expiry_days: int = 90
    # API key policy
    api_key_expiry_days: int = 365
    api_key_rotation_days: int = 90
    # Certificate policy
    min_certificate_key_size: int = 2048
    allowed_certificate_algorithms: List[str] = field(default_factory=lambda: ["RSA", "EC"])
    certificate_expiry_warning_days: int = 30
    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    burst_limit: int = 100
    # Security features
    enable_anomaly_detection: bool = True
    enable_threat_detection: bool = True
    enable_audit_logging: bool = True
    # IP restrictions
    allowed_ip_ranges: List[str] = field(default_factory=list)
    blocked_ip_ranges: List[str] = field(default_factory=list)
    # Compliance
    compliance_standards: List[str] = field(default_factory=list)  # e.g., ["ISO27001", "NIST"]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


@dataclass
class RateLimitRule:
    """Rate limiting rule for devices"""
    rule_id: str
    org_id: str
    name: str
    endpoint_pattern: str  # e.g., "/telemetry/*", "/api/v1/devices/*" - Required field moved before optional
    description: Optional[str] = None
    device_id: Optional[str] = None  # Specific device or None for all
    device_group_id: Optional[str] = None
    method: Optional[str] = None  # HTTP method or None for all
    limit_per_minute: int = 60
    limit_per_hour: int = 1000
    burst_size: int = 10
    penalty_duration: int = 300  # Seconds to block after limit exceeded
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ThreatDetectionRule:
    """Rule for detecting security threats"""
    rule_id: str
    org_id: str
    name: str
    rule_type: str  # e.g., "pattern", "anomaly", "threshold" - Required field moved before optional
    description: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    threat_level: ThreatLevel = ThreatLevel.MEDIUM
    actions: List[str] = field(default_factory=list)  # e.g., ["alert", "block", "log"]
    cooldown_period: int = 300  # Seconds before rule can trigger again
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0


@dataclass
class SecurityEvent:
    """Security event for audit and monitoring"""
    event_id: str
    org_id: str
    event_type: SecurityEventType  # Required field moved before optional
    device_id: Optional[str] = None
    threat_level: ThreatLevel = ThreatLevel.LOW
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    rule_id: Optional[str] = None  # Threat detection rule that triggered
    action_taken: Optional[str] = None  # e.g., "blocked", "alerted", "logged"
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class DeviceSecurityProfile:
    """Security profile for a device"""
    device_id: str
    org_id: str
    # Authentication
    auth_type: AuthenticationType
    auth_credentials_id: Optional[str] = None  # API key ID, certificate ID, etc.
    last_auth_success: Optional[datetime] = None
    last_auth_failure: Optional[datetime] = None
    failed_auth_count: int = 0
    # Access control
    assigned_roles: List[str] = field(default_factory=list)
    effective_permissions: Set[PermissionScope] = field(default_factory=set)
    # Security metrics
    risk_score: float = 0.0  # 0-100
    anomaly_score: float = 0.0  # 0-100
    last_risk_assessment: Optional[datetime] = None
    # Rate limiting
    current_rate_limit: Optional[RateLimitRule] = None
    rate_limit_violations: int = 0
    last_rate_limit_violation: Optional[datetime] = None
    # Security events
    recent_security_events: List[str] = field(default_factory=list)  # Event IDs
    active_threats: List[str] = field(default_factory=list)  # Threat IDs
    # Compliance
    compliance_status: Dict[str, bool] = field(default_factory=dict)
    last_compliance_check: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SecurityAuditLog:
    """Security audit log entry"""
    log_id: str
    org_id: str
    actor_type: str  # "device", "user", "system"
    action: str  # e.g., "auth.success", "permission.granted", "policy.updated"
    resource_type: str  # e.g., "device", "api_key", "certificate"
    result: str  # "success", "failure", "error"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    actor_id: Optional[str] = None
    resource_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None  # For tracking related events


# Enhanced Security Models for 75% Rollout


class MfaMethodType(Enum):
    """Multi-factor authentication method types"""
    TOTP = "totp"
    HARDWARE_TOKEN = "hardware_token"
    BIOMETRIC_FINGERPRINT = "biometric_fingerprint"
    BIOMETRIC_FACE = "biometric_face"
    DEVICE_ATTESTATION = "device_attestation"
    SMS_OTP = "sms_otp"
    PUSH_NOTIFICATION = "push_notification"


@dataclass
class DeviceMfaCredential:
    """Multi-factor authentication credential for devices

    SECURITY NOTE (Phase 1 Security Reform - 2025-12):
    - totp_secret_encrypted: NEVER store plaintext TOTP secrets in MongoDB
      - Encrypted using Vault Transit engine (key: mfa-encryption-key)
      - Use MFAEncryptionService to encrypt/decrypt
    - backup_codes_hashed: NEVER store plaintext backup codes
      - One-way hashed with SHA256 and unique salt per code
      - Use MFAEncryptionService to hash and verify
    """
    credential_id: str
    device_id: str
    org_id: str
    method_type: MfaMethodType
    # TOTP specific - SECURITY: Encrypted with Vault Transit
    totp_secret_encrypted: Optional[str] = None  # Vault Transit ciphertext, NOT plaintext
    totp_encryption_key_version: Optional[str] = None  # Vault Transit key version
    totp_algorithm: str = "SHA256"
    totp_digits: int = 6
    totp_period: int = 30
    # Hardware token specific
    hardware_token_serial: Optional[str] = None
    hardware_token_manufacturer: Optional[str] = None
    # Biometric specific
    biometric_template_hash: Optional[str] = None
    biometric_algorithm: Optional[str] = None
    # Device attestation
    attestation_key_id: Optional[str] = None
    attestation_nonce: Optional[str] = None
    # Common fields
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    failure_count: int = 0
    # SECURITY: Backup codes are one-way hashed, NOT plaintext
    # Each entry is a dict with 'hash', 'salt', 'used', 'created_at'
    backup_codes_hashed: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceFingerprint:
    """Device fingerprint for behavioral analysis"""
    fingerprint_id: str
    device_id: str
    org_id: str
    # Hardware characteristics
    cpu_info: Optional[str] = None
    memory_info: Optional[str] = None
    storage_info: Optional[str] = None
    network_interfaces: List[str] = field(default_factory=list)
    # Software characteristics
    os_version: Optional[str] = None
    firmware_version: Optional[str] = None
    installed_packages: List[str] = field(default_factory=list)
    running_processes: List[str] = field(default_factory=list)
    # Network characteristics
    network_protocols: List[str] = field(default_factory=list)
    communication_patterns: Dict[str, Any] = field(default_factory=dict)
    # Behavioral patterns
    typical_locations: List[str] = field(default_factory=list)
    typical_operation_hours: List[int] = field(default_factory=list)
    data_volume_patterns: Dict[str, float] = field(default_factory=dict)
    api_usage_patterns: Dict[str, int] = field(default_factory=dict)
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_verified_at: Optional[datetime] = None
    confidence_score: float = 0.0  # 0-100


@dataclass
class BehavioralBaseline:
    """Behavioral baseline for anomaly detection"""
    baseline_id: str
    device_id: str
    org_id: str
    # Communication baselines
    avg_requests_per_hour: float = 0.0
    avg_data_size_kb: float = 0.0
    typical_request_types: List[str] = field(default_factory=list)
    # Temporal baselines
    active_hours_pattern: List[bool] = field(default_factory=lambda: [False] * 24)
    active_days_pattern: List[bool] = field(default_factory=lambda: [False] * 7)
    # Geographic baselines
    typical_countries: List[str] = field(default_factory=list)
    typical_regions: List[str] = field(default_factory=list)
    # Error rate baselines
    typical_error_rate: float = 0.0
    typical_auth_failure_rate: float = 0.0
    # Performance baselines
    typical_response_time_ms: float = 0.0
    typical_cpu_usage: float = 0.0
    typical_memory_usage: float = 0.0
    # Learning parameters
    learning_period_days: int = 30
    confidence_threshold: float = 0.8
    anomaly_threshold: float = 2.0  # Standard deviations
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_learning_update: Optional[datetime] = None


@dataclass
class ThreatIntelligenceIndicator:
    """Threat intelligence indicator for real-time matching"""
    indicator_id: str
    indicator_type: str  # "ip", "domain", "hash", "pattern"
    indicator_value: str
    threat_type: str  # "malware", "botnet", "apt", "scanner"
    confidence_score: float  # 0-100
    severity: ThreatLevel
    source: str  # "commercial_feed", "government", "community"
    description: Optional[str] = None
    ttl_hours: int = 24
    tags: List[str] = field(default_factory=list)
    ioc_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=24))
    is_active: bool = True


@dataclass
class IncidentResponse:
    """Automated incident response configuration"""
    response_id: str
    org_id: str
    trigger_conditions: List[str] = field(default_factory=list)
    response_actions: List[str] = field(default_factory=list)
    # Containment actions
    isolate_device: bool = False
    revoke_credentials: bool = False
    block_ip_address: bool = False
    quarantine_traffic: bool = False
    # Notification actions
    send_alert: bool = True
    escalate_to_soc: bool = False
    create_ticket: bool = True
    # Investigation actions
    capture_forensics: bool = False
    preserve_logs: bool = True
    take_snapshot: bool = False
    # Response timing
    max_response_time_seconds: int = 300
    escalation_time_seconds: int = 900
    auto_resolve_time_hours: int = 24
    # Configuration
    is_active: bool = True
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QuantumResistantCertificate:
    """Quantum-resistant certificate model"""
    cert_id: str
    device_id: str
    org_id: str
    # Certificate details
    algorithm: str  # "CRYSTALS-Dilithium", "FALCON", "SPHINCS+"
    key_size: int
    public_key_pem: str
    certificate_pem: str
    certificate_chain_pem: str
    # Validity
    valid_from: datetime
    valid_until: datetime
    serial_number: str
    fingerprint_sha256: str
    # Quantum-specific
    quantum_safe_algorithm: str
    classical_fallback_cert_id: Optional[str] = None
    hybrid_mode: bool = True  # Uses both quantum-safe and classical
    # Certificate management
    auto_rotation_enabled: bool = True
    rotation_threshold_days: int = 30
    next_rotation_date: Optional[datetime] = None
    rotation_history: List[str] = field(default_factory=list)
    # Status
    is_active: bool = True
    revocation_reason: Optional[str] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComplianceRule:
    """Enterprise compliance rule configuration"""
    rule_id: str
    org_id: str
    name: str
    # Compliance framework - Required fields moved before optional
    framework: str  # "SOC2", "ISO27001", "NIST", "GDPR", "HIPAA"
    control_id: str  # Framework-specific control identifier
    requirement: str
    # Rule configuration
    rule_type: str  # "policy", "technical", "procedural"
    evaluation_frequency: str  # "real_time", "daily", "weekly", "monthly"
    description: Optional[str] = None
    remediation_required: bool = True
    auto_remediation: bool = False
    # Conditions
    conditions: Dict[str, Any] = field(default_factory=dict)
    exemptions: List[str] = field(default_factory=list)
    # Reporting
    evidence_required: List[str] = field(default_factory=list)
    assessment_criteria: Dict[str, Any] = field(default_factory=dict)
    # Status
    is_active: bool = True
    last_assessment: Optional[datetime] = None
    next_assessment: Optional[datetime] = None
    compliance_score: float = 0.0  # 0-100
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SecurityMetrics:
    """Real-time security metrics for monitoring"""
    metrics_id: str
    org_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    # Authentication metrics
    auth_success_rate: float = 0.0
    auth_failure_rate: float = 0.0
    mfa_success_rate: float = 0.0
    cert_validation_rate: float = 0.0
    # Threat detection metrics
    threats_detected: int = 0
    false_positive_rate: float = 0.0
    response_time_avg_ms: float = 0.0
    incidents_auto_resolved: int = 0
    # Compliance metrics
    compliance_score: float = 0.0
    policy_violations: int = 0
    audit_findings: int = 0
    remediation_time_avg_hours: float = 0.0
    # Performance impact metrics
    security_overhead_ms: float = 0.0
    encryption_overhead_percent: float = 0.0
    monitoring_cpu_usage: float = 0.0
    # Coverage metrics
    devices_monitored: int = 0
    coverage_percentage: float = 0.0
    unmonitored_devices: int = 0