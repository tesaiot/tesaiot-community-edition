# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Feature Flag System for Safe Modularization
Purpose: Control rollout with 0% error rate
Date: July 25, 2025

This system allows gradual, controlled rollout of modularized components
with instant rollback capability.
"""

import json
import random
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RolloutStage(Enum):
    """Stages of feature rollout"""
    DISABLED = "disabled"
    INTERNAL_TESTING = "internal_testing"  # 0% external
    CANARY = "canary"  # 1%
    EARLY_ADOPTERS = "early_adopters"  # 5%
    BETA = "beta"  # 25%
    GENERAL_AVAILABILITY = "ga"  # 50%
    FULL_ROLLOUT = "full"  # 100%


class FeatureFlags:
    """
    Feature flag system with sophisticated targeting and rollback capabilities.
    Designed for 0% error modularization.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config/feature_flags.json"
        self.flags = self._load_flags()
        self._rollback_history = []
        
    def _load_flags(self) -> Dict[str, Any]:
        """Load feature flags from configuration"""
        default_flags = {
            "modular_dashboard": {
                "enabled": False,
                "stage": RolloutStage.DISABLED.value,
                "rollout_percentage": 0,
                "allowed_users": [],
                "allowed_ips": [],
                "excluded_users": [],
                "regions": [],
                "start_time": None,
                "metrics": {
                    "requests": 0,
                    "errors": 0,
                    "rollbacks": 0
                }
            },
            "modular_sensor_catalog": {
                "enabled": False,
                "stage": RolloutStage.DISABLED.value,
                "rollout_percentage": 0,
                "allowed_users": [],
                "allowed_ips": [],
                "excluded_users": [],
                "regions": [],
                "start_time": None,
                "metrics": {
                    "requests": 0,
                    "errors": 0,
                    "rollbacks": 0
                }
            },
            "modular_api_client": {
                "enabled": False,
                "stage": RolloutStage.DISABLED.value,
                "rollout_percentage": 0,
                "allowed_users": [],
                "allowed_ips": [],
                "excluded_users": [],
                "regions": [],
                "start_time": None,
                "metrics": {
                    "requests": 0,
                    "errors": 0,
                    "rollbacks": 0
                }
            },
            "protected_update": {
                "enabled": True,
                "stage": RolloutStage.FULL_ROLLOUT.value,
                "rollout_percentage": 100,
                "allowed_users": [],
                "allowed_ips": [],
                "excluded_users": [],
                "regions": [],
                "start_time": datetime.utcnow().isoformat(),
                "metrics": {
                    "requests": 0,
                    "errors": 0,
                    "rollbacks": 0
                },
                "services": {
                    "protected_update": {
                        "enabled": True,
                        "rollout_percentage": 100
                    }
                }
            }
        }
        
        try:
            with open(self.config_file, 'r') as f:
                loaded_flags = json.load(f)
                default_flags.update(loaded_flags)
        except FileNotFoundError:
            logger.info(f"No feature flag config found, using defaults")
        except Exception as e:
            logger.error(f"Error loading feature flags: {e}")
            
        return default_flags
    
    def is_enabled(self, flag_name: str, context: Optional[Dict[str, Any]] = None, service_name: Optional[str] = None) -> bool:
        """
        Check if a feature flag is enabled for the given context.
        
        Args:
            flag_name: Name of the feature flag
            context: Optional context containing user_id, ip, region, etc.
            service_name: Optional specific service within the feature (e.g., 'predictive_analytics')
            
        Returns:
            bool: Whether the feature is enabled
        """
        if flag_name not in self.flags:
            return False
            
        flag = self.flags[flag_name]
        
        # Record request
        flag["metrics"]["requests"] += 1
        
        # Check if globally disabled
        if not flag.get("enabled", False):
            return False
        
        # If checking a specific service within the feature
        if service_name and "services" in flag:
            service_config = flag["services"].get(service_name, {})
            if not service_config.get("enabled", False):
                return False
            # Use service-specific rollout percentage if available
            service_rollout = service_config.get("rollout_percentage")
            if service_rollout is not None:
                # Check service-specific rollout
                if context and context.get("user_id"):
                    hash_input = f"{flag_name}:{service_name}:{context['user_id']}"
                    hash_value = abs(hash(hash_input)) % 100
                    return hash_value < service_rollout
                else:
                    return random.random() * 100 < service_rollout
        
        # Stage-based checks
        stage = RolloutStage(flag.get("stage", RolloutStage.DISABLED.value))
        
        if stage == RolloutStage.DISABLED:
            return False
            
        if stage == RolloutStage.INTERNAL_TESTING:
            # Check if user is in allowed users or IPs for internal testing
            if context:
                if context.get("user_id") in flag.get("allowed_users", []):
                    return True
                if context.get("ip") in flag.get("allowed_ips", []):
                    return True
                if context.get("is_internal", False):
                    return True
            return False
        
        # Context-based checks
        if context:
            # Check excluded users first
            if context.get("user_id") in flag.get("excluded_users", []):
                return False
                
            # Check allowed users
            if context.get("user_id") in flag.get("allowed_users", []):
                return True
                
            # Check allowed IPs
            if context.get("ip") in flag.get("allowed_ips", []):
                return True
                
            # Check regions
            if flag.get("regions") and context.get("region") not in flag["regions"]:
                return False
        
        # Percentage-based rollout
        rollout_percentage = flag.get("rollout_percentage", 0)
        if rollout_percentage == 0:
            return False
        elif rollout_percentage == 100:
            return True
        else:
            # Use consistent hashing for stable assignment
            if context and context.get("user_id"):
                hash_input = f"{flag_name}:{context['user_id']}"
                hash_value = abs(hash(hash_input)) % 100
                return hash_value < rollout_percentage
            else:
                # Random for anonymous users
                return random.random() * 100 < rollout_percentage
    
    def enable_flag(self, flag_name: str, stage: RolloutStage = RolloutStage.INTERNAL_TESTING):
        """Enable a feature flag at specified stage"""
        if flag_name not in self.flags:
            logger.error(f"Unknown flag: {flag_name}")
            return
            
        self.flags[flag_name]["enabled"] = True
        self.flags[flag_name]["stage"] = stage.value
        self.flags[flag_name]["start_time"] = datetime.now().isoformat()
        
        # Set appropriate percentage based on stage
        stage_percentages = {
            RolloutStage.INTERNAL_TESTING: 0,
            RolloutStage.CANARY: 1,
            RolloutStage.EARLY_ADOPTERS: 5,
            RolloutStage.BETA: 25,
            RolloutStage.GENERAL_AVAILABILITY: 50,
            RolloutStage.FULL_ROLLOUT: 100
        }
        
        self.flags[flag_name]["rollout_percentage"] = stage_percentages.get(stage, 0)
        
        self._save_flags()
        logger.info(f"Enabled {flag_name} at stage {stage.value}")
    
    def disable_flag(self, flag_name: str, reason: str = "Manual disable"):
        """Disable a feature flag (emergency rollback)"""
        if flag_name not in self.flags:
            return
            
        # Record rollback
        self._rollback_history.append({
            "flag": flag_name,
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "previous_stage": self.flags[flag_name].get("stage"),
            "metrics": self.flags[flag_name].get("metrics", {}).copy()
        })
        
        self.flags[flag_name]["enabled"] = False
        self.flags[flag_name]["stage"] = RolloutStage.DISABLED.value
        self.flags[flag_name]["rollout_percentage"] = 0
        self.flags[flag_name]["metrics"]["rollbacks"] += 1
        
        self._save_flags()
        logger.warning(f"ROLLBACK: Disabled {flag_name} - Reason: {reason}")
    
    def advance_stage(self, flag_name: str) -> bool:
        """
        Advance flag to next rollout stage if metrics are healthy.
        Returns True if advanced, False if metrics unhealthy.
        """
        if flag_name not in self.flags:
            return False
            
        flag = self.flags[flag_name]
        current_stage = RolloutStage(flag.get("stage", RolloutStage.DISABLED.value))
        
        # Check metrics health
        metrics = flag.get("metrics", {})
        error_rate = metrics.get("errors", 0) / max(metrics.get("requests", 1), 1)
        
        if error_rate > 0.01:  # 1% error threshold
            logger.error(f"Cannot advance {flag_name}: error rate {error_rate:.2%} exceeds threshold")
            return False
        
        # Determine next stage
        stage_order = [
            RolloutStage.DISABLED,
            RolloutStage.INTERNAL_TESTING,
            RolloutStage.CANARY,
            RolloutStage.EARLY_ADOPTERS,
            RolloutStage.BETA,
            RolloutStage.GENERAL_AVAILABILITY,
            RolloutStage.FULL_ROLLOUT
        ]
        
        try:
            current_index = stage_order.index(current_stage)
            if current_index < len(stage_order) - 1:
                next_stage = stage_order[current_index + 1]
                self.enable_flag(flag_name, next_stage)
                return True
        except ValueError:
            logger.error(f"Invalid stage for {flag_name}")
            
        return False
    
    def record_error(self, flag_name: str):
        """Record an error for a feature flag"""
        if flag_name in self.flags:
            self.flags[flag_name]["metrics"]["errors"] += 1
            
            # Auto-rollback if error rate exceeds threshold
            metrics = self.flags[flag_name]["metrics"]
            error_rate = metrics["errors"] / max(metrics["requests"], 1)
            
            if error_rate > 0.01:  # 1% threshold
                self.disable_flag(flag_name, f"Auto-rollback: error rate {error_rate:.2%}")
    
    def get_metrics(self, flag_name: str) -> Dict[str, Any]:
        """Get metrics for a feature flag"""
        if flag_name not in self.flags:
            return {}
            
        metrics = self.flags[flag_name].get("metrics", {})
        requests = max(metrics.get("requests", 1), 1)
        
        return {
            "requests": requests,
            "errors": metrics.get("errors", 0),
            "error_rate": metrics.get("errors", 0) / requests,
            "rollbacks": metrics.get("rollbacks", 0),
            "stage": self.flags[flag_name].get("stage"),
            "rollout_percentage": self.flags[flag_name].get("rollout_percentage", 0),
            "enabled": self.flags[flag_name].get("enabled", False)
        }
    
    def _save_flags(self):
        """Save current flag configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.flags, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving feature flags: {e}")


# Global instance
feature_flags = FeatureFlags()


# Decorator for easy feature flag checking
def feature_flag(flag_name: str):
    """Decorator to check feature flag before executing function"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract context from request if available
            context = kwargs.get('context', {})
            
            if feature_flags.is_enabled(flag_name, context):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    feature_flags.record_error(flag_name)
                    raise
            else:
                # Return None or handle gracefully
                return None
        return wrapper
    return decorator

# Alias for compatibility with DI container
FeatureFlagService = FeatureFlags

# Global instance for easy access
feature_flags = FeatureFlags()
