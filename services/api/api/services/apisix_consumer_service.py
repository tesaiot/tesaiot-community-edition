# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
APISIX Consumer Service -- DISABLED / NOT WIRED in the Community Edition.

WHY THIS EXISTS BUT DOES NOTHING
--------------------------------
This module was written for an APISIX deployment backed by **etcd**, where the
Admin API (``PUT /apisix/admin/consumers/<name>``) can register a new consumer
(key-auth credential + per-consumer ``limit-req``) at runtime -- i.e. one APISIX
consumer per device, giving genuinely per-device rate limiting at the gateway.

The Community Edition does NOT run APISIX that way. It runs APISIX in
**standalone YAML mode**:

  * docker-compose.yml ......... ``APISIX_STAND_ALONE: "true"``
  * config/apisix/config.yaml .. ``deployment.role_data_plane.config_provider: yaml``
  * config/apisix/apisix.yaml .. mounted read-only (``:ro``)

In standalone YAML mode APISIX loads all routes / ssls / consumers from
``apisix.yaml`` at boot and the **Admin API does not mutate runtime state** --
``PUT /apisix/admin/consumers/...`` does not create a usable consumer, and the
config file is mounted read-only so it cannot be rewritten at runtime either.
There is therefore NO supported way to register a per-device consumer
dynamically in this topology.

Accordingly:

  * This service has **no callers** anywhere in the codebase (it is dead code).
  * The real device-API-key lifecycle lives in ``api_key_service.py`` and
    ``device_api_key.py``; those keys are validated by the API backend itself,
    not by an APISIX consumer.
  * Rate limiting that IS real in the CE is **route-level** ``limit-req`` on the
    telemetry routes in ``config/apisix/apisix.yaml`` (shared across callers of
    that route), plus the backend's own per-key limits.

DO NOT import or call this module expecting it to work. It is retained only as
a stub so that:
  (a) the false "per-consumer rate limiting via dynamic Admin-API consumers"
      claim is documented as NOT applicable to the standalone CE, and
  (b) anyone running APISIX with an etcd control plane (out of scope for the
      CE) has a documented starting point.

If you migrate to an etcd-backed APISIX and want per-device consumers, restore
this module from version control history and wire create/revoke into
``api_key_service.generate_device_api_key`` / ``revoke_device_api_key`` -- and
update ``config/apisix/README.md`` to match. Until then, importing this module
raises, so it cannot be wired in by accident in standalone mode.
"""

import logging

logger = logging.getLogger(__name__)

# Guard message reused by the import-time error and any runtime access.
_UNSUPPORTED_MSG = (
    "APISIXConsumerService is disabled: the Community Edition runs APISIX in "
    "standalone YAML mode (no etcd), where the Admin API cannot register "
    "per-device consumers at runtime. Device API keys are managed by "
    "api_key_service.py and validated by the API backend; gateway rate "
    "limiting is route-level (config/apisix/apisix.yaml)."
)


class APISIXConsumerServiceUnavailable(RuntimeError):
    """Raised if code tries to use the disabled APISIX consumer service."""


class APISIXConsumerService:
    """Inert placeholder. Instantiation fails loud rather than silently no-op.

    Fail-closed: we refuse to pretend per-consumer gateway rate limiting exists
    in standalone mode. Anyone wiring this in will get an explicit error instead
    of a false sense of enforcement.
    """

    def __init__(self, *args, **kwargs):
        logger.warning(_UNSUPPORTED_MSG)
        raise APISIXConsumerServiceUnavailable(_UNSUPPORTED_MSG)


# NOTE: intentionally NO module-level singleton instance. The previous version
# created ``apisix_consumer_service = APISIXConsumerService()`` at import time;
# that both ran dead code and implied the feature was live. It is removed so the
# claim stays honest and nothing imports a working-looking object by accident.
