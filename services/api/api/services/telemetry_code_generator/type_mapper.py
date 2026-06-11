# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
JSON Schema to C Type Mapper

Maps JSON Schema types to appropriate C types based on constraints.
Follows MISRA-C guidelines for portable embedded code.

References:
- json_schema_to_c: https://github.com/badicsalex/json_schema_to_c
- MISRA-C:2012: https://misra.org.uk/
- CERT-C: https://wiki.sei.cmu.edu/confluence/display/c
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum
import re


class CType(Enum):
    """Supported C types for telemetry fields (portable, fixed-width)"""
    UINT8 = "uint8_t"
    UINT16 = "uint16_t"
    UINT32 = "uint32_t"
    UINT64 = "uint64_t"
    INT8 = "int8_t"
    INT16 = "int16_t"
    INT32 = "int32_t"
    INT64 = "int64_t"
    FLOAT = "float"
    DOUBLE = "double"
    BOOL = "bool"
    CHAR_ARRAY = "char[]"
    STRUCT = "struct"


@dataclass
class CFieldInfo:
    """
    C field information derived from JSON Schema property.

    Attributes:
        name: Field name (C identifier safe)
        c_type: The C type to use
        array_size: Size for arrays/strings (includes null terminator for strings)
        is_required: Whether field is in JSON Schema 'required' array
        min_value: Minimum value constraint
        max_value: Maximum value constraint
        description: Human-readable description from schema
        default_value: Default value as C literal
        enum_values: List of allowed enum values
        nested_fields: For struct types, list of nested CFieldInfo
    """
    name: str
    c_type: CType
    array_size: Optional[int] = None
    is_required: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: Optional[str] = None
    default_value: Optional[str] = None
    enum_values: Optional[List[Any]] = None
    nested_fields: Optional[List['CFieldInfo']] = None

    def get_c_type_string(self) -> str:
        """Get the full C type declaration string"""
        if self.c_type == CType.CHAR_ARRAY:
            return f"char"
        return self.c_type.value

    def get_declaration(self) -> str:
        """Get the full field declaration for C struct"""
        if self.c_type == CType.CHAR_ARRAY:
            return f"char {self.name}[{self.array_size}]"
        elif self.array_size is not None and self.c_type != CType.STRUCT:
            return f"{self.c_type.value} {self.name}[{self.array_size}]"
        else:
            return f"{self.c_type.value} {self.name}"


class TypeMapper:
    """
    Maps JSON Schema properties to C types.

    Design principles:
    - No dynamic allocation (fixed-size arrays)
    - Portable types (stdint.h)
    - MISRA-C compliant naming
    """

    # String format to array size mapping (includes null terminator)
    STRING_FORMAT_SIZES = {
        "date-time": 32,     # ISO 8601: 2025-12-13T12:00:00.000Z
        "date": 12,          # 2025-12-13
        "time": 16,          # 12:00:00.000Z
        "uuid": 40,          # UUID with dashes + null
        "email": 64,
        "uri": 128,
        "hostname": 64,
        "ipv4": 16,
        "ipv6": 46,
    }

    DEFAULT_STRING_SIZE = 64
    DEFAULT_ARRAY_SIZE = 16
    MAX_STRING_SIZE = 256
    MAX_ARRAY_SIZE = 64

    def __init__(self):
        """Initialize the type mapper"""
        self._c_keyword_set = {
            'auto', 'break', 'case', 'char', 'const', 'continue', 'default',
            'do', 'double', 'else', 'enum', 'extern', 'float', 'for', 'goto',
            'if', 'int', 'long', 'register', 'return', 'short', 'signed',
            'sizeof', 'static', 'struct', 'switch', 'typedef', 'union',
            'unsigned', 'void', 'volatile', 'while', 'inline', 'restrict',
            '_Bool', '_Complex', '_Imaginary', 'bool', 'true', 'false'
        }

    def sanitize_name(self, name: str) -> str:
        """
        Convert JSON property name to valid C identifier.

        Rules:
        - Replace invalid characters with underscore
        - Ensure starts with letter or underscore
        - Avoid C keywords
        """
        # Replace non-alphanumeric (except underscore) with underscore
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)

        # Ensure starts with letter or underscore
        if safe_name and safe_name[0].isdigit():
            safe_name = '_' + safe_name

        # Avoid C keywords
        if safe_name.lower() in self._c_keyword_set:
            safe_name = safe_name + '_field'

        return safe_name

    def map_schema(self, schema: Dict[str, Any]) -> List[CFieldInfo]:
        """
        Map entire JSON Schema to list of CFieldInfo.

        Args:
            schema: JSON Schema dictionary with 'properties' and 'required'

        Returns:
            List of CFieldInfo for each property
        """
        properties = schema.get('properties', {})
        required = schema.get('required', [])

        fields = []
        for name, prop_schema in properties.items():
            field_info = self.map_field(name, prop_schema, required)
            fields.append(field_info)

        # Sort: required fields first, then alphabetically
        fields.sort(key=lambda f: (not f.is_required, f.name))

        return fields

    def map_field(self, name: str, schema: Dict[str, Any],
                  required_fields: List[str]) -> CFieldInfo:
        """
        Map a single JSON Schema property to CFieldInfo.

        Args:
            name: Property name from JSON Schema
            schema: Property schema definition
            required_fields: List of required field names

        Returns:
            CFieldInfo with appropriate C type mapping
        """
        safe_name = self.sanitize_name(name)
        json_type = schema.get('type', 'string')
        is_required = name in required_fields

        if json_type == 'integer':
            return self._map_integer(safe_name, schema, is_required)
        elif json_type == 'number':
            return self._map_number(safe_name, schema, is_required)
        elif json_type == 'boolean':
            return self._map_boolean(safe_name, schema, is_required)
        elif json_type == 'string':
            return self._map_string(safe_name, schema, is_required)
        elif json_type == 'array':
            return self._map_array(safe_name, schema, is_required)
        elif json_type == 'object':
            return self._map_object(safe_name, schema, is_required)
        else:
            # Default to string for unknown types
            return self._map_string(safe_name, schema, is_required)

    def _map_integer(self, name: str, schema: Dict[str, Any],
                     is_required: bool) -> CFieldInfo:
        """
        Map integer type based on min/max constraints.

        Selection logic:
        - If min >= 0: use unsigned type
        - Choose smallest type that fits the range
        """
        min_val = schema.get('minimum')
        max_val = schema.get('maximum')

        # Check for enum (use smallest type that fits)
        enum_values = schema.get('enum')
        if enum_values:
            max_val = max(enum_values) if max_val is None else max(max_val, max(enum_values))
            min_val = min(enum_values) if min_val is None else min(min_val, min(enum_values))

        # Determine appropriate C type based on range
        c_type = self._select_int_type(min_val, max_val)

        # Determine default value
        default_value = "0"
        if enum_values and len(enum_values) > 0:
            default_value = str(enum_values[0])

        return CFieldInfo(
            name=name,
            c_type=c_type,
            is_required=is_required,
            min_value=min_val,
            max_value=max_val,
            description=schema.get('title') or schema.get('description'),
            default_value=default_value,
            enum_values=enum_values
        )

    def _select_int_type(self, min_val: Optional[float],
                         max_val: Optional[float]) -> CType:
        """Select the smallest integer type that fits the range"""
        if min_val is not None and min_val >= 0:
            # Unsigned types
            if max_val is not None:
                if max_val <= 255:
                    return CType.UINT8
                elif max_val <= 65535:
                    return CType.UINT16
                elif max_val <= 4294967295:
                    return CType.UINT32
                else:
                    return CType.UINT64
            return CType.UINT32
        else:
            # Signed types
            if min_val is not None and max_val is not None:
                if min_val >= -128 and max_val <= 127:
                    return CType.INT8
                elif min_val >= -32768 and max_val <= 32767:
                    return CType.INT16
                elif min_val >= -2147483648 and max_val <= 2147483647:
                    return CType.INT32
                else:
                    return CType.INT64
            return CType.INT32

    def _map_number(self, name: str, schema: Dict[str, Any],
                    is_required: bool) -> CFieldInfo:
        """
        Map number (float/double) type.

        Uses float by default, double only for very large ranges.
        """
        min_val = schema.get('minimum')
        max_val = schema.get('maximum')

        # Check if double precision is needed
        needs_double = False
        float_max = 3.4028235e+38

        if min_val is not None and (min_val < -float_max or min_val > float_max):
            needs_double = True
        if max_val is not None and (max_val < -float_max or max_val > float_max):
            needs_double = True

        c_type = CType.DOUBLE if needs_double else CType.FLOAT
        default_suffix = "" if needs_double else "f"

        return CFieldInfo(
            name=name,
            c_type=c_type,
            is_required=is_required,
            min_value=min_val,
            max_value=max_val,
            description=schema.get('title') or schema.get('description'),
            default_value=f"0.0{default_suffix}"
        )

    def _map_boolean(self, name: str, schema: Dict[str, Any],
                     is_required: bool) -> CFieldInfo:
        """Map boolean type to C bool (requires stdbool.h)"""
        return CFieldInfo(
            name=name,
            c_type=CType.BOOL,
            is_required=is_required,
            description=schema.get('title') or schema.get('description'),
            default_value="false"
        )

    def _map_string(self, name: str, schema: Dict[str, Any],
                    is_required: bool) -> CFieldInfo:
        """
        Map string type to fixed-size char array.

        Size selection:
        1. Use maxLength if specified
        2. Use format-specific size (datetime, uuid, etc.)
        3. Fall back to default size
        """
        # Determine array size
        max_length = schema.get('maxLength')
        str_format = schema.get('format')

        if max_length:
            # Add 1 for null terminator
            array_size = min(max_length + 1, self.MAX_STRING_SIZE)
        elif str_format and str_format in self.STRING_FORMAT_SIZES:
            array_size = self.STRING_FORMAT_SIZES[str_format]
        else:
            array_size = self.DEFAULT_STRING_SIZE

        return CFieldInfo(
            name=name,
            c_type=CType.CHAR_ARRAY,
            array_size=array_size,
            is_required=is_required,
            description=schema.get('title') or schema.get('description'),
            default_value='""',
            enum_values=schema.get('enum')
        )

    def _map_array(self, name: str, schema: Dict[str, Any],
                   is_required: bool) -> CFieldInfo:
        """
        Map array type to fixed-size C array.

        Note: Uses maxItems or default size. Includes count field.
        """
        items = schema.get('items', {})
        max_items = schema.get('maxItems', self.DEFAULT_ARRAY_SIZE)
        max_items = min(max_items, self.MAX_ARRAY_SIZE)

        # Get the item type
        item_type = items.get('type', 'integer')

        if item_type == 'string':
            # Array of strings - use char[MAX_ITEMS][STRING_SIZE]
            # This is more complex, for now use STRUCT
            return CFieldInfo(
                name=name,
                c_type=CType.STRUCT,
                array_size=max_items,
                is_required=is_required,
                description=schema.get('title') or schema.get('description')
            )

        # Map item type
        item_field = self.map_field(f"{name}_item", items, [])

        return CFieldInfo(
            name=name,
            c_type=item_field.c_type,
            array_size=max_items,
            is_required=is_required,
            min_value=item_field.min_value,
            max_value=item_field.max_value,
            description=schema.get('title') or schema.get('description')
        )

    def _map_object(self, name: str, schema: Dict[str, Any],
                    is_required: bool) -> CFieldInfo:
        """
        Map nested object type to C struct.

        Recursively maps nested properties.
        """
        nested_fields = None
        properties = schema.get('properties')

        if properties:
            required = schema.get('required', [])
            nested_fields = []
            for prop_name, prop_schema in properties.items():
                nested_field = self.map_field(prop_name, prop_schema, required)
                nested_fields.append(nested_field)

        return CFieldInfo(
            name=name,
            c_type=CType.STRUCT,
            is_required=is_required,
            description=schema.get('title') or schema.get('description'),
            nested_fields=nested_fields
        )
