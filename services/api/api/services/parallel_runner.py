# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Parallel Runner for Safe Modularization
Purpose: Run old and new implementations in parallel to ensure identical behavior
Date: July 25, 2025

This system enables the Scientist pattern - running experiments in production
without affecting users.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import traceback

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Result of comparing old vs new implementation"""
    module_name: str
    function_name: str
    timestamp: datetime
    old_result: Any
    new_result: Any
    old_duration: float
    new_duration: float
    old_error: Optional[str] = None
    new_error: Optional[str] = None
    match: bool = False
    mismatch_details: Optional[str] = None
    
    def to_dict(self):
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }


class ParallelRunner:
    """
    Runs old and new implementations in parallel for comparison.
    Implements the Scientist pattern for safe refactoring.
    """
    
    def __init__(self, metrics_collector=None):
        self.metrics_collector = metrics_collector
        self.comparison_results = []
        self.mismatch_handlers = []
        
    def add_mismatch_handler(self, handler: Callable[[ComparisonResult], None]):
        """Add a handler to be called when results don't match"""
        self.mismatch_handlers.append(handler)
        
    async def run_parallel(
        self,
        module_name: str,
        function_name: str,
        old_func: Callable,
        new_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Run old and new implementations in parallel.
        Always returns the old implementation's result.
        
        Args:
            module_name: Name of the module being refactored
            function_name: Name of the function being refactored
            old_func: Original implementation
            new_func: New modular implementation
            *args, **kwargs: Arguments to pass to both functions
            
        Returns:
            Result from old implementation (for safety)
        """
        # Always run old implementation synchronously
        old_start = time.time()
        old_result = None
        old_error = None
        
        try:
            old_result = old_func(*args, **kwargs)
            old_duration = time.time() - old_start
        except Exception as e:
            old_error = str(e)
            old_duration = time.time() - old_start
            logger.error(f"Error in old implementation: {e}")
            raise  # Re-raise to maintain existing behavior
        
        # Run new implementation asynchronously (non-blocking)
        asyncio.create_task(
            self._run_and_compare(
                module_name, function_name,
                old_result, old_duration, old_error,
                new_func, args, kwargs
            )
        )
        
        return old_result
    
    async def _run_and_compare(
        self,
        module_name: str,
        function_name: str,
        old_result: Any,
        old_duration: float,
        old_error: Optional[str],
        new_func: Callable,
        args: tuple,
        kwargs: dict
    ):
        """Run new implementation and compare with old"""
        new_start = time.time()
        new_result = None
        new_error = None
        
        try:
            # Run new implementation
            if asyncio.iscoroutinefunction(new_func):
                new_result = await new_func(*args, **kwargs)
            else:
                new_result = new_func(*args, **kwargs)
            new_duration = time.time() - new_start
            
        except Exception as e:
            new_error = str(e)
            new_duration = time.time() - new_start
            logger.error(f"Error in new implementation of {module_name}.{function_name}: {e}")
            logger.debug(traceback.format_exc())
        
        # Compare results
        comparison = self._compare_results(
            module_name, function_name,
            old_result, old_duration, old_error,
            new_result, new_duration, new_error
        )
        
        # Store result
        self.comparison_results.append(comparison)
        
        # Record metrics
        if self.metrics_collector:
            self._record_metrics(comparison)
        
        # Handle mismatches
        if not comparison.match:
            logger.warning(
                f"Mismatch in {module_name}.{function_name}: {comparison.mismatch_details}"
            )
            for handler in self.mismatch_handlers:
                try:
                    handler(comparison)
                except Exception as e:
                    logger.error(f"Error in mismatch handler: {e}")
    
    def _compare_results(
        self,
        module_name: str,
        function_name: str,
        old_result: Any,
        old_duration: float,
        old_error: Optional[str],
        new_result: Any,
        new_duration: float,
        new_error: Optional[str]
    ) -> ComparisonResult:
        """Compare results from old and new implementations"""
        comparison = ComparisonResult(
            module_name=module_name,
            function_name=function_name,
            timestamp=datetime.now(),
            old_result=old_result,
            new_result=new_result,
            old_duration=old_duration,
            new_duration=new_duration,
            old_error=old_error,
            new_error=new_error
        )
        
        # Check if both had errors
        if old_error and new_error:
            comparison.match = old_error == new_error
            if not comparison.match:
                comparison.mismatch_details = f"Different errors: old='{old_error}', new='{new_error}'"
            return comparison
        
        # Check if only one had error
        if old_error or new_error:
            comparison.match = False
            comparison.mismatch_details = f"Error mismatch: old_error={old_error}, new_error={new_error}"
            return comparison
        
        # Deep comparison of results
        try:
            comparison.match = self._deep_compare(old_result, new_result)
            if not comparison.match:
                comparison.mismatch_details = self._get_diff_details(old_result, new_result)
        except Exception as e:
            comparison.match = False
            comparison.mismatch_details = f"Comparison error: {str(e)}"
        
        return comparison
    
    def _deep_compare(self, obj1: Any, obj2: Any) -> bool:
        """
        Deep comparison of two objects.
        Handles common data types and structures.
        """
        # Handle None
        if obj1 is None and obj2 is None:
            return True
        if obj1 is None or obj2 is None:
            return False
        
        # Handle different types
        if type(obj1) != type(obj2):
            return False
        
        # Handle primitives
        if isinstance(obj1, (str, int, float, bool)):
            return obj1 == obj2
        
        # Handle lists
        if isinstance(obj1, list):
            if len(obj1) != len(obj2):
                return False
            return all(self._deep_compare(a, b) for a, b in zip(obj1, obj2))
        
        # Handle dicts
        if isinstance(obj1, dict):
            if set(obj1.keys()) != set(obj2.keys()):
                return False
            return all(
                self._deep_compare(obj1[key], obj2[key])
                for key in obj1.keys()
            )
        
        # Handle objects with __dict__
        if hasattr(obj1, '__dict__'):
            return self._deep_compare(obj1.__dict__, obj2.__dict__)
        
        # Default to equality
        try:
            return obj1 == obj2
        except:
            # If comparison fails, consider them different
            return False
    
    def _get_diff_details(self, obj1: Any, obj2: Any) -> str:
        """Get human-readable difference details"""
        try:
            # For simple types
            if isinstance(obj1, (str, int, float, bool)):
                return f"Values differ: '{obj1}' != '{obj2}'"
            
            # For dicts, find first difference
            if isinstance(obj1, dict) and isinstance(obj2, dict):
                for key in set(obj1.keys()) | set(obj2.keys()):
                    if key not in obj1:
                        return f"Key '{key}' missing in old result"
                    if key not in obj2:
                        return f"Key '{key}' missing in new result"
                    if obj1[key] != obj2[key]:
                        return f"Key '{key}' differs: old={obj1[key]}, new={obj2[key]}"
            
            # For lists
            if isinstance(obj1, list) and isinstance(obj2, list):
                if len(obj1) != len(obj2):
                    return f"List lengths differ: old={len(obj1)}, new={len(obj2)}"
                for i, (a, b) in enumerate(zip(obj1, obj2)):
                    if a != b:
                        return f"List item {i} differs: old={a}, new={b}"
            
            # Generic difference
            return f"Objects differ: old_type={type(obj1).__name__}, new_type={type(obj2).__name__}"
            
        except Exception as e:
            return f"Error getting diff details: {str(e)}"
    
    def _record_metrics(self, comparison: ComparisonResult):
        """Record metrics for monitoring"""
        if not self.metrics_collector:
            return
            
        # Record match/mismatch
        self.metrics_collector.increment(
            'parallel_run.comparisons',
            tags={
                'module': comparison.module_name,
                'function': comparison.function_name,
                'match': str(comparison.match).lower()
            }
        )
        
        # Record performance
        if comparison.old_duration and comparison.new_duration:
            performance_ratio = comparison.new_duration / comparison.old_duration
            self.metrics_collector.gauge(
                'parallel_run.performance_ratio',
                performance_ratio,
                tags={
                    'module': comparison.module_name,
                    'function': comparison.function_name
                }
            )
        
        # Record errors
        if comparison.old_error or comparison.new_error:
            self.metrics_collector.increment(
                'parallel_run.errors',
                tags={
                    'module': comparison.module_name,
                    'function': comparison.function_name,
                    'implementation': 'old' if comparison.old_error else 'new'
                }
            )
    
    def get_success_rate(self, module_name: Optional[str] = None) -> float:
        """Get success rate of comparisons"""
        if not self.comparison_results:
            return 100.0
            
        if module_name:
            results = [r for r in self.comparison_results if r.module_name == module_name]
        else:
            results = self.comparison_results
            
        if not results:
            return 100.0
            
        matches = sum(1 for r in results if r.match)
        return (matches / len(results)) * 100
    
    def get_performance_comparison(self, module_name: Optional[str] = None) -> Dict[str, float]:
        """Get performance comparison between old and new implementations"""
        if module_name:
            results = [r for r in self.comparison_results if r.module_name == module_name]
        else:
            results = self.comparison_results
            
        if not results:
            return {}
        
        old_times = [r.old_duration for r in results if r.old_duration]
        new_times = [r.new_duration for r in results if r.new_duration]
        
        if not old_times or not new_times:
            return {}
        
        return {
            'old_avg': sum(old_times) / len(old_times),
            'new_avg': sum(new_times) / len(new_times),
            'old_p95': sorted(old_times)[int(len(old_times) * 0.95)],
            'new_p95': sorted(new_times)[int(len(new_times) * 0.95)],
            'performance_ratio': (sum(new_times) / len(new_times)) / (sum(old_times) / len(old_times))
        }


# Global instance
parallel_runner = ParallelRunner()


# Decorator for easy parallel running
def parallel_run(module_name: str):
    """Decorator to run old and new implementations in parallel"""
    def decorator(new_func):
        async def wrapper(*args, **kwargs):
            # Get old function name
            old_func_name = f"legacy_{new_func.__name__}"
            old_func = globals().get(old_func_name)
            
            if not old_func:
                # If no legacy function, just run new
                return await new_func(*args, **kwargs) if asyncio.iscoroutinefunction(new_func) else new_func(*args, **kwargs)
            
            # Run in parallel
            return await parallel_runner.run_parallel(
                module_name,
                new_func.__name__,
                old_func,
                new_func,
                *args,
                **kwargs
            )
        return wrapper
    return decorator