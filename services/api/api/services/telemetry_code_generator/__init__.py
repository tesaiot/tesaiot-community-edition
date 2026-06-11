# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Telemetry Code Generator Package

Generates portable C code (data_telemetry.c/.h) from device JSON Schema.
The generated code is MISRA-C compliant and works on any MCU.
"""

from .type_mapper import TypeMapper, CType, CFieldInfo
from .generator import TelemetryCodeGenerator, generate_telemetry_code, add_telemetry_files_to_zip

__all__ = [
    'TypeMapper',
    'CType',
    'CFieldInfo',
    'TelemetryCodeGenerator',
    'generate_telemetry_code',
    'add_telemetry_files_to_zip'
]

__version__ = '1.0.0'
