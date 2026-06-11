# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Modularization metrics - CE stub.

The full platform tracks internal modularization/rollout self-metrics. That
introspection is not part of the eight in-scope CE capabilities, so this stub
records nothing and returns empty, well-formed payloads. The dashboard
endpoints and the metrics decorator that reference it already degrade
gracefully.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ModularizationMetrics:
    """No-op modularization metrics collector for the Community Edition."""

    def track_method_execution(self, *args, **kwargs):
        return None

    def get_modularization_dashboard(self, *args, **kwargs):
        return {
            "available": False,
            "services": [],
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_historical_metrics(self, *args, **kwargs):
        return {"available": False, "history": []}

    def save_metrics_snapshot(self, *args, **kwargs):
        return None


modularization_metrics = ModularizationMetrics()
