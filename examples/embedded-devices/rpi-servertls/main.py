#!/usr/bin/env python3
"""
TESAIoT Platform - Raspberry Pi Server TLS Client

Connects to TESAIoT Platform using Server TLS authentication (NCSA Level 1).
Supports both MQTTS and HTTPS transport modes.

Copyright (c) 2025 TESAIoT Platform (TESA)
Licensed under Apache License 2.0
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

from mqtt_client import MQTTClient
from https_client import HTTPSClient
from sensor_simulator import SensorSimulator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info("Shutdown signal received, stopping...")
    running = False


def load_config():
    """Load configuration from environment variables."""
    load_dotenv()

    config = {
        'device_id': os.getenv('DEVICE_ID'),
        'mqtt_host': os.getenv('MQTT_HOST', 'localhost'),
        'mqtt_port': int(os.getenv('MQTT_PORT', '8884')),
        'mqtt_username': os.getenv('MQTT_USERNAME'),
        'mqtt_password': os.getenv('MQTT_PASSWORD'),
        'ca_cert_path': os.getenv('CA_CERT_PATH', './certs/ca.pem'),
        'api_base_url': os.getenv('API_BASE_URL', 'https://localhost'),
        'api_key': os.getenv('API_KEY'),
    }

    # Validate required config
    if not config['device_id']:
        logger.error("DEVICE_ID is required. Set it in .env file.")
        sys.exit(1)

    return config


def create_telemetry_payload(device_id: str, sensor_data: dict) -> dict:
    """Create TESAIoT telemetry payload format."""
    return {
        'device_id': device_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'data': sensor_data
    }


def run_mqtt_mode(config: dict, interval: int):
    """Run in MQTTS mode."""
    global running

    # Validate MQTT config
    if not config['mqtt_username'] or not config['mqtt_password']:
        logger.error("MQTT_USERNAME and MQTT_PASSWORD required for MQTTS mode")
        sys.exit(1)

    # Initialize clients
    mqtt_client = MQTTClient(
        host=config['mqtt_host'],
        port=config['mqtt_port'],
        client_id=config['device_id'],
        username=config['mqtt_username'],
        password=config['mqtt_password'],
        ca_cert_path=config['ca_cert_path']
    )

    sensor = SensorSimulator()

    # Connect to broker
    if not mqtt_client.connect():
        logger.error("Failed to connect to MQTT broker")
        sys.exit(1)

    logger.info(f"Connected to {config['mqtt_host']}:{config['mqtt_port']}")
    logger.info(f"Publishing telemetry every {interval} seconds...")

    # Telemetry topic
    topic = f"device/{config['device_id']}/telemetry"

    try:
        while running:
            # Read sensor data
            sensor_data = sensor.read()

            # Create and publish telemetry
            payload = create_telemetry_payload(config['device_id'], sensor_data)

            if mqtt_client.publish(topic, json.dumps(payload)):
                logger.info(f"Published: {json.dumps(sensor_data)}")
            else:
                logger.warning("Failed to publish telemetry")

            # Wait for next interval
            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        mqtt_client.disconnect()
        logger.info("Disconnected from MQTT broker")


def run_https_mode(config: dict, interval: int):
    """Run in HTTPS mode."""
    global running

    # Validate HTTPS config
    if not config['api_key']:
        logger.error("API_KEY required for HTTPS mode")
        sys.exit(1)

    # Initialize clients
    https_client = HTTPSClient(
        base_url=config['api_base_url'],
        api_key=config['api_key'],
        ca_cert_path=config['ca_cert_path']
    )

    sensor = SensorSimulator()

    logger.info(f"Sending telemetry to {config['api_base_url']}")
    logger.info(f"Publishing telemetry every {interval} seconds...")

    try:
        while running:
            # Read sensor data
            sensor_data = sensor.read()

            # Create and send telemetry
            payload = create_telemetry_payload(config['device_id'], sensor_data)

            if https_client.send_telemetry(config['device_id'], payload):
                logger.info(f"Sent: {json.dumps(sensor_data)}")
            else:
                logger.warning("Failed to send telemetry")

            # Wait for next interval
            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='TESAIoT Raspberry Pi Server TLS Client'
    )
    parser.add_argument(
        '--mode',
        choices=['mqtt', 'https'],
        default='mqtt',
        help='Transport mode (default: mqtt)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=10,
        help='Telemetry interval in seconds (default: 10)'
    )
    args = parser.parse_args()

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Load configuration
    config = load_config()

    logger.info("=" * 50)
    logger.info("TESAIoT Raspberry Pi Client (Server TLS)")
    logger.info(f"Device ID: {config['device_id']}")
    logger.info(f"Mode: {args.mode.upper()}")
    logger.info("=" * 50)

    # Run in selected mode
    if args.mode == 'mqtt':
        run_mqtt_mode(config, args.interval)
    else:
        run_https_mode(config, args.interval)

    logger.info("Client stopped")


if __name__ == '__main__':
    main()
