"""
HTTPS Client Wrapper for TESAIoT Platform

Provides a simple interface for HTTPS connections with API Key authentication.

Copyright (c) 2025 TESAIoT Platform (TESA)
Licensed under Apache License 2.0
"""

import logging
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


class HTTPSClient:
    """HTTPS client with API Key authentication."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        ca_cert_path: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize HTTPS client.

        Args:
            base_url: API base URL
            api_key: API Key for authentication
            ca_cert_path: Path to CA certificate (optional)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.ca_cert_path = ca_cert_path
        self.timeout = timeout

        # Setup session
        self._session = requests.Session()
        self._session.headers.update({
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        })

        # Configure TLS verification
        if ca_cert_path:
            self._session.verify = ca_cert_path
        else:
            # Use system CA bundle
            self._session.verify = True

    def send_telemetry(self, device_id: str, payload: Dict) -> bool:
        """
        Send telemetry data to TESAIoT Platform.

        Args:
            device_id: Device identifier
            payload: Telemetry payload

        Returns:
            True if successful, False otherwise
        """
        # CE ingest endpoint: POST /api/v1/telemetry with body {device_id, data[, timestamp]}
        # authorized by the device API key (X-API-KEY). The cloud path
        # /devices/{id}/telemetry does not exist on Community Edition.
        url = f"{self.base_url}/api/v1/telemetry"

        try:
            response = self._session.post(
                url,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200 or response.status_code == 201:
                logger.debug(f"Telemetry sent successfully")
                return True
            else:
                logger.warning(
                    f"Telemetry failed: {response.status_code} - {response.text}"
                )
                return False

        except requests.exceptions.SSLError as e:
            logger.error(f"SSL error: {e}")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return False
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False

    def get_device_config(self, device_id: str) -> Optional[Dict]:
        """
        Get device configuration from TESAIoT Platform.

        Args:
            device_id: Device identifier

        Returns:
            Configuration dict or None if failed
        """
        url = f"{self.base_url}/devices/{device_id}"

        try:
            response = self._session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"Get config failed: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Get config error: {e}")
            return None

    def health_check(self) -> bool:
        """
        Check API health.

        Returns:
            True if API is healthy, False otherwise
        """
        # health endpoint is at the base API level, not under /external
        base = self.base_url.replace('/external', '')
        url = f"{base}/health"

        try:
            response = self._session.get(url, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
