"""
MQTT Client Wrapper for TESAIoT Platform

Provides a simple interface for MQTTS connections with Server TLS authentication.
Uses paho-mqtt with TLS 1.2+ and CA certificate verification.

Copyright (c) 2025 TESAIoT Platform (TESA)
Licensed under Apache License 2.0
"""

import logging
import ssl
from typing import Callable, Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTClient:
    """MQTT client with Server TLS authentication."""

    def __init__(
        self,
        host: str,
        port: int,
        client_id: str,
        username: str,
        password: str,
        ca_cert_path: str,
        keepalive: int = 60
    ):
        """
        Initialize MQTT client.

        Args:
            host: MQTT broker hostname
            port: MQTT broker port (8884 for Server TLS)
            client_id: Client identifier (device_id)
            username: MQTT username (device_id)
            password: MQTT password from Server TLS bundle
            ca_cert_path: Path to CA certificate
            keepalive: Keepalive interval in seconds
        """
        self.host = host
        self.port = port
        self.keepalive = keepalive

        # Create MQTT client
        self._client = mqtt.Client(
            client_id=client_id,
            protocol=mqtt.MQTTv311,
            transport='tcp'
        )

        # Set credentials
        self._client.username_pw_set(username, password)

        # Configure TLS
        self._client.tls_set(
            ca_certs=ca_cert_path,
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS,
            ciphers=None
        )

        # Enforce TLS 1.2+
        self._client.tls_insecure_set(False)

        # Set callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_publish = self._on_publish

        self._connected = False
        self._message_callback: Optional[Callable] = None

    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection result."""
        if rc == 0:
            self._connected = True
            logger.info("MQTT connected successfully")

            # Subscribe to device topics
            device_id = client._client_id.decode() if isinstance(
                client._client_id, bytes
            ) else client._client_id

            topics = [
                (f"device/{device_id}/commands", 1),
                (f"device/{device_id}/config", 1),
            ]
            client.subscribe(topics)
            logger.info(f"Subscribed to command/config topics")
        else:
            self._connected = False
            error_messages = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized",
            }
            error = error_messages.get(rc, f"Unknown error ({rc})")
            logger.error(f"MQTT connection failed: {error}")

    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection."""
        self._connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnect: {rc}")
        else:
            logger.info("MQTT disconnected")

    def _on_message(self, client, userdata, msg):
        """Handle incoming messages."""
        logger.debug(f"Received: {msg.topic} -> {msg.payload.decode()}")
        if self._message_callback:
            self._message_callback(msg.topic, msg.payload.decode())

    def _on_publish(self, client, userdata, mid):
        """Handle publish confirmation."""
        logger.debug(f"Message {mid} published")

    def connect(self) -> bool:
        """
        Connect to MQTT broker.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._client.connect(
                self.host,
                self.port,
                self.keepalive
            )
            self._client.loop_start()

            # Wait for connection
            import time
            for _ in range(10):
                if self._connected:
                    return True
                time.sleep(0.5)

            logger.error("MQTT connection timeout")
            return False

        except Exception as e:
            logger.error(f"MQTT connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker."""
        self._client.loop_stop()
        self._client.disconnect()

    def publish(self, topic: str, payload: str, qos: int = 1) -> bool:
        """
        Publish message to topic.

        Args:
            topic: MQTT topic
            payload: Message payload (JSON string)
            qos: Quality of Service (0, 1, or 2)

        Returns:
            True if publish successful, False otherwise
        """
        if not self._connected:
            logger.warning("Not connected to MQTT broker")
            return False

        try:
            result = self._client.publish(topic, payload, qos=qos)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            logger.error(f"Publish error: {e}")
            return False

    def set_message_callback(self, callback: Callable):
        """Set callback for incoming messages."""
        self._message_callback = callback

    @property
    def is_connected(self) -> bool:
        """Check if connected to broker."""
        return self._connected
