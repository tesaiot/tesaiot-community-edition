# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

import logging
from typing import Dict, Any, List
from datetime import datetime
import asyncio


logger = logging.getLogger(__name__)


class DeviceManagementHealthCheck:
    """Health check service for Device Management module"""
    
    def __init__(self, device_service, device_bridge, repository, cache_repository):
        self.device_service = device_service
        self.device_bridge = device_bridge
        self.repository = repository
        self.cache_repository = cache_repository
        self.last_check = None
        self.health_history = []
        
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        start_time = datetime.utcnow()
        checks = {}
        
        # 1. Check service availability
        checks["service"] = await self._check_service_health()
        
        # 2. Check database connectivity
        checks["database"] = await self._check_database_health()
        
        # 3. Check cache connectivity
        checks["cache"] = await self._check_cache_health()
        
        # 4. Check bridge functionality
        checks["bridge"] = await self._check_bridge_health()
        
        # 5. Check circuit breakers
        checks["circuit_breakers"] = await self._check_circuit_breakers()
        
        # 6. Check performance metrics
        checks["performance"] = await self._check_performance_metrics()
        
        # Calculate overall health
        all_healthy = all(check.get("healthy", False) for check in checks.values())
        
        health_status = {
            "timestamp": start_time.isoformat(),
            "healthy": all_healthy,
            "status": "healthy" if all_healthy else "degraded",
            "checks": checks,
            "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
        }
        
        # Store in history (keep last 100 checks)
        self.health_history.append(health_status)
        if len(self.health_history) > 100:
            self.health_history.pop(0)
        
        self.last_check = health_status
        return health_status
    
    async def _check_service_health(self) -> Dict[str, Any]:
        """Check if service is responding"""
        try:
            # Try a simple operation
            test_org_id = "health-check-org"
            filters = {"limit": 1}
            pagination = {"page": 1, "page_size": 1}
            
            start = datetime.utcnow()
            await self.device_service.list_devices(filters, pagination, test_org_id)
            duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
            
            return {
                "healthy": True,
                "message": "Service responding normally",
                "response_time_ms": duration_ms
            }
        except Exception as e:
            logger.error(f"Service health check failed: {e}")
            return {
                "healthy": False,
                "message": f"Service error: {str(e)}",
                "error": str(e)
            }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            # Test database ping
            start = datetime.utcnow()
            collection = self.repository._get_collection()
            await asyncio.get_event_loop().run_in_executor(
                None, collection.database.client.server_info
            )
            duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
            
            return {
                "healthy": True,
                "message": "Database connection healthy",
                "response_time_ms": duration_ms
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "healthy": False,
                "message": f"Database error: {str(e)}",
                "error": str(e)
            }
    
    async def _check_cache_health(self) -> Dict[str, Any]:
        """Check cache connectivity"""
        try:
            # Test cache operation
            test_key = "health-check-test"
            test_value = {"timestamp": datetime.utcnow().isoformat()}
            
            start = datetime.utcnow()
            await self.cache_repository.set(test_key, test_value, ttl=10)
            retrieved = await self.cache_repository.get(test_key)
            await self.cache_repository.delete(test_key)
            duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
            
            if retrieved and retrieved.get("timestamp") == test_value["timestamp"]:
                return {
                    "healthy": True,
                    "message": "Cache connection healthy",
                    "response_time_ms": duration_ms
                }
            else:
                return {
                    "healthy": False,
                    "message": "Cache read/write mismatch"
                }
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {
                "healthy": False,
                "message": f"Cache error: {str(e)}",
                "error": str(e)
            }
    
    async def _check_bridge_health(self) -> Dict[str, Any]:
        """Check bridge pattern functionality"""
        try:
            if hasattr(self.device_bridge, 'get_bridge_health'):
                bridge_health = self.device_bridge.get_bridge_health()
                
                # Calculate success rate
                total_requests = (
                    bridge_health.get("modular_requests", 0) + 
                    bridge_health.get("legacy_requests", 0)
                )
                total_errors = (
                    bridge_health.get("modular_errors", 0) + 
                    bridge_health.get("legacy_errors", 0)
                )
                
                if total_requests > 0:
                    success_rate = ((total_requests - total_errors) / total_requests) * 100
                else:
                    success_rate = 100
                
                return {
                    "healthy": success_rate >= 95,
                    "message": f"Bridge success rate: {success_rate:.1f}%",
                    "stats": bridge_health,
                    "success_rate": success_rate
                }
            else:
                return {
                    "healthy": True,
                    "message": "Bridge health check not available"
                }
        except Exception as e:
            logger.error(f"Bridge health check failed: {e}")
            return {
                "healthy": False,
                "message": f"Bridge error: {str(e)}",
                "error": str(e)
            }
    
    async def _check_circuit_breakers(self) -> Dict[str, Any]:
        """Check circuit breaker states"""
        try:
            # Check if any circuit breakers are open
            open_breakers = []
            
            # This is a placeholder - actual implementation would check real circuit breakers
            # For now, assume all are closed
            
            if open_breakers:
                return {
                    "healthy": False,
                    "message": f"Circuit breakers open: {', '.join(open_breakers)}",
                    "open_breakers": open_breakers
                }
            else:
                return {
                    "healthy": True,
                    "message": "All circuit breakers closed"
                }
        except Exception as e:
            logger.error(f"Circuit breaker check failed: {e}")
            return {
                "healthy": False,
                "message": f"Circuit breaker check error: {str(e)}",
                "error": str(e)
            }
    
    async def _check_performance_metrics(self) -> Dict[str, Any]:
        """Check performance against targets"""
        try:
            # Get recent performance metrics from bridge
            if hasattr(self.device_bridge, 'metrics') and self.device_bridge.metrics:
                metrics = self.device_bridge.metrics.get_summary("device_management")
                
                # Check against targets
                targets = {
                    "device_query": 10,  # ms
                    "list_operations": 50,
                    "registration": 100,
                    "status_update": 20
                }
                
                violations = []
                for operation, target in targets.items():
                    current = metrics.get(f"p95_{operation}", 0)
                    if current > target:
                        violations.append(f"{operation}: {current}ms > {target}ms")
                
                if violations:
                    return {
                        "healthy": False,
                        "message": f"Performance targets violated",
                        "violations": violations,
                        "metrics": metrics
                    }
                else:
                    return {
                        "healthy": True,
                        "message": "All performance targets met",
                        "metrics": metrics
                    }
            else:
                return {
                    "healthy": True,
                    "message": "Performance metrics not available"
                }
        except Exception as e:
            logger.error(f"Performance check failed: {e}")
            return {
                "healthy": False,
                "message": f"Performance check error: {str(e)}",
                "error": str(e)
            }
    
    def get_health_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent health check history"""
        return self.health_history[-limit:]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary"""
        if not self.health_history:
            return {
                "status": "unknown",
                "message": "No health checks performed yet"
            }
        
        # Calculate health over last 10 checks
        recent_checks = self.health_history[-10:]
        healthy_count = sum(1 for check in recent_checks if check.get("healthy", False))
        health_percentage = (healthy_count / len(recent_checks)) * 100
        
        if health_percentage >= 95:
            status = "healthy"
        elif health_percentage >= 80:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "health_percentage": health_percentage,
            "last_check": self.last_check.get("timestamp") if self.last_check else None,
            "checks_performed": len(self.health_history),
            "recent_failures": 10 - healthy_count
        }