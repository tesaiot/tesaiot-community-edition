#!/usr/bin/env python3
"""
TESAIoT Edge AI Device Simulator - Python Client

Simulates an IoT device (Infineon XENSIV DPS368) sending telemetry data
with periodic anomaly injection for Edge AI testing.

Device: Infineon XENSIV DPS368
Sensor Type: Barometric Pressure & Temperature Sensor
Data Range:
  - Pressure: 300-1200 hPa (typical: 950-1050 hPa)
  - Temperature: -40°C to +85°C (typical: 20-35°C)

Usage:
    pip install -r requirements.txt
    cp .env.example .env
    # Edit .env if needed
    python main.py

See: https://github.com/tesaiot/developer-hub
"""

import json
import os
import random
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional

from dotenv import load_dotenv
import paho.mqtt.client as mqtt

# Load environment variables from .env file
load_dotenv()


class InfineonDPS368Simulator:
    """
    IoT Device Simulator for Infineon XENSIV DPS368 Sensor.

    Simulates realistic sensor data with periodic anomaly injection
    for Edge AI anomaly detection testing.
    """

    # Sensor specifications (based on Infineon DPS368 datasheet)
    PRESSURE_MIN = 950.0    # hPa (normal range)
    PRESSURE_MAX = 1050.0   # hPa (normal range)
    TEMP_MIN = 20.0         # °C (normal range)
    TEMP_MAX = 35.0         # °C (normal range)

    # Anomaly values for Edge AI testing
    ANOMALY_TEMP = 85.0     # High temperature anomaly
    ANOMALY_PRESSURE = 1200.0  # High pressure anomaly

    def __init__(self):
        """Initialize the MQTT client with configuration from environment."""
        # Configuration from environment variables
        self.broker_host = os.getenv("MQTT_BROKER_HOST", "localhost")
        self.broker_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
        self.device_id = os.getenv("DEVICE_ID", "infineon-sensor-01")
        self.topic = os.getenv(
            "MQTT_TOPIC",
            f"device/{os.getenv('DEVICE_ID', 'infineon-sensor-01')}/telemetry"
        )
        self.publish_interval = float(os.getenv("PUBLISH_INTERVAL", "1.0"))
        self.anomaly_interval = int(os.getenv("ANOMALY_INTERVAL", "10"))

        self.client_id = os.getenv(
            "MQTT_CLIENT_ID",
            f"dps368-sim-{int(datetime.now().timestamp())}"
        )

        # Create MQTT client with auto-reconnect
        # Support both paho-mqtt 1.x and 2.x
        try:
            # paho-mqtt 2.x style
            self.client = mqtt.Client(
                client_id=self.client_id,
                protocol=mqtt.MQTTv311,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            )
            self._paho_v2 = True
        except (AttributeError, TypeError):
            # paho-mqtt 1.x fallback
            self.client = mqtt.Client(
                client_id=self.client_id,
                protocol=mqtt.MQTTv311,
            )
            self._paho_v2 = False

        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish

        # TESAIoT Community Edition: the EMQX broker requires authenticated,
        # TLS-protected connections and rejects anonymous plaintext clients.
        # Enable serverTLS + username/password when MQTT_USE_TLS is set.
        if os.getenv("MQTT_USE_TLS", "").lower() in ("1", "true", "yes"):
            import ssl
            self.client.tls_set(ca_certs=os.getenv("MQTT_CA_CERT"),
                                cert_reqs=ssl.CERT_REQUIRED,
                                tls_version=ssl.PROTOCOL_TLS)
            self.client.tls_insecure_set(False)
        username = os.getenv("MQTT_USERNAME")
        if username:
            self.client.username_pw_set(username, os.getenv("MQTT_PASSWORD", ""))

        # Enable auto-reconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        # Running flag for graceful shutdown
        self.running = True
        self.connected = False
        self.packet_count = 0

        # Statistics
        self.total_published = 0
        self.total_anomalies = 0

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Optional[Any] = None,
    ) -> None:
        """Handle connection to broker."""
        # paho 1.x passes rc as int, paho 2.x passes reason_code object
        rc = (
            reason_code
            if isinstance(reason_code, int)
            else reason_code.value if hasattr(reason_code, "value") else 0
        )

        if rc == 0:
            self.connected = True
            print(f"[{self._timestamp()}] Connected to MQTT Broker: {self.broker_host}:{self.broker_port}")
            print(f"[{self._timestamp()}] Device ID: {self.device_id}")
            print(f"[{self._timestamp()}] Topic: {self.topic}")
            print(f"[{self._timestamp()}] Publishing every {self.publish_interval}s (anomaly every {self.anomaly_interval} packets)")
            print("-" * 60)
        else:
            self.connected = False
            print(f"[{self._timestamp()}] Connection failed with reason code: {rc}")

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        reason_code: Any = None,
        properties: Optional[Any] = None,
    ) -> None:
        """Handle disconnection from broker."""
        self.connected = False
        if self.running:
            print(f"[{self._timestamp()}] Disconnected from broker. Attempting to reconnect...")
        else:
            print(f"[{self._timestamp()}] Disconnected from broker.")

    def _on_publish(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_code: Any = None,
        properties: Optional[Any] = None,
    ) -> None:
        """Handle publish confirmation."""
        self.total_published += 1

    def _timestamp(self) -> str:
        """Get current timestamp string."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _generate_normal_data(self) -> dict:
        """Generate normal sensor readings."""
        # Add slight variation for realistic data
        pressure = round(
            random.uniform(self.PRESSURE_MIN, self.PRESSURE_MAX), 2
        )
        temperature = round(
            random.uniform(self.TEMP_MIN, self.TEMP_MAX), 2
        )
        return {
            "pressure": pressure,
            "temperature": temperature
        }

    def _generate_anomaly_data(self) -> dict:
        """Generate anomaly data for Edge AI testing."""
        # Randomly choose anomaly type
        anomaly_type = random.choice(["temperature", "pressure", "both"])

        if anomaly_type == "temperature":
            return {
                "pressure": round(random.uniform(self.PRESSURE_MIN, self.PRESSURE_MAX), 2),
                "temperature": round(self.ANOMALY_TEMP + random.uniform(0, 5), 2)
            }
        elif anomaly_type == "pressure":
            return {
                "pressure": round(self.ANOMALY_PRESSURE + random.uniform(0, 50), 2),
                "temperature": round(random.uniform(self.TEMP_MIN, self.TEMP_MAX), 2)
            }
        else:  # both
            return {
                "pressure": round(self.ANOMALY_PRESSURE + random.uniform(0, 50), 2),
                "temperature": round(self.ANOMALY_TEMP + random.uniform(0, 5), 2)
            }

    def _generate_telemetry(self, is_anomaly: bool = False) -> dict:
        """
        Generate telemetry payload following the data schema.

        Schema:
        {
            "timestamp": "<ISO-8601-String>",
            "device_id": "infineon-sensor-01",
            "sensor_type": "DPS368",
            "data": {
                "pressure": <float>,
                "temperature": <float>
            }
        }
        """
        if is_anomaly:
            data = self._generate_anomaly_data()
        else:
            data = self._generate_normal_data()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": self.device_id,
            "sensor_type": "DPS368",
            "data": data
        }

    def _publish_telemetry(self) -> None:
        """Publish telemetry data to MQTT broker."""
        self.packet_count += 1

        # Check if this should be an anomaly packet
        is_anomaly = (self.packet_count % self.anomaly_interval) == 0

        # Generate telemetry payload
        payload = self._generate_telemetry(is_anomaly)
        payload_json = json.dumps(payload, indent=None)

        # Publish to broker
        result = self.client.publish(
            topic=self.topic,
            payload=payload_json,
            qos=1,
            retain=False
        )

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            data = payload["data"]
            status = "[ANOMALY]" if is_anomaly else "[NORMAL]"

            if is_anomaly:
                self.total_anomalies += 1

            print(
                f"[{self._timestamp()}] {status} Published: "
                f"Pressure={data['pressure']:.2f} hPa, "
                f"Temperature={data['temperature']:.2f} °C"
            )
        else:
            print(f"[{self._timestamp()}] Publish failed with error code: {result.rc}")

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handle graceful shutdown on SIGINT/SIGTERM."""
        print(f"\n[{self._timestamp()}] Shutting down...")
        print("-" * 60)
        print(f"Total packets published: {self.total_published}")
        print(f"Total anomalies injected: {self.total_anomalies}")
        print("-" * 60)
        self.running = False

    def run(self) -> None:
        """Run the device simulator."""
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Print banner
        print()
        print("=" * 60)
        print("  TESAIoT Edge AI Device Simulator")
        print("  Sensor: Infineon XENSIV DPS368")
        print("=" * 60)
        print()
        print(f"Connecting to MQTT Broker at {self.broker_host}:{self.broker_port}...")
        print()

        # Connect to broker
        try:
            self.client.connect(
                host=self.broker_host,
                port=self.broker_port,
                keepalive=60
            )
        except Exception as e:
            print(f"[{self._timestamp()}] Failed to connect to broker: {e}")
            print()
            print("Make sure the MQTT broker is running:")
            print("  - Local: mosquitto, EMQX, or HiveMQ")
            print("  - Docker: docker run -p 1883:1883 eclipse-mosquitto")
            print()
            sys.exit(1)

        # Start network loop in background thread
        self.client.loop_start()

        # Wait for connection
        retry_count = 0
        max_retries = 10
        while not self.connected and retry_count < max_retries:
            time.sleep(0.5)
            retry_count += 1

        if not self.connected:
            print(f"[{self._timestamp()}] Failed to connect after {max_retries} retries")
            self.client.loop_stop()
            sys.exit(1)

        # Main publishing loop
        try:
            while self.running:
                if self.connected:
                    self._publish_telemetry()
                else:
                    print(f"[{self._timestamp()}] Waiting for reconnection...")

                time.sleep(self.publish_interval)
        except Exception as e:
            print(f"[{self._timestamp()}] Error in main loop: {e}")
        finally:
            # Clean disconnect
            self.client.loop_stop()
            self.client.disconnect()
            print(f"[{self._timestamp()}] Device simulator stopped.")


def main():
    """Entry point."""
    simulator = InfineonDPS368Simulator()
    simulator.run()


if __name__ == "__main__":
    main()
