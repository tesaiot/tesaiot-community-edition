# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Temporary stub for device schemas when pydantic is not available
"""

# Mock classes to prevent import errors
class DeviceCategory:
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    GATEWAY = "gateway"
    CONTROLLER = "controller"
    WEARABLE = "wearable"
    DRONE = "drone"
    ROBOTICS = "robotics"
    AMR_AGV = "amr_agv"
    SMART_HOME = "smart_home"
    MINIPC = "minipc"
    EDGE_SERVER = "edge_server"
    INDUSTRIAL_IOT = "industrial_iot"
    MEDICAL_DEVICE = "medical_device"
    WELLNESS_DEVICE = "wellness_device"

# Placeholder functions
device_schema_registry = {}

def get_device_schema_fields(category):
    """Temporary implementation returning hardcoded schemas"""
    schemas = {
        'industrial_iot': [
            {'name': 'communication_protocol', 'label': 'Communication Protocol', 'type': 'text', 'required': True},
            {'name': 'plc_type', 'label': 'PLC Type', 'type': 'text', 'required': False},
            {'name': 'scada_integration', 'label': 'SCADA Integration', 'type': 'switch', 'required': False},
            {'name': 'data_frequency', 'label': 'Data Frequency', 'type': 'number', 'required': False}
        ],
        'robotics': [
            {'name': 'robot_type', 'label': 'Robot Type', 'type': 'text', 'required': True},
            {'name': 'payload_capacity', 'label': 'Payload Capacity', 'type': 'number', 'required': False},
            {'name': 'safety_mode', 'label': 'Safety Mode', 'type': 'text', 'required': False}
        ],
        'amr_agv': [
            {'name': 'vehicle_type', 'label': 'Vehicle Type', 'type': 'text', 'required': True},
            {'name': 'max_load', 'label': 'Max Load', 'type': 'number', 'required': False},
            {'name': 'navigation_type', 'label': 'Navigation Type', 'type': 'text', 'required': False}
        ]
    }
    return schemas.get(category, [])