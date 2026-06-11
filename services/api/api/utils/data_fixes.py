# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Data Migration Utilities
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

from datetime import datetime
import uuid

def fix_user_data(data):
    """
    Fix user data to ensure all fields have proper values.
    
    Args:
        data: User data dictionary
        
    Returns:
        dict: Fixed user data
    """
    if not data:
        return {}
    
    from bson import ObjectId
    
    # Ensure required fields
    data['id'] = data.get('id', data.get('_id', ''))
    data['email'] = data.get('email', '')
    data['name'] = data.get('name') or data.get('email', '').split('@')[0]
    data['role'] = data.get('role', 'user')
    
    # Don't override organization fields if they exist
    if not data.get('organization'):
        data['organization'] = 'Default Organization'
    if not data.get('organization_id'):
        data['organization_id'] = 'default-org'
    
    # Set is_admin flag based on role
    user_role = data.get('role', 'user')
    data['is_admin'] = user_role in ['platform_admin', 'super_admin', 'organization_admin', 'admin']
    
    # Convert any ObjectId instances to strings (recursive for nested dicts)
    def clean_value(value):
        """Recursively clean values, converting ObjectId and other non-serializable types"""
        if value is None:
            return value
        elif isinstance(value, ObjectId):
            return str(value)
        elif isinstance(value, dict):
            return {k: clean_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [clean_value(item) for item in value]
        elif hasattr(value, 'value'):  # Enum types
            return value.value
        elif hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool)):
            # Other objects - convert to string
            return str(value)
        else:
            return value
    
    cleaned_data = {}
    for k, v in data.items():
        cleaned_data[k] = clean_value(v)
    
    return cleaned_data

def fix_device_data(data):
    """
    Fix device data to ensure all fields have proper values.
    
    Args:
        data: Device data dictionary or list
        
    Returns:
        dict/list: Fixed device data
    """
    if isinstance(data, list):
        return [fix_device_data(item) for item in data]
    
    if not data:
        return {}
    
    # Ensure device ID
    device_id = data.get('device_id') or data.get('_id') or data.get('id', '')
    data['device_id'] = str(device_id) if device_id else ''
    data['id'] = data['device_id']  # Ensure both fields exist
    
    # Ensure UUID exists and is different from device_id
    if not data.get('uuid') or data.get('uuid') == data.get('device_id'):
        data['uuid'] = str(uuid.uuid4())
    
    # Ensure required fields
    data['name'] = data.get('name') or f"Device-{data['device_id'][:8]}"
    data['type'] = data.get('type', 'sensor')
    data['status'] = data.get('status', 'active')
    
    # Ensure auth_mode field (map from auth_type if needed)
    if 'auth_mode' not in data and 'auth_type' in data:
        # Map auth_type to auth_mode
        auth_type = data['auth_type']
        if auth_type == 'api_key':
            data['auth_mode'] = 'server_tls'
        elif auth_type == 'certificate':
            data['auth_mode'] = 'mtls'
        else:
            data['auth_mode'] = auth_type
    elif 'auth_mode' not in data:
        data['auth_mode'] = 'mtls'  # Default to mtls for security
    
    # Set certificate_status for server_tls devices
    if data.get('auth_mode') == 'server_tls':
        data['certificate_status'] = 'ca_only'
    
    # Ensure tags field exists
    if 'tags' not in data:
        data['tags'] = []
    elif not isinstance(data.get('tags'), list):
        data['tags'] = []
    
    # Fix organization_id - convert ObjectId to string
    from bson import ObjectId
    org_id = data.get('organization_id')
    if isinstance(org_id, ObjectId):
        data['organization_id'] = str(org_id)
    elif not org_id:
        data['organization_id'] = 'default-org'
    
    # Fix metadata
    if 'metadata' not in data or not data['metadata']:
        data['metadata'] = {}
    
    # Preserve certificate_algorithm
    if 'certificate_algorithm' in data and data['certificate_algorithm']:
        # Ensure it's also in metadata for backward compatibility
        data['metadata']['certificate_algorithm'] = data['certificate_algorithm']
    elif data.get('metadata', {}).get('certificate_algorithm'):
        # If only in metadata, copy to top level
        data['certificate_algorithm'] = data['metadata']['certificate_algorithm']
    
    # Preserve CSR-related fields - CRITICAL for CSR device detection
    # Preserve Trust M UID - CRITICAL for Trust M device detection
    csr_fields = ['certificate_generation_method', 'generation_method', 'csr_provided', 'certificate_csr', 'trustm_uid']
    for field in csr_fields:
        if field in data:
            # Preserve the field at top level
            pass  # Already exists, don't override
        
    # Also ensure metadata has certificate_generation_method if it exists at top level
    if data.get('certificate_generation_method'):
        data['metadata']['certificate_generation_method'] = data.get('certificate_generation_method')
    elif data.get('generation_method'):
        # Map generation_method to certificate_generation_method for consistency
        data['certificate_generation_method'] = data.get('generation_method')
        data['metadata']['certificate_generation_method'] = data.get('generation_method')
    
    # Populate device public key data and encryption status if missing
    if not data.get('key_encryption_enabled'):
        try:
            # Import here to avoid circular imports
            from ..core.database import get_db
            db = get_db()
            device_pk_record = db.device_public_keys.find_one({
                'device_id': data.get('device_id')
            })
            if device_pk_record:
                # Update device_public_key if it's missing or incomplete
                if not data.get('device_public_key') or not data.get('device_public_key', {}).get('key'):
                    data['device_public_key'] = {
                        'key': device_pk_record.get('public_key_pem'),
                        'algorithm': device_pk_record.get('key_algorithm'),
                        'status': device_pk_record.get('status'),
                        'uploaded_at': device_pk_record.get('registered_at')
                    }
                # Enable encryption if public key exists
                data['key_encryption_enabled'] = True
        except Exception:
            # Silently fail if database connection fails
            # This prevents breaking device display when database is unavailable
            pass
    
    # Fix timestamps (normalize to ISO8601 with UTC offset)
    from datetime import timezone as _tz
    for field in ['created_at', 'updated_at', 'last_seen', 'last_telemetry']:
        if field in data and data[field]:
            if isinstance(data[field], str):
                try:
                    # Parse incoming string (treat missing tz as UTC)
                    raw = str(data[field])
                    dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=_tz.utc)
                    data[field] = dt.astimezone(_tz.utc).isoformat()
                except:
                    data[field] = datetime.now(_tz.utc).isoformat()
            elif isinstance(data[field], datetime):
                dt2 = data[field]
                if dt2.tzinfo is None:
                    dt2 = dt2.replace(tzinfo=_tz.utc)
                data[field] = dt2.astimezone(_tz.utc).isoformat()
    
    # Convert any remaining ObjectId instances to strings
    cleaned_data = {}
    for k, v in data.items():
        if isinstance(v, ObjectId):
            cleaned_data[k] = str(v)
        else:
            # Include all fields, even if None (important for CSR fields)
            cleaned_data[k] = v
    
    # CRITICAL: Ensure CSR fields are always included
    # These fields MUST be present for frontend CSR detection
    csr_critical_fields = [
        'certificate_generation_method', 
        'generation_method', 
        'csr_provided',
        'certificate_csr'
    ]
    
    for field in csr_critical_fields:
        if field in data:
            cleaned_data[field] = data[field]
    
    return cleaned_data

def fix_certificate_data(data):
    """
    Fix certificate data to ensure all fields have proper values.
    
    Args:
        data: Certificate data dictionary or list
        
    Returns:
        dict/list: Fixed certificate data
    """
    if isinstance(data, list):
        return [fix_certificate_data(item) for item in data]
    
    if not data:
        return {}
    
    # Ensure certificate ID
    cert_id = data.get('certificate_id') or data.get('_id') or data.get('id', '')
    data['certificate_id'] = str(cert_id) if cert_id else ''
    data['id'] = data['certificate_id']
    
    # Ensure required fields
    data['device_id'] = data.get('device_id', '')
    data['device_name'] = data.get('device_name') or f"Device-{data['device_id'][:8]}"
    data['status'] = data.get('status', 'active')
    data['type'] = data.get('type', 'device')
    
    # Fix serial number
    if not data.get('serial_number'):
        data['serial_number'] = data.get('certificate_id', '')[:16].upper()
    
    # Fix validity dates
    for field in ['valid_from', 'valid_to', 'issued_at']:
        if field in data and data[field]:
            if isinstance(data[field], str):
                try:
                    dt = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                    data[field] = dt.isoformat()
                except:
                    data[field] = datetime.now().isoformat()
            elif isinstance(data[field], datetime):
                data[field] = data[field].isoformat()
    
    # Calculate days until expiry
    if data.get('valid_to'):
        try:
            expiry = datetime.fromisoformat(data['valid_to'].replace('Z', '+00:00'))
            days_left = (expiry - datetime.now()).days
            data['days_until_expiry'] = max(0, days_left)
        except:
            data['days_until_expiry'] = 0
    
    # Remove None values
    return {k: v for k, v in data.items() if v is not None}

def fix_organization_data(data):
    """
    Fix organization data to ensure all fields have proper values.
    
    Args:
        data: Organization data dictionary or list
        
    Returns:
        dict/list: Fixed organization data
    """
    if isinstance(data, list):
        return [fix_organization_data(item) for item in data]
    
    if not data:
        return {}
    
    # Ensure organization ID
    org_id = data.get('organization_id') or data.get('_id') or data.get('id', '')
    data['organization_id'] = str(org_id) if org_id else ''
    data['id'] = data['organization_id']
    
    # Ensure required fields
    data['name'] = data.get('name') or 'Unnamed Organization'
    data['status'] = data.get('status', 'active')
    data['type'] = data.get('type', 'standard')
    
    # Fix contact info
    if 'contact' not in data:
        data['contact'] = {}
    
    # Fix settings
    if 'settings' not in data:
        data['settings'] = {
            'max_devices': 1000,
            'max_users': 100,
            'features': ['basic']
        }
    
    # Remove None values
    return {k: v for k, v in data.items() if v is not None}

def fix_stats_data(data):
    """
    Fix statistics data to ensure all fields have proper values.
    
    Args:
        data: Stats data dictionary
        
    Returns:
        dict: Fixed stats data
    """
    if not data:
        return {
            'total_devices': 0,
            'active_devices': 0,
            'total_users': 0,
            'total_organizations': 0,
            'alerts_today': 0,
            'data_points_today': 0
        }
    
    # Ensure all numeric fields
    numeric_fields = [
        'total_devices', 'active_devices', 'inactive_devices',
        'total_users', 'active_users', 'total_organizations',
        'alerts_today', 'data_points_today', 'certificates_expiring'
    ]
    
    for field in numeric_fields:
        if field in data:
            try:
                data[field] = int(data[field])
            except:
                data[field] = 0
    
    # Remove None values
    return {k: v for k, v in data.items() if v is not None}

def fix_telemetry_data(data):
    """
    Fix telemetry data to ensure proper formatting and remove MongoDB-specific fields.
    
    Args:
        data: Telemetry data dictionary or list
        
    Returns:
        dict/list: Fixed telemetry data
    """
    if isinstance(data, list):
        return [fix_telemetry_data(item) for item in data]
    
    if not data:
        return {}
    
    from bson import ObjectId
    
    # Create clean telemetry object
    cleaned = {}
    
    # Handle timestamp
    timestamp = data.get('timestamp')
    if timestamp:
        if isinstance(timestamp, datetime):
            cleaned['timestamp'] = timestamp.isoformat()
        elif isinstance(timestamp, str):
            cleaned['timestamp'] = timestamp
        else:
            cleaned['timestamp'] = datetime.now().isoformat()
    else:
        cleaned['timestamp'] = datetime.now().isoformat()
    
    # Handle device_id
    device_id = data.get('device_id', '')
    if isinstance(device_id, ObjectId):
        cleaned['device_id'] = str(device_id)
    else:
        cleaned['device_id'] = str(device_id) if device_id else ''
    
    # Handle data field (actual telemetry values)
    telemetry_values = data.get('data', {})
    if isinstance(telemetry_values, dict):
        cleaned['data'] = {}
        for key, value in telemetry_values.items():
            # Skip MongoDB internal fields
            if key.startswith('_'):
                continue
            # Convert ObjectIds to strings
            if isinstance(value, ObjectId):
                cleaned['data'][key] = str(value)
            elif isinstance(value, dict) and '$oid' in value:
                # Handle MongoDB extended JSON format
                cleaned['data'][key] = value['$oid']
            elif isinstance(value, dict):
                # Flatten nested sensor data (e.g., accelerometer.x -> accelerometer_x)
                for nested_key, nested_value in value.items():
                    flattened_key = f"{key}_{nested_key}"
                    if isinstance(nested_value, ObjectId):
                        cleaned['data'][flattened_key] = str(nested_value)
                    elif isinstance(nested_value, (int, float, str, bool)) or nested_value is None:
                        cleaned['data'][flattened_key] = nested_value
                    else:
                        cleaned['data'][flattened_key] = str(nested_value)
            elif isinstance(value, (int, float, str, bool)):
                cleaned['data'][key] = value
            elif value is None:
                cleaned['data'][key] = None
            else:
                # Convert other types to string
                cleaned['data'][key] = str(value)
    else:
        # If data is not a dict, try to extract telemetry values from root level
        cleaned['data'] = {}
        for key, value in data.items():
            if key not in ['_id', 'timestamp', 'device_id', 'metadata', 'organization_id']:
                if isinstance(value, ObjectId):
                    cleaned['data'][key] = str(value)
                elif isinstance(value, dict) and '$oid' in value:
                    cleaned['data'][key] = value['$oid']
                elif isinstance(value, dict):
                    # Flatten nested sensor data at root level
                    for nested_key, nested_value in value.items():
                        flattened_key = f"{key}_{nested_key}"
                        if isinstance(nested_value, ObjectId):
                            cleaned['data'][flattened_key] = str(nested_value)
                        elif isinstance(nested_value, (int, float, str, bool)) or nested_value is None:
                            cleaned['data'][flattened_key] = nested_value
                        else:
                            cleaned['data'][flattened_key] = str(nested_value)
                elif isinstance(value, (int, float, str, bool)) or value is None:
                    cleaned['data'][key] = value
                else:
                    cleaned['data'][key] = str(value)
    
    # Handle metadata
    metadata = data.get('metadata', {})
    if isinstance(metadata, dict):
        cleaned['metadata'] = {}
        for key, value in metadata.items():
            if key.startswith('_'):
                continue
            if isinstance(value, ObjectId):
                cleaned['metadata'][key] = str(value)
            elif isinstance(value, dict) and '$oid' in value:
                cleaned['metadata'][key] = value['$oid']
            else:
                cleaned['metadata'][key] = value
    else:
        cleaned['metadata'] = {}
    
    # Handle organization_id if present
    org_id = data.get('organization_id')
    if org_id:
        if isinstance(org_id, ObjectId):
            cleaned['organization_id'] = str(org_id)
        elif isinstance(org_id, dict) and '$oid' in org_id:
            cleaned['organization_id'] = org_id['$oid']
        else:
            cleaned['organization_id'] = str(org_id)
    
    return cleaned
