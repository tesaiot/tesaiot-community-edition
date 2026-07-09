# Copyright (c) 2025 TESAIoT Platform (TESA)
# Licensed under Apache License 2.0

"""Unit tests for MQTT client and sensor simulator."""

import pytest
from unittest.mock import patch, MagicMock


class TestMQTTClient:
    """Test MQTT client initialization and methods."""

    @patch("mqtt_client.mqtt.Client")
    def test_client_initialization(self, mock_mqtt_client):
        """Client should configure TLS and credentials."""
        from mqtt_client import MQTTClient

        client = MQTTClient(
            host="localhost",
            port=8884,
            client_id="device-001",
            username="device-001",
            password="secret-password",
            ca_cert_path="/path/to/ca.crt"
        )

        # Verify MQTT client was created
        mock_mqtt_client.assert_called_once()

        # Verify credentials were set
        mock_instance = mock_mqtt_client.return_value
        mock_instance.username_pw_set.assert_called_once_with(
            "device-001", "secret-password"
        )

        # Verify TLS was configured
        mock_instance.tls_set.assert_called_once()

    @patch("mqtt_client.mqtt.Client")
    def test_connect_success(self, mock_mqtt_client):
        """Successful connection should return True."""
        from mqtt_client import MQTTClient

        mock_instance = mock_mqtt_client.return_value

        client = MQTTClient(
            host="localhost",
            port=8884,
            client_id="device-001",
            username="device-001",
            password="secret",
            ca_cert_path="/ca.crt"
        )

        # Simulate successful connection
        client._connected = True

        # Start loop and set connected
        result = client.connect()

        mock_instance.connect.assert_called_once_with(
            "localhost", 8884, 60
        )

    @patch("mqtt_client.mqtt.Client")
    def test_publish_when_not_connected(self, mock_mqtt_client):
        """Publish should fail when not connected."""
        from mqtt_client import MQTTClient

        client = MQTTClient(
            host="localhost",
            port=8884,
            client_id="device-001",
            username="device-001",
            password="secret",
            ca_cert_path="/ca.crt"
        )

        # Not connected
        client._connected = False

        result = client.publish("test/topic", '{"data": 1}')
        assert result is False

    @patch("mqtt_client.mqtt.Client")
    def test_publish_when_connected(self, mock_mqtt_client):
        """Publish should succeed when connected."""
        from mqtt_client import MQTTClient
        import paho.mqtt.client as mqtt

        mock_instance = mock_mqtt_client.return_value
        mock_result = MagicMock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        mock_instance.publish.return_value = mock_result

        client = MQTTClient(
            host="localhost",
            port=8884,
            client_id="device-001",
            username="device-001",
            password="secret",
            ca_cert_path="/ca.crt"
        )

        # Set connected
        client._connected = True

        result = client.publish("test/topic", '{"data": 1}', qos=1)
        assert result is True
        mock_instance.publish.assert_called_once_with(
            "test/topic", '{"data": 1}', qos=1
        )

    @patch("mqtt_client.mqtt.Client")
    def test_is_connected_property(self, mock_mqtt_client):
        """is_connected should reflect connection state."""
        from mqtt_client import MQTTClient

        client = MQTTClient(
            host="localhost",
            port=8884,
            client_id="device-001",
            username="device-001",
            password="secret",
            ca_cert_path="/ca.crt"
        )

        assert client.is_connected is False

        client._connected = True
        assert client.is_connected is True

    @patch("mqtt_client.mqtt.Client")
    def test_message_callback(self, mock_mqtt_client):
        """Message callback should be invoked on incoming message."""
        from mqtt_client import MQTTClient

        client = MQTTClient(
            host="localhost",
            port=8884,
            client_id="device-001",
            username="device-001",
            password="secret",
            ca_cert_path="/ca.crt"
        )

        # Set up callback
        callback_called = []

        def my_callback(topic, payload):
            callback_called.append((topic, payload))

        client.set_message_callback(my_callback)

        # Simulate message
        mock_msg = MagicMock()
        mock_msg.topic = "test/topic"
        mock_msg.payload = b'{"value": 42}'

        client._on_message(None, None, mock_msg)

        assert len(callback_called) == 1
        assert callback_called[0] == ("test/topic", '{"value": 42}')


class TestSensorSimulator:
    """Test sensor data simulator."""

    def test_simulator_initialization(self):
        """Simulator should start with default values."""
        from sensor_simulator import SensorSimulator

        simulator = SensorSimulator()
        # Check internal state exists
        assert hasattr(simulator, '_temperature')
        assert hasattr(simulator, '_humidity')
        assert hasattr(simulator, '_pressure')

    def test_read_returns_dict(self):
        """read() should return dictionary with sensor values."""
        from sensor_simulator import SensorSimulator

        simulator = SensorSimulator()
        data = simulator.read()

        assert isinstance(data, dict)
        assert 'temperature' in data
        assert 'humidity' in data
        assert 'pressure' in data

    def test_read_values_in_range(self):
        """Values should be within realistic ranges."""
        from sensor_simulator import SensorSimulator

        simulator = SensorSimulator()

        # Read multiple times to test drift
        for _ in range(100):
            data = simulator.read()
            assert -10.0 <= data['temperature'] <= 45.0
            assert 0.0 <= data['humidity'] <= 100.0
            assert 950.0 <= data['pressure'] <= 1050.0

    def test_read_values_rounded(self):
        """Values should be rounded to 2 decimal places."""
        from sensor_simulator import SensorSimulator

        simulator = SensorSimulator()
        data = simulator.read()

        # Check that values are rounded
        for key in ['temperature', 'humidity', 'pressure']:
            value = data[key]
            # Should have at most 2 decimal places
            assert round(value, 2) == value


class TestDHT22Sensor:
    """Test DHT22 sensor wrapper."""

    def test_fallback_to_simulator(self):
        """Should fall back to simulator when hardware unavailable."""
        from sensor_simulator import DHT22Sensor

        # This should not raise an error even without hardware
        sensor = DHT22Sensor(pin=4)
        data = sensor.read()

        assert 'temperature' in data
        assert 'humidity' in data


class TestBMP280Sensor:
    """Test BMP280 sensor wrapper."""

    def test_fallback_to_simulator(self):
        """Should fall back to simulator when hardware unavailable."""
        from sensor_simulator import BMP280Sensor

        # This should not raise an error even without hardware
        sensor = BMP280Sensor(address=0x76)
        data = sensor.read()

        assert 'temperature' in data
        assert 'pressure' in data
