# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Professional OTP Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Professional OTP (One-Time Password) Service providing:
- Secure 6-digit OTP generation using secrets module
- Redis storage with TTL (OTP_EXPIRE_MINUTES) and one-time use
- Multi-level rate limiting (user/IP/global)
- OTP verification with attempt tracking
- Cooldown period between resends (30 seconds)
- Admin bypass capabilities for testing
- Production-ready security and validation
"""

import os
import secrets
import time
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

try:
    from ..core.database import get_redis
    from .base_service import BaseService
except ImportError:
    # Fallback imports for testing
    get_redis = lambda: None
    BaseService = object

logger = logging.getLogger(__name__)


class OTPError(Exception):
    """Base exception for OTP-related errors."""
    pass


class RateLimitExceeded(OTPError):
    """Raised when rate limit is exceeded."""
    pass


class OTPUsed(OTPError):
    """Raised when OTP has already been used."""
    pass


class OTPInvalid(OTPError):
    """Raised when OTP is invalid."""
    pass


class OTPAttemptLimitExceeded(OTPError):
    """Raised when maximum verification attempts exceeded."""
    pass


class CooldownActive(OTPError):
    """Raised when cooldown period is still active."""
    pass


class OTPStatus(Enum):
    """OTP status enumeration."""
    PENDING = "pending"
    VERIFIED = "verified"
    EXHAUSTED = "exhausted"  # Too many attempts


@dataclass
class OTPResult:
    """Result object for OTP operations."""
    success: bool
    otp_code: Optional[str] = None
    message: str = ""
    created_at: Optional[datetime] = None
    attempts_remaining: Optional[int] = None
    cooldown_remaining: Optional[int] = None
    rate_limit_info: Optional[Dict[str, Any]] = None


@dataclass
class RateLimitInfo:
    """Rate limit information."""
    limit_type: str
    limit: int
    current: int
    reset_time: datetime
    exceeded: bool


class OTPService(BaseService):
    """
    Professional OTP Service with comprehensive security features.
    
    Features:
    - Secure OTP generation using secrets module
    - Redis storage with TTL (OTP_EXPIRE_MINUTES) + one-time use
    - Multi-level rate limiting
    - Attempt tracking and limits
    - Cooldown periods
    - Admin bypass capabilities
    - Comprehensive logging and monitoring
    """
    
    def __init__(self, redis_client=None, logger=None):
        """
        Initialize OTP service.
        
        Args:
            redis_client: Redis client instance (optional)
            logger: Logger instance (optional)
        """
        super().__init__(redis_client=redis_client, logger=logger)
        
        # Load configuration from environment variables
        self.otp_length = int(os.getenv('OTP_LENGTH', '6'))
        self.max_attempts = int(os.getenv('OTP_MAX_ATTEMPTS', '3'))
        self.cooldown_seconds = int(os.getenv('OTP_COOLDOWN_SECONDS', '30'))
        # SECURITY: OTPs expire. They were previously stored with no TTL and
        # stayed valid forever until used.
        self.otp_expire_minutes = int(os.getenv('OTP_EXPIRE_MINUTES', '10'))
        
        # Rate limiting configuration
        self.rate_limit_hours = int(os.getenv('OTP_RATE_LIMIT_HOURS', '1'))
        self.rate_limit_per_user_hour = int(os.getenv('OTP_RATE_LIMIT_PER_USER_HOUR', '3'))
        self.rate_limit_per_ip_minute = int(os.getenv('OTP_RATE_LIMIT_PER_IP_MINUTE', '10'))
        self.rate_limit_global_hour = int(os.getenv('OTP_RATE_LIMIT_GLOBAL_HOUR', '100'))
        
        # Redis database selection (default to DB 1 for OTP)
        self.redis_db = 1
        
        # Cache prefix for OTP operations
        self._cache_prefix = "tesa:otp"
        
        # Validate configuration
        self._validate_configuration()
    
    def _validate_configuration(self):
        """Validate OTP service configuration."""
        if self.otp_length < 4 or self.otp_length > 10:
            raise ValueError("OTP length must be between 4 and 10 digits")
        
        if self.max_attempts < 1 or self.max_attempts > 10:
            raise ValueError("Max attempts must be between 1 and 10")
        
        if self.cooldown_seconds < 0 or self.cooldown_seconds > 300:
            raise ValueError("Cooldown must be between 0 and 300 seconds")

        if self.otp_expire_minutes < 1 or self.otp_expire_minutes > 1440:
            raise ValueError("OTP expiry must be between 1 and 1440 minutes")

        logger.info(f"OTP Service initialized: length={self.otp_length}, "
                   f"max_attempts={self.max_attempts}, "
                   f"expire_minutes={self.otp_expire_minutes}")
    
    def _get_redis_client(self):
        """Get Redis client with DB selection."""
        if self.redis:
            return self.redis
        
        # Create a dedicated Redis connection for OTP service to avoid affecting shared connections
        try:
            import redis as redis_module
            redis_client = redis_module.Redis(
                host=os.getenv('REDIS_HOST', 'redis'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD') or None,
                db=self.redis_db,  # Connect directly to DB 1
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            redis_client.ping()
            return redis_client
        except Exception as e:
            logger.error(f"Failed to create dedicated Redis connection for OTP service: {e}")
            # Fallback to shared connection
            redis_client = get_redis()
            if redis_client:
                # Switch to OTP database (DB 1)
                redis_client.select(self.redis_db)
            return redis_client
    
    def _remaining_ttl(self, redis_client, key: str) -> int:
        """Remaining TTL for a key in seconds (fallback: full OTP window)."""
        try:
            ttl = redis_client.ttl(key)
            if ttl and ttl > 0:
                return int(ttl)
        except Exception:
            pass
        return self.otp_expire_minutes * 60

    def _generate_otp(self) -> str:
        """
        Generate cryptographically secure OTP.
        
        Returns:
            Secure random OTP string
        """
        # Use secrets module for cryptographic security
        otp_int = secrets.randbelow(10 ** self.otp_length)
        # Ensure leading zeros are preserved
        otp = str(otp_int).zfill(self.otp_length)
        
        logger.debug(f"Generated OTP with length {len(otp)}")
        return otp
    
    def _hash_identifier(self, identifier: str) -> str:
        """
        Hash identifier for privacy protection.
        
        Args:
            identifier: User identifier (email, phone, user_id)
            
        Returns:
            SHA256 hash of identifier
        """
        return hashlib.sha256(identifier.encode('utf-8')).hexdigest()
    
    def _get_otp_key(self, identifier: str) -> str:
        """Get Redis key for OTP storage."""
        hashed_id = self._hash_identifier(identifier)
        return f"{self._cache_prefix}:otp:{hashed_id}"
    
    def _get_attempts_key(self, identifier: str) -> str:
        """Get Redis key for attempt tracking."""
        hashed_id = self._hash_identifier(identifier)
        return f"{self._cache_prefix}:attempts:{hashed_id}"
    
    def _get_cooldown_key(self, identifier: str) -> str:
        """Get Redis key for cooldown tracking."""
        hashed_id = self._hash_identifier(identifier)
        return f"{self._cache_prefix}:cooldown:{hashed_id}"
    
    def _get_rate_limit_key(self, limit_type: str, identifier: str) -> str:
        """Get Redis key for rate limiting."""
        if limit_type == "global":
            return f"{self._cache_prefix}:rate_limit:global"
        elif limit_type == "user":
            hashed_id = self._hash_identifier(identifier)
            return f"{self._cache_prefix}:rate_limit:user:{hashed_id}"
        elif limit_type == "ip":
            return f"{self._cache_prefix}:rate_limit:ip:{identifier}"
        else:
            raise ValueError(f"Invalid rate limit type: {limit_type}")
    
    def _check_rate_limit(self, redis_client, limit_type: str, identifier: str, 
                         limit: int, window_seconds: int, is_admin: bool = False) -> RateLimitInfo:
        """
        Check rate limit for specific type and identifier.
        
        Args:
            redis_client: Redis client
            limit_type: Type of rate limit (user, ip, global)
            identifier: Identifier to check
            limit: Maximum allowed requests
            window_seconds: Time window in seconds
            is_admin: Whether this is an admin request (bypasses limits)
            
        Returns:
            RateLimitInfo object
        """
        if is_admin:
            return RateLimitInfo(
                limit_type=limit_type,
                limit=limit,
                current=0,
                reset_time=datetime.utcnow(),
                exceeded=False
            )
        
        key = self._get_rate_limit_key(limit_type, identifier)
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        try:
            # Use sliding window rate limiting
            pipe = redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current entries
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, window_seconds)
            
            results = pipe.execute()
            current_count = results[1]
            
            reset_time = datetime.utcnow() + timedelta(seconds=window_seconds)
            exceeded = current_count >= limit
            
            if exceeded:
                # Remove the request we just added since it exceeds limit
                redis_client.zrem(key, str(current_time))
            
            return RateLimitInfo(
                limit_type=limit_type,
                limit=limit,
                current=current_count,
                reset_time=reset_time,
                exceeded=exceeded
            )
            
        except Exception as e:
            logger.error(f"Rate limit check failed for {limit_type}: {e}")
            # Fail open for availability
            return RateLimitInfo(
                limit_type=limit_type,
                limit=limit,
                current=0,
                reset_time=datetime.utcnow(),
                exceeded=False
            )
    
    def _check_all_rate_limits(self, redis_client, user_identifier: str, 
                              ip_address: Optional[str] = None, is_admin: bool = False) -> Dict[str, RateLimitInfo]:
        """
        Check all applicable rate limits.
        
        Args:
            redis_client: Redis client
            user_identifier: User identifier
            ip_address: IP address (optional)
            is_admin: Whether this is an admin request
            
        Returns:
            Dictionary of rate limit information
        """
        rate_limits = {}
        
        # User rate limit (per hour)
        rate_limits['user'] = self._check_rate_limit(
            redis_client, 'user', user_identifier,
            self.rate_limit_per_user_hour, 3600, is_admin
        )
        
        # IP rate limit (per minute)
        if ip_address:
            rate_limits['ip'] = self._check_rate_limit(
                redis_client, 'ip', ip_address,
                self.rate_limit_per_ip_minute, 60, is_admin
            )
        
        # Global rate limit (per hour)
        rate_limits['global'] = self._check_rate_limit(
            redis_client, 'global', 'all',
            self.rate_limit_global_hour, 3600, is_admin
        )
        
        return rate_limits
    
    def _check_cooldown(self, redis_client, identifier: str, is_admin: bool = False) -> int:
        """
        Check cooldown period for identifier.
        
        Args:
            redis_client: Redis client
            identifier: User identifier
            is_admin: Whether this is an admin request
            
        Returns:
            Remaining cooldown seconds (0 if no cooldown)
        """
        if is_admin or self.cooldown_seconds == 0:
            return 0
        
        cooldown_key = self._get_cooldown_key(identifier)
        
        try:
            last_request = redis_client.get(cooldown_key)
            if last_request:
                last_time = float(last_request)
                elapsed = time.time() - last_time
                remaining = max(0, self.cooldown_seconds - elapsed)
                return int(remaining)
            return 0
        except Exception as e:
            logger.error(f"Cooldown check failed: {e}")
            return 0
    
    def _set_cooldown(self, redis_client, identifier: str):
        """Set cooldown period for identifier."""
        if self.cooldown_seconds > 0:
            cooldown_key = self._get_cooldown_key(identifier)
            try:
                redis_client.setex(cooldown_key, self.cooldown_seconds, str(time.time()))
            except Exception as e:
                logger.error(f"Failed to set cooldown: {e}")
    
    @BaseService.timing_decorator
    def generate_otp(self, identifier: str, ip_address: Optional[str] = None, 
                    is_admin: bool = False, context: Optional[Dict[str, Any]] = None) -> OTPResult:
        """
        Generate and store a new OTP.
        
        Args:
            identifier: User identifier (email, phone, user_id)
            ip_address: Client IP address for rate limiting
            is_admin: Whether this is an admin request (bypasses rate limits)
            context: Additional context for logging
            
        Returns:
            OTPResult with generation status and information
        """
        try:
            redis_client = self._get_redis_client()
            if not redis_client:
                logger.error("Redis client unavailable for OTP generation")
                return OTPResult(
                    success=False,
                    message="OTP service temporarily unavailable"
                )
            
            # Check cooldown period
            cooldown_remaining = self._check_cooldown(redis_client, identifier, is_admin)
            if cooldown_remaining > 0:
                logger.warning(f"OTP generation blocked by cooldown: {identifier}, {cooldown_remaining}s remaining")
                return OTPResult(
                    success=False,
                    message=f"Please wait {cooldown_remaining} seconds before requesting another OTP",
                    cooldown_remaining=cooldown_remaining
                )
            
            # Check rate limits
            rate_limits = self._check_all_rate_limits(redis_client, identifier, ip_address, is_admin)
            
            # Check if any rate limit is exceeded
            exceeded_limits = [info for info in rate_limits.values() if info.exceeded]
            if exceeded_limits:
                limit_info = exceeded_limits[0]
                logger.warning(f"Rate limit exceeded for {identifier}: {limit_info.limit_type}")
                return OTPResult(
                    success=False,
                    message=f"Rate limit exceeded. Please try again later.",
                    rate_limit_info={
                        'type': limit_info.limit_type,
                        'limit': limit_info.limit,
                        'reset_time': limit_info.reset_time.isoformat()
                    }
                )
            
            # Generate new OTP
            otp_code = self._generate_otp()
            created_at = datetime.utcnow()
            
            # Store OTP in Redis (no expiry time)
            otp_key = self._get_otp_key(identifier)
            otp_data = {
                'code': otp_code,
                'created_at': created_at.isoformat(),
                'attempts': 0,
                'status': OTPStatus.PENDING.value,
                'identifier_hash': self._hash_identifier(identifier),
                'context': context or {}
            }
            
            # Store with TTL: OTP is valid for OTP_EXPIRE_MINUTES or until used
            redis_client.setex(otp_key, self.otp_expire_minutes * 60, json.dumps(otp_data))
            
            # Reset attempt counter
            attempts_key = self._get_attempts_key(identifier)
            redis_client.delete(attempts_key)
            
            # Set cooldown
            self._set_cooldown(redis_client, identifier)
            
            logger.info(f"OTP generated for {self._hash_identifier(identifier)[:8]}..., created at {created_at}")
            
            return OTPResult(
                success=True,
                otp_code=otp_code,
                message="OTP generated successfully",
                created_at=created_at,
                attempts_remaining=self.max_attempts,
                rate_limit_info={k: {
                    'limit': v.limit,
                    'current': v.current,
                    'reset_time': v.reset_time.isoformat()
                } for k, v in rate_limits.items()}
            )
            
        except Exception as e:
            logger.error(f"OTP generation failed for {identifier}: {e}", exc_info=True)
            return OTPResult(
                success=False,
                message="Failed to generate OTP"
            )
    
    @BaseService.timing_decorator
    def verify_otp(self, identifier: str, otp_code: str, 
                  context: Optional[Dict[str, Any]] = None) -> OTPResult:
        """
        Verify an OTP code.
        
        Args:
            identifier: User identifier
            otp_code: OTP code to verify
            context: Additional context for logging
            
        Returns:
            OTPResult with verification status
        """
        try:
            redis_client = self._get_redis_client()
            if not redis_client:
                logger.error("Redis client unavailable for OTP verification")
                return OTPResult(
                    success=False,
                    message="OTP service temporarily unavailable"
                )
            
            otp_key = self._get_otp_key(identifier)
            otp_data_str = redis_client.get(otp_key)
            
            if not otp_data_str:
                logger.warning(f"OTP not found for {self._hash_identifier(identifier)[:8]}...")
                return OTPResult(
                    success=False,
                    message="OTP not found"
                )
            
            try:
                otp_data = json.loads(otp_data_str)
            except json.JSONDecodeError:
                logger.error("Failed to decode OTP data")
                return OTPResult(
                    success=False,
                    message="Invalid OTP data"
                )
            
            # Check if OTP is already verified or exhausted
            if otp_data.get('status') == OTPStatus.VERIFIED.value:
                logger.warning(f"OTP already verified for {self._hash_identifier(identifier)[:8]}...")
                return OTPResult(
                    success=False,
                    message="OTP has already been used"
                )
            
            if otp_data.get('status') == OTPStatus.EXHAUSTED.value:
                logger.warning(f"OTP exhausted for {self._hash_identifier(identifier)[:8]}...")
                return OTPResult(
                    success=False,
                    message="Maximum verification attempts exceeded"
                )
            
            # Increment attempt counter
            attempts = otp_data.get('attempts', 0) + 1
            attempts_remaining = max(0, self.max_attempts - attempts)
            
            # Check if code matches
            if otp_code == otp_data['code']:
                # Success - delete OTP immediately after verification
                redis_client.delete(otp_key)
                
                logger.info(f"OTP verified successfully for {self._hash_identifier(identifier)[:8]}...")
                
                return OTPResult(
                    success=True,
                    message="OTP verified successfully",
                    attempts_remaining=attempts_remaining
                )
            else:
                # Wrong code - update attempt count
                otp_data['attempts'] = attempts
                
                if attempts >= self.max_attempts:
                    # Mark as exhausted
                    otp_data['status'] = OTPStatus.EXHAUSTED.value
                    otp_data['exhausted_at'] = datetime.utcnow().isoformat()
                    
                    logger.warning(f"OTP exhausted after {attempts} attempts for {self._hash_identifier(identifier)[:8]}...")

                    # Keep for audit until the OTP TTL elapses
                    redis_client.setex(
                        otp_key, self._remaining_ttl(redis_client, otp_key),
                        json.dumps(otp_data)
                    )
                    
                    return OTPResult(
                        success=False,
                        message="Maximum verification attempts exceeded",
                        attempts_remaining=0
                    )
                else:
                    # Update with new attempt count, preserving the TTL
                    redis_client.setex(
                        otp_key, self._remaining_ttl(redis_client, otp_key),
                        json.dumps(otp_data)
                    )
                    
                    logger.warning(f"Invalid OTP code for {self._hash_identifier(identifier)[:8]}..., "
                                 f"attempt {attempts}/{self.max_attempts}")
                    
                    return OTPResult(
                        success=False,
                        message=f"Invalid OTP code. {attempts_remaining} attempts remaining.",
                        attempts_remaining=attempts_remaining
                    )
                    
        except Exception as e:
            logger.error(f"OTP verification failed for {identifier}: {e}", exc_info=True)
            return OTPResult(
                success=False,
                message="OTP verification failed"
            )
    
    @BaseService.timing_decorator
    def resend_otp(self, identifier: str, ip_address: Optional[str] = None, 
                  is_admin: bool = False, context: Optional[Dict[str, Any]] = None) -> OTPResult:
        """
        Resend (regenerate) OTP for identifier.
        
        Args:
            identifier: User identifier
            ip_address: Client IP address
            is_admin: Whether this is an admin request
            context: Additional context
            
        Returns:
            OTPResult with resend status
        """
        # Resend is essentially generate with existing OTP invalidation
        try:
            redis_client = self._get_redis_client()
            if redis_client:
                # Invalidate existing OTP
                otp_key = self._get_otp_key(identifier)
                redis_client.delete(otp_key)
            
            # Generate new OTP
            return self.generate_otp(identifier, ip_address, is_admin, context)
            
        except Exception as e:
            logger.error(f"OTP resend failed for {identifier}: {e}", exc_info=True)
            return OTPResult(
                success=False,
                message="Failed to resend OTP"
            )
    
    def get_otp_status(self, identifier: str) -> Dict[str, Any]:
        """
        Get current OTP status for identifier.
        
        Args:
            identifier: User identifier
            
        Returns:
            Dictionary with OTP status information
        """
        try:
            redis_client = self._get_redis_client()
            if not redis_client:
                return {'status': 'service_unavailable'}
            
            otp_key = self._get_otp_key(identifier)
            otp_data_str = redis_client.get(otp_key)
            
            if not otp_data_str:
                return {'status': 'no_otp'}
            
            try:
                otp_data = json.loads(otp_data_str)
                
                return {
                    'status': otp_data.get('status', 'unknown'),
                    'created_at': otp_data.get('created_at'),
                    'attempts': otp_data.get('attempts', 0),
                    'max_attempts': self.max_attempts,
                    'expires': True,  # OTPs expire after OTP_EXPIRE_MINUTES
                    'expire_minutes': self.otp_expire_minutes
                }
                
            except json.JSONDecodeError:
                return {'status': 'invalid_data'}
                
        except Exception as e:
            logger.error(f"Failed to get OTP status for {identifier}: {e}")
            return {'status': 'error'}
    
    def cleanup_used_otps(self) -> Dict[str, int]:
        """
        Clean up used/exhausted OTP entries (maintenance function).
        
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            redis_client = self._get_redis_client()
            if not redis_client:
                return {'error': 'Redis unavailable'}
            
            stats = {
                'checked': 0,
                'used': 0,
                'exhausted': 0,
                'cleaned': 0
            }
            
            # Scan for OTP keys
            pattern = f"{self._cache_prefix}:otp:*"
            for key in redis_client.scan_iter(match=pattern):
                stats['checked'] += 1
                
                try:
                    otp_data_str = redis_client.get(key)
                    if otp_data_str:
                        otp_data = json.loads(otp_data_str)
                        status = otp_data.get('status')
                        
                        if status == OTPStatus.VERIFIED.value:
                            redis_client.delete(key)
                            stats['used'] += 1
                            stats['cleaned'] += 1
                        elif status == OTPStatus.EXHAUSTED.value:
                            redis_client.delete(key)
                            stats['exhausted'] += 1
                            stats['cleaned'] += 1
                except (json.JSONDecodeError, Exception):
                    # Clean up invalid data
                    redis_client.delete(key)
                    stats['cleaned'] += 1
            
            logger.info(f"OTP cleanup completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"OTP cleanup failed: {e}")
            return {'error': str(e)}
    
    async def validate_permissions(self, user_role: str, org_id: Optional[str] = None,
                                 resource_id: Optional[str] = None, action: str = 'read') -> bool:
        """
        Validate permissions for OTP service operations.
        
        Args:
            user_role: User's role
            org_id: Organization ID
            resource_id: Resource ID
            action: Action being performed
            
        Returns:
            True if user has permission
        """
        # OTP service permissions:
        # - Any authenticated user can generate/verify OTPs for themselves
        # - Platform admins can perform admin operations
        # - Organization admins can help users in their org
        
        if user_role in ['platform_admin', 'super_admin']:
            return True
        
        if action in ['generate', 'verify', 'resend'] and user_role in ['user', 'admin', 'org_admin']:
            return True
        
        if action in ['cleanup', 'status'] and user_role in ['admin', 'org_admin', 'platform_admin']:
            return True
        
        return False
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get OTP service configuration and status.
        
        Returns:
            Dictionary with service information
        """
        return {
            'service': 'OTP Service',
            'version': '1.0.0',
            'configuration': {
                'otp_length': self.otp_length,
                'expires_on_time': True,
                'expire_minutes': self.otp_expire_minutes,
                'expires_on_use': True,
                'max_attempts': self.max_attempts,
                'cooldown_seconds': self.cooldown_seconds,
                'rate_limits': {
                    'per_user_hour': self.rate_limit_per_user_hour,
                    'per_ip_minute': self.rate_limit_per_ip_minute,
                    'global_hour': self.rate_limit_global_hour
                }
            },
            'redis_db': self.redis_db,
            'features': [
                'Secure OTP generation',
                'Redis storage with time expiry (OTP_EXPIRE_MINUTES)',
                'One-time use only (deleted after verification)',
                'Multi-level rate limiting',
                'Attempt tracking',
                'Cooldown periods',
                'Admin bypass',
                'Comprehensive logging'
            ]
        }


# Convenience functions for backward compatibility and ease of use
def generate_otp(identifier: str, ip_address: Optional[str] = None, 
                is_admin: bool = False, context: Optional[Dict[str, Any]] = None) -> OTPResult:
    """Convenience function to generate OTP."""
    service = OTPService()
    return service.generate_otp(identifier, ip_address, is_admin, context)


def verify_otp(identifier: str, otp_code: str, 
              context: Optional[Dict[str, Any]] = None) -> OTPResult:
    """Convenience function to verify OTP."""
    service = OTPService()
    return service.verify_otp(identifier, otp_code, context)


def resend_otp(identifier: str, ip_address: Optional[str] = None, 
              is_admin: bool = False, context: Optional[Dict[str, Any]] = None) -> OTPResult:
    """Convenience function to resend OTP."""
    service = OTPService()
    return service.resend_otp(identifier, ip_address, is_admin, context)