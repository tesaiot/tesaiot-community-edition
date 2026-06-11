# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Telemetry Code Generator Service

Generates portable C code from device JSON Schema.
The generated code is MISRA-C compliant and works on any MCU.

Usage:
    generator = TelemetryCodeGenerator()
    header, source, readme = generator.generate(device_id, device_name, schema)
"""

import os
import logging
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .type_mapper import TypeMapper, CFieldInfo, CType

logger = logging.getLogger(__name__)


class TelemetryCodeGenerator:
    """
    Generates data_telemetry.c/.h from JSON Schema.

    Features:
    - Maps JSON Schema types to portable C types
    - Generates validation code for constraints
    - Creates JSON serialization without dynamic allocation
    - MISRA-C:2012 compliant output
    """

    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the code generator.

        Args:
            template_dir: Directory containing Jinja2 templates.
                         Defaults to templates/ subdirectory.
        """
        if template_dir is None:
            template_dir = os.path.join(
                os.path.dirname(__file__), 'templates'
            )

        self.template_dir = template_dir
        self.type_mapper = TypeMapper()

        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Add custom filters
        self.jinja_env.filters['upper'] = str.upper
        self.jinja_env.filters['lower'] = str.lower

    def generate(self, device_id: str, device_name: str,
                 schema: Dict[str, Any]) -> Tuple[str, str, str]:
        """
        Generate C code files from JSON Schema.

        Args:
            device_id: Device UUID
            device_name: Human-readable device name
            schema: JSON Schema dictionary

        Returns:
            Tuple of (header_content, source_content, readme_content)
        """
        logger.info(f"Generating telemetry code for device: {device_id}")

        # Parse schema and map types
        fields = self._parse_schema(schema)

        # Calculate max JSON size estimate
        max_json_size = self._estimate_json_size(fields)

        # Get schema version
        schema_version = schema.get('version',
                                    schema.get('$schema_version', '1.0'))

        # Get required fields list
        required_fields = [f for f in fields if f.is_required]
        optional_fields = [f for f in fields if not f.is_required]

        # Prepare template context
        context = {
            'device_id': device_id,
            'device_name': self._sanitize_device_name(device_name),
            'schema_version': schema_version,
            'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'fields': fields,
            'max_json_size': max_json_size,
            'required_fields': required_fields,
            'optional_fields': optional_fields,
            'field_count': len(fields),
        }

        # Render templates
        try:
            header = self.jinja_env.get_template('data_telemetry.h.j2').render(context)
            source = self.jinja_env.get_template('data_telemetry.c.j2').render(context)
            readme = self.jinja_env.get_template('README.md.j2').render(context)
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            raise

        logger.info(f"Generated {len(fields)} fields for device {device_id}")

        return header, source, readme

    def generate_default_template(self, device_id: str,
                                  device_name: str) -> Tuple[str, str, str]:
        """
        Generate a default template when device has no schema.

        Includes TODO comments for developers to fill in.

        Args:
            device_id: Device UUID
            device_name: Human-readable device name

        Returns:
            Tuple of (header_content, source_content, readme_content)
        """
        # Create a minimal default schema
        default_schema = {
            "type": "object",
            "version": "1.0",
            "properties": {
                "value": {
                    "type": "number",
                    "title": "Sensor Value (TODO: customize)",
                    "description": "Replace with your actual sensor data"
                },
                "timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "title": "Timestamp"
                }
            },
            "required": ["timestamp"]
        }

        return self.generate(device_id, device_name, default_schema)

    def _parse_schema(self, schema: Dict[str, Any]) -> List[CFieldInfo]:
        """
        Parse JSON Schema and return list of C field info.

        Args:
            schema: JSON Schema dictionary

        Returns:
            List of CFieldInfo sorted by (required, name)
        """
        return self.type_mapper.map_schema(schema)

    def _estimate_json_size(self, fields: List[CFieldInfo]) -> int:
        """
        Estimate maximum JSON output size.

        Calculates a safe buffer size for the JSON output based on
        field types and sizes.

        Args:
            fields: List of CFieldInfo

        Returns:
            Estimated maximum JSON size in bytes
        """
        size = 2  # {}

        for field in fields:
            # Field name with quotes and colon: "name":
            size += len(field.name) + 4

            if field.c_type == CType.CHAR_ARRAY:
                # String with quotes: "value"
                size += (field.array_size or 64) + 2
            elif field.c_type in (CType.FLOAT, CType.DOUBLE):
                # Float: -123456789.123456
                size += 20
            elif field.c_type == CType.BOOL:
                # Boolean: false
                size += 5
            elif 'int64' in field.c_type.value.lower():
                # 64-bit integer: -9223372036854775808
                size += 21
            else:
                # 32-bit integer: -2147483648
                size += 12

            # Comma separator
            size += 1

        # Add 20% safety margin and round up to nearest 64
        size = int(size * 1.2)
        size = ((size + 63) // 64) * 64

        # Minimum 256, maximum 4096
        return max(256, min(size, 4096))

    def _sanitize_device_name(self, name: str) -> str:
        """
        Sanitize device name for use in C comments.

        Removes characters that could break C comments.

        Args:
            name: Raw device name

        Returns:
            Sanitized name safe for C comments
        """
        # Remove characters that could break comments
        safe_name = name.replace('*/', '').replace('/*', '')
        safe_name = safe_name.replace('\n', ' ').replace('\r', '')
        return safe_name[:64]  # Limit length


def generate_telemetry_code(device_id: str, device_name: str,
                            schema: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Convenience function to generate telemetry code.

    Args:
        device_id: Device UUID
        device_name: Human-readable device name
        schema: JSON Schema dictionary

    Returns:
        Tuple of (header_content, source_content, readme_content)
    """
    generator = TelemetryCodeGenerator()
    return generator.generate(device_id, device_name, schema)


def add_telemetry_files_to_zip(zip_file, device: Dict[str, Any],
                                folder_prefix: str = 'telemetry') -> bool:
    """
    Add telemetry C code files to an existing ZIP file.

    This helper function generates data_telemetry.c/.h from the device's
    telemetrySchema and adds them to the provided ZIP file.

    Args:
        zip_file: Open zipfile.ZipFile object (write mode)
        device: Device document from MongoDB containing:
            - device_id: Device UUID
            - name: Device name
            - telemetrySchema: JSON Schema for telemetry (optional)
        folder_prefix: Folder name in ZIP for telemetry files

    Returns:
        True if files were added successfully, False if no schema or error

    Usage in bundle generators:
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add certificate files...
            add_telemetry_files_to_zip(zf, device)
    """
    try:
        device_id = device.get('device_id') or str(device.get('_id', 'unknown'))
        device_name = device.get('name', device_id)

        # Get telemetry schema from device
        telemetry_schema = device.get('telemetrySchema')

        # Check if schema exists and has properties
        if not telemetry_schema:
            logger.debug(f"Device {device_id} has no telemetrySchema - using default template")
            generator = TelemetryCodeGenerator()
            header, source, readme = generator.generate_default_template(device_id, device_name)
        else:
            # Extract the schema definition
            # Schema can be in telemetrySchema directly or nested under 'schema' key
            schema_def = telemetry_schema.get('schema', telemetry_schema)

            if not schema_def.get('properties'):
                logger.debug(f"Device {device_id} telemetrySchema has no properties - using default")
                generator = TelemetryCodeGenerator()
                header, source, readme = generator.generate_default_template(device_id, device_name)
            else:
                # Generate code from actual schema
                generator = TelemetryCodeGenerator()
                header, source, readme = generator.generate(device_id, device_name, schema_def)

        # Add files to zip
        zip_file.writestr(f'{folder_prefix}/data_telemetry.h', header)
        zip_file.writestr(f'{folder_prefix}/data_telemetry.c', source)
        zip_file.writestr(f'{folder_prefix}/README.md', readme)

        logger.info(f"Added telemetry files to bundle for device {device_id}")
        return True

    except Exception as e:
        logger.warning(f"Failed to add telemetry files for device {device.get('device_id', 'unknown')}: {e}")
        return False
