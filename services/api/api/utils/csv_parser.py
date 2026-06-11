# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
CSV Parser for Device Bulk Import
Supports Trust M UID validation and parsing
"""

import csv
import io
import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CSVParserError(Exception):
    """CSV parsing error"""
    def __init__(self, message: str, row: int = None, field: str = None):
        self.message = message
        self.row = row
        self.field = field
        super().__init__(self.message)


class TrustMCSVParser:
    """
    Parser for CSV files containing Trust M device pre-registration data.

    Expected CSV Format:
    device_id,name,type,auth_mode,trustm_uid,location_name,description

    Example:
    PSoC-E84-001,Assembly Line Sensor,sensor,mtls,cdcd000800140035004e00540054004e003400310031003200320041,Factory Floor,Production monitoring
    """

    REQUIRED_FIELDS = ['device_id', 'name', 'type', 'auth_mode']
    OPTIONAL_FIELDS = ['trustm_uid', 'location_name', 'latitude', 'longitude', 'description',
                      'manufacturer', 'model', 'network_type', 'firmware_version']
    VALID_TYPES = ['sensor', 'actuator', 'gateway', 'controller']
    VALID_AUTH_MODES = ['mtls', 'server_tls']
    VALID_NETWORK_TYPES = ['nbiot', 'lorawan', 'wifi', 'cellular', 'bluetooth', 'zigbee']

    # Trust M UID: 27 bytes = 54 hex characters
    TRUSTM_UID_PATTERN = re.compile(r'^[0-9a-fA-F]{54}$')

    @staticmethod
    def validate_trustm_uid(uid: str) -> bool:
        """
        Validate Trust M UID format.
        Must be exactly 54 hexadecimal characters (27 bytes).
        """
        if not uid:
            return False
        return TrustMCSVParser.TRUSTM_UID_PATTERN.match(uid) is not None

    @staticmethod
    def parse_csv_string(csv_content: str) -> List[Dict[str, Any]]:
        """
        Parse CSV string content into device list.

        Args:
            csv_content: CSV file content as string

        Returns:
            List of device dictionaries

        Raises:
            CSVParserError: If CSV format is invalid
        """
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            devices = []
            errors = []

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                try:
                    device = TrustMCSVParser._parse_row(row, row_num)
                    devices.append(device)
                except CSVParserError as e:
                    errors.append(f"Row {row_num}: {e.message}")
                    logger.warning(f"CSV parse error at row {row_num}: {e.message}")

            if errors and not devices:
                raise CSVParserError(f"All rows failed validation:\n" + "\n".join(errors))

            return devices

        except csv.Error as e:
            raise CSVParserError(f"Invalid CSV format: {str(e)}")

    @staticmethod
    def _parse_row(row: Dict[str, str], row_num: int) -> Dict[str, Any]:
        """
        Parse a single CSV row into device dictionary.

        Args:
            row: CSV row as dictionary
            row_num: Row number for error reporting

        Returns:
            Device dictionary

        Raises:
            CSVParserError: If row validation fails
        """
        # Validate required fields
        for field in TrustMCSVParser.REQUIRED_FIELDS:
            if not row.get(field) or not row[field].strip():
                raise CSVParserError(
                    f"Missing required field: {field}",
                    row=row_num,
                    field=field
                )

        device_id = row['device_id'].strip()
        name = row['name'].strip()
        device_type = row['type'].strip().lower()
        auth_mode = row['auth_mode'].strip().lower()

        # Validate device type
        if device_type not in TrustMCSVParser.VALID_TYPES:
            raise CSVParserError(
                f"Invalid device type: {device_type}. Must be one of: {', '.join(TrustMCSVParser.VALID_TYPES)}",
                row=row_num,
                field='type'
            )

        # Validate auth mode
        if auth_mode not in TrustMCSVParser.VALID_AUTH_MODES:
            raise CSVParserError(
                f"Invalid auth_mode: {auth_mode}. Must be one of: {', '.join(TrustMCSVParser.VALID_AUTH_MODES)}",
                row=row_num,
                field='auth_mode'
            )

        # Build device object
        device = {
            'device_id': device_id,
            'name': name,
            'type': device_type,
            'auth_mode': auth_mode,
            'status': 'awaiting_first_connection',  # For Trust M devices
            'metadata': {}
        }

        # Parse Trust M UID (optional but validated if present)
        trustm_uid = row.get('trustm_uid', '').strip()
        if trustm_uid:
            if not TrustMCSVParser.validate_trustm_uid(trustm_uid):
                raise CSVParserError(
                    f"Invalid Trust M UID format. Must be 54 hexadecimal characters. Got: {trustm_uid}",
                    row=row_num,
                    field='trustm_uid'
                )
            device['trustm_uid'] = trustm_uid

        # Parse location
        location_name = row.get('location_name', '').strip()
        if location_name:
            device['location'] = {'name': location_name}

            # Add coordinates if provided
            try:
                lat = row.get('latitude', '').strip()
                lng = row.get('longitude', '').strip()
                if lat and lng:
                    device['location']['latitude'] = float(lat)
                    device['location']['longitude'] = float(lng)
            except ValueError as e:
                logger.warning(f"Row {row_num}: Invalid coordinates, skipping: {e}")

        # Parse optional metadata fields
        desc = row.get('description', '').strip()
        if desc:
            device['description'] = desc

        manufacturer = row.get('manufacturer', '').strip()
        if manufacturer:
            device['metadata']['manufacturer'] = manufacturer

        model = row.get('model', '').strip()
        if model:
            device['metadata']['model'] = model

        network_type = row.get('network_type', '').strip().lower()
        if network_type:
            if network_type not in TrustMCSVParser.VALID_NETWORK_TYPES:
                logger.warning(f"Row {row_num}: Unknown network_type '{network_type}', using anyway")
            device['metadata']['network_type'] = network_type

        firmware_version = row.get('firmware_version', '').strip()
        if firmware_version:
            device['firmwareVersion'] = firmware_version

        return device

    @staticmethod
    def generate_template_csv() -> str:
        """
        Generate a CSV template file with example data.

        Returns:
            CSV template as string
        """
        template = io.StringIO()
        writer = csv.DictWriter(template, fieldnames=[
            'device_id', 'name', 'type', 'auth_mode', 'trustm_uid',
            'location_name', 'latitude', 'longitude', 'description',
            'manufacturer', 'model', 'network_type', 'firmware_version'
        ])

        writer.writeheader()
        writer.writerow({
            'device_id': 'PSoC-E84-001',
            'name': 'Assembly Line Sensor',
            'type': 'sensor',
            'auth_mode': 'mtls',
            'trustm_uid': 'cdcd000800140035004e00540054004e003400310031003200320041',
            'location_name': 'Factory Floor',
            'latitude': '13.7563',
            'longitude': '100.5018',
            'description': 'Production line monitoring device',
            'manufacturer': 'Infineon',
            'model': 'PSoC Edge E84',
            'network_type': 'wifi',
            'firmware_version': '1.0.0'
        })
        writer.writerow({
            'device_id': 'PSoC-E84-002',
            'name': 'Temperature Controller',
            'type': 'controller',
            'auth_mode': 'mtls',
            'trustm_uid': 'cdcd000800140035004e00540054004e003400310031003200330042',
            'location_name': 'Warehouse',
            'latitude': '',
            'longitude': '',
            'description': 'HVAC temperature control',
            'manufacturer': 'Infineon',
            'model': 'PSoC Edge E84',
            'network_type': 'wifi',
            'firmware_version': '1.0.0'
        })

        return template.getvalue()

    @staticmethod
    def validate_csv_file(csv_content: str) -> Dict[str, Any]:
        """
        Validate CSV file and return validation results.

        Args:
            csv_content: CSV file content

        Returns:
            Validation result dictionary with:
            - valid: bool
            - errors: List of error messages
            - warnings: List of warning messages
            - device_count: Number of valid devices
            - preview: First 5 devices
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'device_count': 0,
            'preview': []
        }

        try:
            devices = TrustMCSVParser.parse_csv_string(csv_content)
            result['valid'] = True
            result['device_count'] = len(devices)
            result['preview'] = devices[:5]  # First 5 for preview

            # Check for duplicate device_ids
            device_ids = [d['device_id'] for d in devices]
            duplicates = [did for did in device_ids if device_ids.count(did) > 1]
            if duplicates:
                result['warnings'].append(f"Duplicate device_ids found: {', '.join(set(duplicates))}")

            # Check for duplicate Trust M UIDs
            trustm_uids = [d.get('trustm_uid') for d in devices if d.get('trustm_uid')]
            dup_uids = [uid for uid in trustm_uids if trustm_uids.count(uid) > 1]
            if dup_uids:
                result['errors'].append(f"Duplicate Trust M UIDs found: {', '.join(set(dup_uids))}")
                result['valid'] = False

        except CSVParserError as e:
            result['errors'].append(str(e))
        except Exception as e:
            result['errors'].append(f"Unexpected error: {str(e)}")

        return result
