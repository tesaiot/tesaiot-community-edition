# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""Common utilities module for TESA IoT Platform"""

from .utils import get_client_info, validate_request_data

__all__ = ['get_client_info', 'validate_request_data']
