# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Performance optimizer - CE stub.

The full optimizer relied on pandas/numpy/psutil for heavyweight analytics
workloads that are out of scope for the Community Edition. The in-scope
Dashboard module only references the ``performance_optimizer`` singleton (and
its optional decorators), so this stub provides pass-through decorators and a
small in-process cache helper without any heavy dependencies.
"""

import logging
from functools import wraps

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """No-op performance optimizer with pass-through decorators."""

    def cached(self, *dargs, **dkwargs):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        # Support both @optimizer.cached and @optimizer.cached(ttl=...)
        if len(dargs) == 1 and callable(dargs[0]) and not dkwargs:
            return decorator(dargs[0])
        return decorator

    # Common aliases used across the codebase resolve to the same no-op.
    optimize = cached
    measure = cached
    profile = cached

    def __getattr__(self, _name):
        # Any other attribute access returns a pass-through decorator/callable.
        def _passthrough(*args, **kwargs):
            if len(args) == 1 and callable(args[0]) and not kwargs:
                return args[0]
            def decorator(func):
                @wraps(func)
                def wrapper(*a, **k):
                    return func(*a, **k)
                return wrapper
            return decorator
        return _passthrough


performance_optimizer = PerformanceOptimizer()
