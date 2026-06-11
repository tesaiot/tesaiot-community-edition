# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Rust analytics bridge - CE stub.

The full platform offloads heavyweight analytics to an external Rust service.
That accelerator is out of scope for the single-organization Community Edition,
so this module advertises the bridge as unavailable. Callers already guard on
``is_analytics_available()`` and fall back to native Python paths.
"""

import logging

logger = logging.getLogger(__name__)


def is_analytics_available() -> bool:
    """The Rust analytics accelerator is not bundled in the Community Edition."""
    return False


def get_analytics_metrics_rust(*args, **kwargs):
    """No-op fallback; returns an empty metrics payload."""
    return {}
