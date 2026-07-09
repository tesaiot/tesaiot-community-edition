"""
Sensor Simulator for TESAIoT Examples

Simulates sensor readings for testing without hardware.
Replace with actual sensor libraries for production use.

Copyright (c) 2025 TESAIoT Platform (TESA)
Licensed under Apache License 2.0
"""

import random
from typing import Dict


class SensorSimulator:
    """Simulates common IoT sensor readings."""

    def __init__(self):
        """Initialize simulator with base values."""
        self._temperature = 25.0
        self._humidity = 60.0
        self._pressure = 1013.25

    def read(self) -> Dict[str, float]:
        """
        Read simulated sensor values.

        Values drift slightly from previous reading for realism.

        Returns:
            Dictionary with sensor readings
        """
        # Add small random drift to each value
        self._temperature += random.uniform(-0.5, 0.5)
        self._humidity += random.uniform(-1.0, 1.0)
        self._pressure += random.uniform(-0.5, 0.5)

        # Clamp to realistic ranges
        self._temperature = max(min(self._temperature, 45.0), -10.0)
        self._humidity = max(min(self._humidity, 100.0), 0.0)
        self._pressure = max(min(self._pressure, 1050.0), 950.0)

        return {
            'temperature': round(self._temperature, 2),
            'humidity': round(self._humidity, 2),
            'pressure': round(self._pressure, 2)
        }


class DHT22Sensor:
    """
    DHT22 Temperature/Humidity Sensor

    Requires: pip install adafruit-circuitpython-dht

    Example:
        sensor = DHT22Sensor(pin=4)
        data = sensor.read()
    """

    def __init__(self, pin: int = 4):
        """
        Initialize DHT22 sensor.

        Args:
            pin: GPIO pin number (BCM)
        """
        self.pin = pin
        self._dht = None

        try:
            import board
            import adafruit_dht

            # Map pin number to board pin
            pin_map = {
                4: board.D4,
                17: board.D17,
                27: board.D27,
                22: board.D22,
            }
            board_pin = pin_map.get(pin, board.D4)
            self._dht = adafruit_dht.DHT22(board_pin)
        except ImportError:
            print("DHT library not installed. Using simulator.")
            self._simulator = SensorSimulator()
        except Exception as e:
            print(f"DHT sensor init failed: {e}. Using simulator.")
            self._simulator = SensorSimulator()

    def read(self) -> Dict[str, float]:
        """Read temperature and humidity."""
        if self._dht:
            try:
                return {
                    'temperature': round(self._dht.temperature, 2),
                    'humidity': round(self._dht.humidity, 2)
                }
            except RuntimeError:
                # DHT sensors can be flaky, retry next time
                return self._simulator.read()
        else:
            return self._simulator.read()


class BMP280Sensor:
    """
    BMP280 Pressure/Temperature Sensor (I2C)

    Requires: pip install adafruit-circuitpython-bmp280

    Example:
        sensor = BMP280Sensor()
        data = sensor.read()
    """

    def __init__(self, address: int = 0x76):
        """
        Initialize BMP280 sensor.

        Args:
            address: I2C address (0x76 or 0x77)
        """
        self.address = address
        self._bmp = None

        try:
            import board
            import busio
            import adafruit_bmp280

            i2c = busio.I2C(board.SCL, board.SDA)
            self._bmp = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=address)
        except ImportError:
            print("BMP280 library not installed. Using simulator.")
            self._simulator = SensorSimulator()
        except Exception as e:
            print(f"BMP280 sensor init failed: {e}. Using simulator.")
            self._simulator = SensorSimulator()

    def read(self) -> Dict[str, float]:
        """Read temperature and pressure."""
        if self._bmp:
            return {
                'temperature': round(self._bmp.temperature, 2),
                'pressure': round(self._bmp.pressure, 2)
            }
        else:
            data = self._simulator.read()
            return {
                'temperature': data['temperature'],
                'pressure': data['pressure']
            }
