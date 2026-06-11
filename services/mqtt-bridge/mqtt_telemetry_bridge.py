# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""
TESAIoT Community Edition - MQTT Telemetry Bridge with Vault PKI Support
Subscribes to EMQX telemetry topics and forwards data to API

Data Flow: EMQX -> MQTT Bridge -> API -> MongoDB -> UI Telemetry Display
Enhanced with Vault-issued certificates for secure internal communication
"""

import paho.mqtt.client as mqtt
import base64
import json
import time
import requests
import logging
import threading
from datetime import datetime, timezone
from urllib.parse import quote
import os
import signal
import ssl
import socket
import ast

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.environ.get('DEBUG', '').lower() == 'true' else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Only console output in container
    ]
)
logger = logging.getLogger(__name__)

# Healthcheck heartbeat file: the compose healthcheck verifies its mtime is
# recent. /tmp is a tmpfs mount in the hardened (read_only) container.
HEALTH_FILE = os.environ.get('HEALTH_FILE', '/tmp/mqtt-bridge-healthy')

# Maximum accepted MQTT payload size (bytes) before parsing/logging.
MAX_PAYLOAD_BYTES = int(os.environ.get('MAX_PAYLOAD_BYTES', '1048576'))


def touch_health_file():
    """Update the healthcheck heartbeat file's mtime (create if missing)."""
    try:
        with open(HEALTH_FILE, 'a'):
            os.utime(HEALTH_FILE, None)
    except OSError as e:
        logger.debug(f"Could not touch health file {HEALTH_FILE}: {e}")


def decode_jwt_exp(token):
    """Decode the `exp` claim from a JWT without verifying the signature.

    Signature verification is not needed here: the bridge only uses `exp`
    to schedule its own proactive re-authentication; the API still verifies
    the token on every request.
    Returns the exp epoch seconds, or None if it cannot be determined.
    """
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        # Restore base64url padding
        payload_b64 += '=' * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = claims.get('exp')
        return int(exp) if exp is not None else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

def fix_telemetry_payload(payload):
    """
    Fix telemetry payload by converting string representations of dictionaries
    to actual dictionary objects. This handles PSoC devices that send sensor
    data as strings instead of proper JSON objects.
    
    Args:
        payload: The telemetry data payload
        
    Returns:
        Fixed payload with proper JSON objects
    """
    if not isinstance(payload, dict):
        return payload
    
    fixed_payload = {}
    
    for key, value in payload.items():
        if isinstance(value, str) and value.strip().startswith("{") and value.strip().endswith("}"):
            # This looks like a string representation of a dictionary
            try:
                # Use ast.literal_eval for safe evaluation of Python literals
                parsed_value = ast.literal_eval(value)
                fixed_payload[key] = parsed_value
                logger.debug(f"✅ Converted string to dict for field '{key}'")
            except (ValueError, SyntaxError) as e:
                # If parsing fails, try to clean up and parse as JSON
                try:
                    # Replace single quotes with double quotes for JSON compatibility
                    json_str = value.replace("'", '"')
                    parsed_value = json.loads(json_str)
                    fixed_payload[key] = parsed_value
                    logger.debug(f"✅ Converted string to dict using JSON for field '{key}'")
                except Exception as json_error:
                    # If all parsing fails, keep the original string
                    logger.warning(f"⚠️  Could not parse string representation for field '{key}': {e}")
                    fixed_payload[key] = value
        else:
            # Keep other values as-is
            fixed_payload[key] = value
    
    return fixed_payload

def flatten_telemetry_data(data, parent_key='', sep='_'):
    """
    Flatten nested dictionary structures into flat key-value pairs.
    This is needed because the API expects flat telemetry data.
    
    Args:
        data: The nested dictionary to flatten
        parent_key: The base key for recursion
        sep: Separator to use between nested keys
        
    Returns:
        Flattened dictionary with concatenated keys
        
    Example:
        Input: {"accel": {"x": 0.1, "y": 0.2}, "temp": 25}
        Output: {"accel_x": 0.1, "accel_y": 0.2, "temp": 25}
    """
    items = []
    
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        
        if isinstance(value, dict):
            # Recursively flatten nested dictionaries
            items.extend(flatten_telemetry_data(value, new_key, sep=sep).items())
        else:
            items.append((new_key, value))
    
    return dict(items)

class MQTTTelemetryBridge:
    """MQTT to API bridge for telemetry data with Vault PKI support"""
    
    def __init__(self, mqtt_host="localhost", mqtt_port=8884, api_base_url="http://localhost:5566", use_tls=True):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port  # Default to secure port 8884
        self.api_base_url = api_base_url
        self.use_tls = use_tls
        self.client = None
        self.running = False
        
        # MQTT Authentication - Use MQTT_BRIDGE_PASSWORD which matches API auth service
        self.mqtt_username = os.environ.get('MQTT_USERNAME', 'mqtt-bridge')
        self.mqtt_password = os.environ.get('MQTT_BRIDGE_PASSWORD', os.environ.get('MQTT_PASSWORD', ''))

        # API service-account credentials: REQUIRED, no insecure defaults.
        self.api_user = os.environ.get('BRIDGE_API_USER')
        self.api_password = os.environ.get('BRIDGE_API_PASSWORD')
        if not self.api_user or not self.api_password:
            raise SystemExit(
                "FATAL: BRIDGE_API_USER and BRIDGE_API_PASSWORD environment "
                "variables must be set (see .env.example). Refusing to start "
                "without API service credentials."
            )

        # API Authentication
        self.api_token = None
        self.api_token_expiry = None
        # Re-authenticate this many seconds before the token's exp claim.
        self.token_refresh_margin = int(os.environ.get('TOKEN_REFRESH_MARGIN_SECONDS', '300'))
        # Fallback assumed token lifetime when the JWT has no readable exp.
        self.token_fallback_ttl = int(os.environ.get('API_TOKEN_FALLBACK_TTL_SECONDS', str(23 * 60 * 60)))
        
        # Certificate paths (when using Vault PKI)
        self.cert_dir = os.environ.get('MQTT_CERT_DIR', '/vault/certs')
        self.cert_file = os.environ.get('MQTT_CERT_FILE', f'{self.cert_dir}/server.crt')
        self.key_file = os.environ.get('MQTT_KEY_FILE', f'{self.cert_dir}/server.key')
        self.ca_file = os.environ.get('MQTT_CA_FILE', f'{self.cert_dir}/ca.crt')
        
        # Stats
        self.messages_received = 0
        self.messages_forwarded = 0
        self.errors = 0
        
        # Setup signal handlers for certificate reload
        signal.signal(signal.SIGHUP, self.handle_cert_reload)
        
    def handle_cert_reload(self, signum, frame):
        """Handle certificate reload signal from Vault agent"""
        logger.info("🔄 Received certificate reload signal (SIGHUP)")
        if self.client and self.client.is_connected():
            logger.info("🔌 Disconnecting to reload certificates...")
            self.client.disconnect()
            # The on_disconnect callback will handle reconnection with new certs
        
    def verify_certificates(self):
        """Verify that certificate files exist and are valid"""
        if not self.use_tls:
            return True
            
        # Check if certificate files exist
        cert_files = {
            "Certificate": self.cert_file,
            "Private Key": self.key_file,
            "CA Certificate": self.ca_file
        }
        
        all_exist = True
        for name, path in cert_files.items():
            if os.path.exists(path):
                logger.info(f"✅ {name} found: {path}")
                # Check file permissions
                stat_info = os.stat(path)
                logger.debug(f"   Permissions: {oct(stat_info.st_mode)[-3:]}")
            else:
                logger.info(f"ℹ️  {name} not found: {path} - will use server-only TLS")
                all_exist = False
                
        if all_exist:
            # Verify certificate validity
            try:
                import subprocess
                # Check certificate expiration
                result = subprocess.run(
                    ['openssl', 'x509', '-enddate', '-noout', '-in', self.cert_file],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    logger.info(f"📅 Certificate validity: {result.stdout.strip()}")
                    
                # Verify certificate chain
                result = subprocess.run(
                    ['openssl', 'verify', '-CAfile', self.ca_file, self.cert_file],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    logger.info("✅ Certificate chain verification passed")
                else:
                    logger.warning(f"⚠️  Certificate chain verification: {result.stderr}")
                    
            except Exception as e:
                logger.warning(f"⚠️  Could not verify certificates: {e}")
                
        return all_exist
        
    def get_certificate_common_name(self):
        """Extract Common Name from certificate for client ID"""
        try:
            if os.path.exists(self.cert_file):
                import subprocess
                result = subprocess.run(
                    ['openssl', 'x509', '-noout', '-subject', '-in', self.cert_file],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    # Extract CN from subject line
                    subject = result.stdout.strip()
                    if 'CN=' in subject:
                        cn = subject.split('CN=')[1].split('/')[0].strip()
                        return cn
        except Exception as e:
            logger.warning(f"Could not extract CN from certificate: {e}")
        
        # Fallback to hostname-based client ID
        hostname = socket.gethostname()
        return f"mqtt-bridge-{hostname}"
        
    def authenticate_api(self):
        """Authenticate with API and get JWT token with retry logic"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                auth_url = f"{self.api_base_url}/api/v1/auth/login"

                logger.info(f"🔑 Attempting API authentication (attempt {attempt + 1}/{max_retries})...")
                logger.debug(f"   Auth URL: {auth_url}")
                logger.debug(f"   Service User: {self.api_user}")

                response = requests.post(
                    auth_url,
                    json={
                        "email": self.api_user,
                        "password": self.api_password
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    self.api_token = data.get('token')
                    if not self.api_token:
                        logger.error("❌ Authentication response missing token")
                        continue

                    # Derive expiry from the JWT's own exp claim (refresh a
                    # safety margin earlier); fall back to a configurable TTL
                    # when the token carries no readable exp.
                    exp = decode_jwt_exp(self.api_token)
                    if exp:
                        self.api_token_expiry = exp - self.token_refresh_margin
                    else:
                        logger.warning("⚠️  Could not read exp claim from token; using fallback TTL")
                        self.api_token_expiry = time.time() + self.token_fallback_ttl
                    logger.info("✅ Successfully authenticated with API")
                    logger.debug(f"   Token refresh scheduled at: {datetime.fromtimestamp(self.api_token_expiry).isoformat()}")
                    return True
                else:
                    logger.error(f"❌ API authentication failed: {response.status_code} - {response.text}")
                    if response.status_code == 401:
                        logger.error("   Check BRIDGE_API_USER and BRIDGE_API_PASSWORD environment variables")
                    if attempt < max_retries - 1:
                        logger.info(f"   Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    
            except requests.exceptions.Timeout:
                logger.error(f"⏰ Authentication request timed out (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
            except requests.exceptions.ConnectionError as e:
                logger.error(f"🔌 Connection error during authentication (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
            except Exception as e:
                logger.error(f"❌ Unexpected error during authentication (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
        
        logger.error(f"❌ Failed to authenticate after {max_retries} attempts")
        return False
    
    def ensure_authenticated(self):
        """Ensure we have a valid API token"""
        # Check if token exists and is not expired
        if not self.api_token or (self.api_token_expiry and time.time() >= self.api_token_expiry):
            logger.info("🔑 API token missing or expired, re-authenticating...")
            return self.authenticate_api()
        return True

    def api_request(self, method, url, json_payload, timeout=10):
        """Send an authenticated request to the API.

        On a 401 response the cached token is invalidated, authentication is
        re-run once, and the request is retried a single time.
        Returns the final requests.Response, or None when authentication failed.
        """
        if not self.ensure_authenticated():
            logger.error("❌ Failed to authenticate with API")
            return None

        for retry in range(2):
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_token}'
            }
            response = requests.request(method, url, json=json_payload,
                                        headers=headers, timeout=timeout)
            if response.status_code == 401 and retry == 0:
                logger.warning("🔑 API returned 401 - invalidating token and re-authenticating once...")
                self.api_token = None
                self.api_token_expiry = None
                if not self.authenticate_api():
                    logger.error("❌ Re-authentication after 401 failed")
                    return response
                continue
            return response
        return response

    def connect_mqtt(self):
        """Connect to MQTT broker with TLS using Vault-issued certificates"""
        # Use certificate CN as client ID, or fall back to a unique identifier
        client_id = self.get_certificate_common_name()
        self.client = mqtt.Client(client_id=client_id)
        
        # Set username and password if provided
        if self.mqtt_username and self.mqtt_password:
            logger.info(f"🔑 Using MQTT authentication with username: {self.mqtt_username}")
            self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        else:
            logger.warning("⚠️  MQTT_PASSWORD not set - connection may fail if broker requires authentication")
        
        # Configure TLS for secure connection
        if self.use_tls:
            logger.info("🔐 Configuring TLS...")

            # Check if we have client certificates
            have_client_certs = self.verify_certificates()

            # Explicit, opt-in escape hatch ONLY. Never silently disable
            # certificate verification.
            tls_insecure = os.environ.get('MQTT_TLS_INSECURE', '').lower() == 'true'

            # Hostname verification toggle. Default is OFF because the
            # vault-agent EMQX server certificate is issued with
            # EMQX_CERT_CN/EMQX_CERT_ALT_NAMES which default to
            # "localhost,mqtt.localhost" (see .env.example) — the internal
            # Docker DNS name "tesa-emqx" is NOT in the SANs, so strict
            # hostname verification would always fail in-cluster.
            # The certificate CHAIN is still fully verified against the CA
            # (cert_reqs=CERT_REQUIRED). To enable full verification, add
            # "tesa-emqx" to EMQX_CERT_ALT_NAMES and set
            # MQTT_TLS_VERIFY_HOSTNAME=true.
            verify_hostname = os.environ.get('MQTT_TLS_VERIFY_HOSTNAME', 'false').lower() == 'true'

            try:
                if tls_insecure:
                    # WARNING: no server certificate verification at all.
                    logger.warning("⚠️  MQTT_TLS_INSECURE=true - server certificate verification DISABLED. "
                                   "Do NOT use this outside isolated development environments.")
                    self.client.tls_set(
                        ca_certs=None,
                        certfile=self.cert_file if have_client_certs else None,
                        keyfile=self.key_file if have_client_certs else None,
                        cert_reqs=ssl.CERT_NONE,
                        tls_version=ssl.PROTOCOL_TLS_CLIENT,
                        ciphers=None
                    )
                    self.client.tls_insecure_set(True)
                elif os.path.exists(self.ca_file):
                    # Verify the broker certificate against the platform CA.
                    self.client.tls_set(
                        ca_certs=self.ca_file,
                        certfile=self.cert_file if have_client_certs else None,
                        keyfile=self.key_file if have_client_certs else None,
                        cert_reqs=ssl.CERT_REQUIRED,
                        tls_version=ssl.PROTOCOL_TLS_CLIENT,
                        ciphers=None
                    )
                    if verify_hostname:
                        self.client.tls_insecure_set(False)
                        logger.info("✅ TLS: CA chain + hostname verification enabled")
                    else:
                        # Chain is verified; hostname check skipped (SAN gap,
                        # see comment above). tls_insecure_set(True) with
                        # CERT_REQUIRED only disables the hostname match.
                        self.client.tls_insecure_set(True)
                        logger.warning("⚠️  TLS: CA chain verified, hostname verification SKIPPED "
                                       "(broker cert SANs default to localhost; add 'tesa-emqx' to "
                                       "EMQX_CERT_ALT_NAMES and set MQTT_TLS_VERIFY_HOSTNAME=true to enable)")
                    if have_client_certs:
                        logger.info("🔐 mTLS: presenting client certificate")
                        logger.info(f"   - Certificate: {self.cert_file}")
                        logger.info(f"   - Private Key: {self.key_file}")
                    logger.info(f"   - CA: {self.ca_file}")
                else:
                    # No platform CA file available: fall back to the system
                    # trust store with full verification. This will fail for
                    # a private/internal CA - fail loud instead of silently
                    # disabling verification.
                    logger.warning(f"⚠️  CA file {self.ca_file} not found - using system trust store "
                                   "with full verification. If the broker uses the internal Vault CA, "
                                   "set MQTT_CA_FILE to the CA bundle path.")
                    self.client.tls_set(
                        ca_certs=None,
                        certfile=None,
                        keyfile=None,
                        cert_reqs=ssl.CERT_REQUIRED,
                        tls_version=ssl.PROTOCOL_TLS_CLIENT,
                        ciphers=None
                    )
                    self.client.tls_insecure_set(False)

                logger.info(f"   - Client ID: {client_id}")

            except Exception as e:
                logger.error(f"❌ Failed to configure TLS: {e}")
                return False
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                protocol = "MQTTs (TLS)" if self.use_tls else "MQTT"
                logger.info(f"✅ Connected to MQTT broker at {self.mqtt_host}:{self.mqtt_port} via {protocol}")
                touch_health_file()
                logger.info(f"🔐 Connection details: TLS={self.use_tls}, Port={self.mqtt_port}, Username={self.mqtt_username}")
                
                # Subscribe to all device telemetry topics (supporting both device/ and devices/ patterns)
                # Support singular "device" pattern used by PSoC devices
                client.subscribe("device/+/telemetry/+", qos=1)  # PSoC pattern with sensor type
                client.subscribe("device/+/telemetry", qos=1)    # PSoC pattern without sensor type
                client.subscribe("device/+/data/+", qos=1)
                client.subscribe("device/+/status", qos=1) 
                client.subscribe("device/+/heartbeat", qos=1)
                
                # Also support plural "devices" pattern for backward compatibility
                client.subscribe("devices/+/telemetry", qos=1)
                client.subscribe("devices/+/data/+", qos=1)
                client.subscribe("devices/+/status", qos=1) 
                client.subscribe("devices/+/heartbeat", qos=1)
                
                logger.info("📡 Subscribed to telemetry topics: device/+/telemetry/+, device/+/telemetry, device/+/data/+, device/+/status, device/+/heartbeat (and devices/... patterns)")
            else:
                logger.error(f"❌ Failed to connect to MQTT broker, return code {rc}")
                # Common return codes:
                # 1: Connection refused - incorrect protocol version
                # 2: Connection refused - invalid client identifier
                # 3: Connection refused - server unavailable
                # 4: Connection refused - bad username or password
                # 5: Connection refused - not authorized
                if rc == 4:
                    logger.error("❌ Authentication failed - check MQTT_USERNAME and MQTT_PASSWORD")
                elif rc == 5:
                    logger.error("❌ Not authorized - check user permissions")
        
        def on_disconnect(client, userdata, rc):
            # IMPORTANT: never block here - this runs on paho's network
            # thread. Reconnection is handled by paho's own loop using the
            # backoff configured via reconnect_delay_set() below.
            logger.warning(f"🔌 Disconnected from MQTT broker (rc: {rc})")
            if self.running and rc != 0:
                logger.info("🔄 paho network loop will reconnect automatically (1-30s backoff)")

        def on_message(client, userdata, msg):
            self.handle_telemetry_message(msg)
            
        def on_subscribe(client, userdata, mid, granted_qos):
            logger.info(f"📬 Subscription confirmed with QoS {granted_qos}")
            
        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_message = on_message
        self.client.on_subscribe = on_subscribe

        # Automatic reconnect with exponential backoff, handled by paho's
        # network loop instead of sleeping inside the on_disconnect callback.
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        try:
            logger.info(f"🔌 Connecting to MQTT broker at {self.mqtt_host}:{self.mqtt_port}...")
            self.client.connect(self.mqtt_host, self.mqtt_port, 60)
            return True
        except ssl.SSLError as e:
            logger.error(f"❌ TLS/SSL connection failed: {e}")
            logger.error("   Check that the broker is configured for TLS on port 8884")
            return False
        except ConnectionRefusedError as e:
            logger.error(f"❌ Connection refused: {e}")
            logger.error(f"   Check that EMQX is running and listening on {self.mqtt_host}:{self.mqtt_port}")
            return False
        except Exception as e:
            logger.error(f"❌ MQTT connection failed: {e}")
            return False
    
    def handle_telemetry_message(self, msg):
        """Process incoming telemetry message"""
        try:
            self.messages_received += 1

            # Cap payload size BEFORE any parsing/logging to avoid memory
            # blow-ups and log flooding from misbehaving devices.
            if len(msg.payload) > MAX_PAYLOAD_BYTES:
                logger.warning(f"⚠️  Dropping oversize payload on {msg.topic}: "
                               f"{len(msg.payload)} bytes > MAX_PAYLOAD_BYTES={MAX_PAYLOAD_BYTES}")
                self.errors += 1
                return

            # Extract device ID from topic (device(s)/{device_id}/telemetry or device(s)/{device_id}/data/{sensor})
            topic_parts = msg.topic.split('/')
            if len(topic_parts) < 3 or topic_parts[0] not in ['device', 'devices']:
                logger.warning(f"⚠️  Invalid topic format: {msg.topic}")
                return
                
            device_id = topic_parts[1]
            message_type = topic_parts[2]  # telemetry, status, heartbeat
            
            # Parse JSON payload
            try:
                payload = json.loads(msg.payload.decode())
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON in message from {device_id}: {e}")
                self.errors += 1
                return
            
            logger.info(f"📨 Received {message_type} from {device_id}")
            logger.debug(f"📨 Payload: {json.dumps(payload, indent=2)}")
            
            # Forward to API
            if message_type == 'telemetry':
                success = self.forward_telemetry_to_api(device_id, payload)
            elif message_type == 'status':
                success = self.forward_status_to_api(device_id, payload)
            elif message_type == 'heartbeat':
                success = self.forward_heartbeat_to_api(device_id, payload)
            else:
                logger.warning(f"⚠️  Unknown message type: {message_type}")
                return
                
            if success:
                self.messages_forwarded += 1
                logger.info(f"✅ Forwarded {message_type} for {device_id} to API")
            else:
                self.errors += 1
                logger.error(f"❌ Failed to forward {message_type} for {device_id}")
                
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            self.errors += 1
    
    def forward_telemetry_to_api(self, device_id, payload):
        """Forward telemetry data to API"""
        try:
            # Fix the payload format for PSoC devices
            fixed_payload = fix_telemetry_payload(payload)
            
            # Log if any fixes were applied
            if fixed_payload != payload:
                logger.info(f"🔧 Applied format fixes for device {device_id}")
                logger.debug(f"   Original: {json.dumps(payload, indent=2)}")
                logger.debug(f"   Fixed: {json.dumps(fixed_payload, indent=2)}")
            
            # Flatten nested telemetry data for API compatibility
            flattened_data = flatten_telemetry_data(fixed_payload)
            
            # Log if flattening was needed
            if flattened_data != fixed_payload:
                logger.info(f"📊 Flattened nested telemetry data for device {device_id}")
                logger.debug(f"   Before flattening: {json.dumps(fixed_payload, indent=2)}")
                logger.debug(f"   After flattening: {json.dumps(flattened_data, indent=2)}")
            
            # Prepare telemetry data for general telemetry endpoint format
            api_payload = {
                "device_id": device_id,  # Required by /api/v1/telemetry endpoint
                "timestamp": datetime.now(timezone.utc).isoformat(),  # ISO timestamp with Z
                "data": flattened_data,  # Main telemetry data
                "metadata": {
                    "source": "mqtt_bridge_vault" if self.use_tls else "mqtt_bridge",
                    "bridge_timestamp": datetime.now().isoformat(),
                    "original_device_id": device_id,
                    "pki_enabled": self.use_tls,
                    "format_fixed": fixed_payload != payload,  # Track if fixes were applied
                    "data_flattened": flattened_data != fixed_payload  # Track if flattening was applied
                }
            }
            
            # Use the general telemetry endpoint that supports API key or mTLS authentication.
            # api_request() handles auth, 401-invalidate-and-retry-once, and headers.
            url = f"{self.api_base_url}/api/v1/telemetry"

            response = self.api_request('POST', url, api_payload)
            if response is None:
                return False

            if response.status_code in [200, 201]:
                logger.debug(f"✅ Telemetry forwarded successfully for {device_id}")
                return True
            else:
                logger.error(f"❌ API returned status {response.status_code}: {response.text}")
                # Log the request details for debugging
                logger.debug(f"   Request URL: {url}")
                logger.debug(f"   Request payload: {json.dumps(api_payload, indent=2)}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"⏰ Timeout forwarding telemetry for {device_id}")
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f"🔌 Connection error forwarding telemetry for {device_id}")
            return False
        except Exception as e:
            logger.error(f"❌ Error forwarding telemetry for {device_id}: {e}")
            return False
    
    def forward_status_to_api(self, device_id, payload):
        """Forward device status updates to API"""
        try:
            # Extract status information
            status = payload.get('status', 'unknown')
            
            # Update device status via API (device_id URL-encoded to prevent
            # path injection from attacker-controlled topic segments)
            url = f"{self.api_base_url}/api/v1/devices/{quote(device_id, safe='')}"

            api_payload = {
                "status": status,
                # UTC with offset to ensure correct local rendering
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "metadata": payload.get('metadata', {})
            }

            response = self.api_request('PUT', url, api_payload)
            if response is None:
                return False

            return response.status_code in [200, 201]
            
        except Exception as e:
            logger.error(f"❌ Error forwarding status for {device_id}: {e}")
            return False
    
    def forward_heartbeat_to_api(self, device_id, payload):
        """Forward device heartbeat to API"""
        try:
            # Simple heartbeat - just update last_seen (authenticated like the
            # other forwarders; device_id URL-encoded)
            url = f"{self.api_base_url}/api/v1/devices/{quote(device_id, safe='')}/heartbeat"

            api_payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system": payload.get('system', {}),
                "metadata": payload.get('metadata', {})
            }

            response = self.api_request('POST', url, api_payload)
            if response is None:
                return False

            return response.status_code in [200, 201, 404]  # 404 is OK if device doesn't exist yet
            
        except Exception as e:
            logger.error(f"❌ Error forwarding heartbeat for {device_id}: {e}")
            return False
    
    def stats_worker(self):
        """Print periodic statistics"""
        while self.running:
            time.sleep(60)  # Print stats every minute
            logger.info(f"📊 Bridge Stats: Received={self.messages_received}, Forwarded={self.messages_forwarded}, Errors={self.errors}")
            # Healthcheck heartbeat (also touched by the main loop while the
            # MQTT connection is up)
            if self.client and self.client.is_connected():
                touch_health_file()
            
            # Check certificate expiration
            if self.use_tls and os.path.exists(self.cert_file):
                try:
                    import subprocess
                    result = subprocess.run(
                        ['openssl', 'x509', '-enddate', '-noout', '-in', self.cert_file],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        logger.info(f"📅 Certificate status: {result.stdout.strip()}")
                except Exception:
                    pass
    
    def start_bridge(self):
        """Start the MQTT to API bridge"""
        logger.info("🚀 Starting MQTT Telemetry Bridge with TLS Support")
        logger.info(f"📡 MQTT Broker: {self.mqtt_host}:{self.mqtt_port}")
        logger.info(f"🌐 API Base URL: {self.api_base_url}")
        logger.info(f"🔐 TLS Enabled: {self.use_tls}")
        logger.info(f"👤 MQTT Username: {self.mqtt_username}")
        
        if self.use_tls:
            logger.info(f"📁 Certificate Directory: {self.cert_dir}")
        
        # Authenticate with API first
        logger.info("🔐 Authenticating with API...")
        if not self.authenticate_api():
            logger.error("❌ Failed to authenticate with API. Exiting.")
            return False
        
        if not self.connect_mqtt():
            logger.error("❌ Failed to connect to MQTT broker")
            return False
            
        self.running = True
        
        # Start statistics thread
        stats_thread = threading.Thread(target=self.stats_worker, daemon=True)
        stats_thread.start()
        
        try:
            # Start MQTT loop
            self.client.loop_start()
            
            logger.info("✅ MQTT Telemetry Bridge is running with TLS")
            logger.info("🔄 Data Flow: EMQX -> Bridge -> API -> MongoDB -> UI")
            logger.info("📱 Check telemetry in Admin Portal: https://localhost")
            logger.info(f"🔒 Using TLS on port {self.mqtt_port} with username authentication")
            logger.info("⏹️  Press Ctrl+C to stop")
            
            # Keep main thread alive; refresh the healthcheck heartbeat file
            # (~every 10s, well under the healthcheck's staleness window)
            # only while the MQTT connection is actually up.
            last_health_touch = 0.0
            while self.running:
                time.sleep(1)
                now = time.time()
                if now - last_health_touch >= 10 and self.client and self.client.is_connected():
                    touch_health_file()
                    last_health_touch = now

        except KeyboardInterrupt:
            logger.info("⏹️  Received interrupt signal, stopping bridge...")
            self.stop_bridge()
            
        return True
    
    def stop_bridge(self):
        """Stop the bridge"""
        self.running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        logger.info("🛑 MQTT Telemetry Bridge stopped")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="TESA IoT MQTT Telemetry Bridge with Vault PKI")
    parser.add_argument("--mqtt-host", default=os.environ.get('MQTT_HOST', 'localhost'), 
                       help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=int(os.environ.get('MQTT_PORT', '8884')), 
                       help="MQTT broker port (secure)")
    parser.add_argument("--api-url", default=os.environ.get('API_URL', 'http://localhost:5566'), 
                       help="API base URL")
    parser.add_argument("--no-tls", action="store_true", 
                       help="Disable TLS (use plain MQTT)")
    
    args = parser.parse_args()
    
    # Override with environment variable if set
    use_tls = not args.no_tls
    if os.environ.get('MQTT_USE_TLS', '').lower() == 'false':
        use_tls = False
    
    # Override port if no-tls is specified
    mqtt_port = args.mqtt_port
    if not use_tls and mqtt_port == 8884:  # If still default secure port
        mqtt_port = 1883    # Switch to non-secure port
    
    # Create and start bridge
    bridge = MQTTTelemetryBridge(
        mqtt_host=args.mqtt_host,
        mqtt_port=mqtt_port,
        api_base_url=args.api_url,
        use_tls=use_tls
    )
    
    bridge.start_bridge()

if __name__ == "__main__":
    main()
