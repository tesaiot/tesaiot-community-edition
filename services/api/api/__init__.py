# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESAIoT Community Edition - API

Flask application factory for the single-organization, self-host distribution.
In scope: user management, device/identity management, certificate lifecycle via
HashiCorp Vault PKI, EMQX MQTT auth/ACL webhooks, and the IoT Telemetry
Dashboard (system-health and telemetry metrics served by
services/realtime_analytics_service.py and the dashboard module), plus health.

Out of scope: OTA/firmware, AI inference, the predictive/AI "analytics" product
module, B2B/WebSocket-B2B, billing/packages/usage, and multi-tenant organization
management (collapsed to a single default org exposed read-only) and the
multi-tenant sub-organization hierarchy. Where excluded subsystems were
referenced by in-scope dashboard endpoints, they are replaced with no-op
Apache-2.0 stubs (e.g. modules/analytics/utils/performance_optimizer.py) so
the dashboard stays operational without pulling in the excluded code.
"""

import os
import logging
from datetime import datetime

from flask import Flask, g, jsonify, request, redirect
from flask_cors import CORS

from .core.config import Config
from .core.database import init_databases, db_manager
from .core.exceptions import setup_error_handlers
from .core.logging import setup_logging
from .core.auth import require_auth

# In-scope blueprints
from .controllers.auth import auth_bp
from .controllers.auth_profile_endpoints import auth_profile_bp
from .controllers.otp_auth import otp_auth_bp
from .controllers.users import users_bp
from .controllers.organizations_bp import organizations_bp
from .controllers.devices import devices_bp
from .controllers.device_auth import device_auth_bp
from .controllers.device_api_key import device_api_key_bp
from .controllers.device_credentials import device_credentials_bp
from .controllers.device_api import device_api_bp
from .controllers.device_groups import device_groups_bp, init_device_groups_controller
from .controllers.certificates import certificates_bp
from .controllers.dashboard import dashboard_bp
from .controllers.telemetry import telemetry_bp
from .controllers.emqx_auth import emqx_auth_bp
from .controllers.logs import logs_bp
from .controllers.realtime import realtime_bp
from .controllers.metrics import metrics_bp
from .controllers import metrics as metrics_module

# Optional / best-effort blueprints (guarded)
try:
    from .controllers.emqx_events_webhook import emqx_webhook_bp
except Exception:
    emqx_webhook_bp = None

try:
    from .controllers.device_logs import device_logs_bp
except Exception:
    device_logs_bp = None

try:
    from .controllers.internal_service import internal_service_bp
except Exception:
    internal_service_bp = None

try:
    from .controllers.pool_monitoring import pool_monitoring_bp
except Exception:
    pool_monitoring_bp = None

socketio = None


def get_version():
    try:
        version_paths = [
            os.path.join(os.path.dirname(__file__), '../../VERSION.txt'),
            os.path.join(os.path.dirname(__file__), '../VERSION.txt'),
            '/app/VERSION.txt',
            'VERSION.txt',
        ]
        for path in version_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    version = f.read().strip()
                    if version:
                        return version
        return "ce-1.0.0"
    except Exception as e:
        logging.warning(f"Failed to read VERSION.txt: {e}")
        return "ce-1.0.0"


API_VERSION = get_version()
BUILD_DATE = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def _resolve_cors_origins():
    """Resolve the CORS origin allowlist from the environment (fail-closed).

    Priority:
      1. CORS_ALLOWED_ORIGINS - comma-separated explicit allowlist
      2. Derived from the deployment's own identity:
         TESA_PUBLIC_API_BASE_URL origin and https://DOMAIN / http://DOMAIN

    NEVER defaults to '*': combining a wildcard with supports_credentials
    lets any website ride the user's session. An empty list simply disables
    cross-origin access (same-origin requests are unaffected).
    """
    logger = logging.getLogger(__name__)

    raw = os.getenv('CORS_ALLOWED_ORIGINS', '').strip()
    if raw:
        origins = [o.strip().rstrip('/') for o in raw.split(',') if o.strip()]
        if '*' in origins:
            logger.warning(
                "CORS_ALLOWED_ORIGINS contains '*'. Credentials support is "
                "DISABLED for wildcard origins; set explicit origins instead."
            )
        return origins

    origins = []
    base_url = os.getenv('TESA_PUBLIC_API_BASE_URL', '').strip()
    if base_url:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            if parsed.scheme and parsed.netloc:
                origins.append(f"{parsed.scheme}://{parsed.netloc}")
        except Exception:
            pass
    domain = os.getenv('DOMAIN', '').strip()
    if domain:
        origins.extend([f"https://{domain}", f"http://{domain}"])

    # De-duplicate preserving order
    seen = set()
    origins = [o for o in origins if not (o in seen or seen.add(o))]
    if not origins:
        logger.warning(
            "No CORS origins configured (set CORS_ALLOWED_ORIGINS or DOMAIN / "
            "TESA_PUBLIC_API_BASE_URL); cross-origin browser access is disabled."
        )
    return origins


def create_app(config_name='production'):
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # Resolve the effective configuration name from FLASK_ENV when present so a
    # single source drives both config selection and security validation.
    config_name = os.getenv('FLASK_ENV') or config_name
    app.config.from_object(Config.get_config(config_name))

    # SECURITY: validate_security_config never ran (from_object loads the class
    # without instantiating it, so __init__ was dead code). Call it explicitly
    # and fail CLOSED on missing/weak/CHANGEME* secrets before the app boots.
    Config.validate_security_config(config_name)

    setup_logging(app)
    logger = logging.getLogger(__name__)
    logger.info(f"Initializing TESAIoT Community Edition API {API_VERSION}")
    logger.info(f"Build Date: {BUILD_DATE}")
    logger.info(f"Configuration: {config_name}")

    # SECURITY: env-driven CORS allowlist. The previous configuration combined
    # origins=['*'] with supports_credentials=True, which lets any website make
    # credentialed requests against the API. Credentials are only enabled when
    # the allowlist is explicit (no wildcard).
    cors_origins = _resolve_cors_origins()
    cors_supports_credentials = bool(cors_origins) and '*' not in cors_origins
    CORS(
        app,
        origins=cors_origins,
        allow_headers=[
            'Content-Type', 'Authorization', 'X-API-KEY', 'x-request-id',
            'x-requested-with', 'X-Device-API-Key', 'X-Device-ID', 'X-Device-UUID',
            'X-Device-Signature', 'X-Gateway-API-Key', 'X-Organization-API-Key',
            'X-Timestamp', 'X-Nonce', 'X-Proxy-App-Version',
        ],
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        supports_credentials=cors_supports_credentials,
    )
    logger.info(
        f"CORS configured: origins={cors_origins or '[] (cross-origin disabled)'} "
        f"credentials={cors_supports_credentials}"
    )

    with app.app_context():
        init_databases(app)
        try:
            from .core.di_container import register_modular_services
            register_modular_services(app)
            logger.info("Dependency injection container initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize DI container: {e}")

        # Initialize Device Groups Service
        try:
            init_device_groups_controller(db_manager.mongo_db)
            logger.info("Device Groups Service initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Device Groups Service: {e}")

    setup_error_handlers(app)

    from .services.logging_service import LoggingMiddleware
    LoggingMiddleware(app)

    from .middleware.audit_middleware import AuditMiddleware
    AuditMiddleware(app)

    # ============================================================
    # FastAPI Integration for Device Management Module
    # (backs the IoT Telemetry Dashboard inside Device Details)
    # ============================================================
    logger.info("Initializing FastAPI Device Management module...")
    try:
        from fastapi import FastAPI
        from a2wsgi import ASGIMiddleware
        from werkzeug.middleware.dispatcher import DispatcherMiddleware
        from .modules.device_management.routes import device_management_router

        fastapi_app = FastAPI(
            title="TESAIoT Community Edition Device Management API",
            version=API_VERSION,
            description="Device Management with telemetry endpoints",
        )
        fastapi_app.include_router(device_management_router)

        # Mirror the Flask app's env-driven CORS allowlist on the FastAPI
        # mount (it previously had no CORS middleware at all).
        try:
            from fastapi.middleware.cors import CORSMiddleware
            fastapi_app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_origins,
                allow_credentials=cors_supports_credentials,
                allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
                allow_headers=[
                    'Content-Type', 'Authorization', 'X-API-KEY', 'x-request-id',
                    'x-requested-with', 'X-Device-API-Key', 'X-Device-ID',
                ],
            )
        except Exception as cors_err:
            logger.warning(f"Failed to add CORS middleware to FastAPI mount: {cors_err}")

        class PathFixMiddleware:
            """Fix a2wsgi path handling when used with DispatcherMiddleware."""

            def __init__(self, app, strip_prefix: str):
                self.app = app
                self.strip_prefix = strip_prefix

            async def __call__(self, scope, receive, send):
                if scope['type'] == 'http':
                    path = scope.get('path', '')
                    if path.startswith(self.strip_prefix):
                        scope = scope.copy()
                        scope['path'] = path[len(self.strip_prefix):] or '/'
                return await self.app(scope, receive, send)

        MOUNT_PATH = '/api/v1/device-management'
        fixed_fastapi = PathFixMiddleware(fastapi_app, MOUNT_PATH)
        app.wsgi_app = DispatcherMiddleware(
            app.wsgi_app,
            {MOUNT_PATH: ASGIMiddleware(fixed_fastapi)},
        )
        logger.info(f"FastAPI Device Management module mounted at {MOUNT_PATH}")
    except Exception as e:
        logger.warning(f"Failed to initialize FastAPI module: {e}")
        logger.warning("Device Management enhanced features will not be available")

    # ------------------------------------------------------------------
    # User management + auth
    # ------------------------------------------------------------------
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    from .controllers.ce_compat import ce_compat_bp
    app.register_blueprint(ce_compat_bp)
    app.register_blueprint(auth_profile_bp)
    app.register_blueprint(otp_auth_bp, url_prefix='/api/v1/auth/otp')
    app.register_blueprint(users_bp, url_prefix='/api/v1/users')
    app.register_blueprint(organizations_bp, url_prefix='/api/v1/organizations')

    @app.route('/api/v1/user/me')
    @require_auth
    def user_me_redirect():
        return redirect('/api/v1/users/me', code=302)

    # ------------------------------------------------------------------
    # Device & identity management
    # ------------------------------------------------------------------
    app.register_blueprint(devices_bp, url_prefix='/api/v1/devices')
    app.register_blueprint(device_auth_bp, url_prefix='/api/v1')
    app.register_blueprint(device_api_key_bp)
    app.register_blueprint(device_credentials_bp)
    app.register_blueprint(device_api_bp, url_prefix='/api/v1/device')
    app.register_blueprint(device_groups_bp)
    logger.info("Device & identity management blueprints registered")

    # ------------------------------------------------------------------
    # Certificate lifecycle (Vault PKI)
    # ------------------------------------------------------------------
    try:
        from .controllers.certificate_download_routes import cert_download_bp
        app.register_blueprint(cert_download_bp)
        logger.info("Certificate download routes registered")
    except Exception as e:
        logger.warning(f"Failed to register certificate download routes: {e}")

    app.register_blueprint(certificates_bp, url_prefix='/api/v1/certificates')
    try:
        from .controllers.certificates import download_certificate as _download_cert
        app.add_url_rule(
            '/api/v1/certificates/devices/<device_id>/certificate/download/<file_type>',
            endpoint='certificates_download_direct',
            view_func=_download_cert,
            methods=['GET'],
        )
    except Exception as e:
        logger.warning(f"Could not bind direct certificate download route: {e}")

    try:
        from .controllers.device_certificate_api import device_cert_api_bp
        app.register_blueprint(device_cert_api_bp)
        logger.info("Device certificate API registered")
    except Exception as e:
        logger.warning(f"Failed to register device certificate API: {e}")

    try:
        from .controllers.server_tls_bundle import server_tls_bundle_bp
        app.register_blueprint(server_tls_bundle_bp)
        logger.info("Server-TLS bundle endpoint registered")
    except Exception as e:
        logger.warning(f"Failed to register server-tls bundle endpoint: {e}")

    try:
        from .controllers.mqtt_quic_server_tls_bundle import mqtt_quic_server_tls_bundle_bp
        app.register_blueprint(mqtt_quic_server_tls_bundle_bp)
        logger.info("MQTT-QUIC server-TLS bundle endpoint registered")
    except Exception as e:
        logger.warning(f"Failed to register MQTT-QUIC bundle endpoint: {e}")

    # Certificate monitoring routes (health/expiring/alerts/renewal-candidates)
    try:
        from .routes_certificate_monitoring import register_certificate_monitoring_routes
        register_certificate_monitoring_routes(app)
        logger.info("Certificate monitoring routes registered")
    except Exception as e:
        logger.warning(f"Failed to register certificate monitoring routes: {e}")

    # ------------------------------------------------------------------
    # Telemetry / dashboard (read endpoints)
    # ------------------------------------------------------------------
    app.register_blueprint(dashboard_bp, url_prefix='/api/v1/dashboard')
    from copy import deepcopy
    dashboard_compat_bp = deepcopy(dashboard_bp)
    dashboard_compat_bp.name = 'dashboard_compat'
    app.register_blueprint(dashboard_compat_bp, url_prefix='/api/dashboard')
    app.register_blueprint(telemetry_bp)

    # ------------------------------------------------------------------
    # MQTT / EMQX auth + ACL webhooks
    # ------------------------------------------------------------------
    app.register_blueprint(emqx_auth_bp)
    if emqx_webhook_bp:
        app.register_blueprint(emqx_webhook_bp)
        logger.info("EMQX Events Webhook registered")
    if internal_service_bp:
        app.register_blueprint(internal_service_bp)
        logger.info("Internal Service API registered")
    if device_logs_bp:
        app.register_blueprint(device_logs_bp)
        logger.info("Enhanced Device Logs API registered")

    # ------------------------------------------------------------------
    # Observability (health, logs, metrics)
    # ------------------------------------------------------------------
    app.register_blueprint(logs_bp, url_prefix='/api/v1/logs')
    app.register_blueprint(realtime_bp)
    app.register_blueprint(metrics_bp)
    app.add_url_rule(
        '/api/metrics',
        endpoint='api_metrics_prometheus',
        view_func=metrics_module.prometheus_metrics,
    )
    app.add_url_rule(
        '/api/metrics/health',
        endpoint='api_metrics_health',
        view_func=metrics_module.health_check,
    )
    if pool_monitoring_bp:
        app.register_blueprint(pool_monitoring_bp)

    try:
        from .controllers.health_critical import health_critical_bp
        app.register_blueprint(health_critical_bp)
        logger.info("Critical health route registered")
    except Exception as e:
        logger.warning(f"Failed to register critical health route: {e}")

    try:
        from .controllers.build_info import build_info_bp
        app.register_blueprint(build_info_bp, url_prefix='/api/v1/build')
        logger.info("Build info route registered")
    except Exception as e:
        logger.warning(f"Failed to register build info route: {e}")

    # ------------------------------------------------------------------
    # Inline device-identity / api-key convenience routes
    # ------------------------------------------------------------------
    @app.route('/api/v1/device-identities')
    @require_auth
    def get_device_identities():
        try:
            from .services.device_service import get_devices_for_user
            devices = get_devices_for_user(g.current_user)
            identities = []
            for device in devices:
                identities.append({
                    'device_id': device.get('device_id'),
                    'name': device.get('name'),
                    'type': device.get('type'),
                    'status': device.get('status'),
                    'organization_id': device.get('organization_id'),
                    'last_seen': device.get('last_seen'),
                    'created_at': device.get('created_at'),
                })
            return jsonify({
                'device_identities': identities,
                'total': len(identities),
                'organization_id': g.current_user.get('organization_id'),
            }), 200
        except Exception as e:
            logger.error(f"Error getting device identities: {e}")
            return jsonify({'error': 'Failed to get device identities'}), 500

    @app.route('/api/v1/api-keys', methods=['GET'])
    @require_auth
    def get_api_keys():
        try:
            from .services.api_key_service import get_organization_api_keys
            org_id = g.current_user.get('organization_id')
            api_keys = get_organization_api_keys(org_id, g.current_user)
            return jsonify({
                'api_keys': api_keys,
                'total': len(api_keys),
                'organization_id': org_id,
            }), 200
        except Exception as e:
            logger.error(f"Error getting API keys: {e}")
            return jsonify({'error': 'Failed to get API keys'}), 500

    @app.route('/api/v1/api-keys', methods=['POST'])
    @require_auth
    def create_api_key():
        try:
            from .services.api_key_service import create_organization_api_key
            org_id = g.current_user.get('organization_id')
            data = request.get_json()
            if not data or not data.get('name'):
                return jsonify({'error': 'API key name is required'}), 400
            result = create_organization_api_key(org_id, data, g.current_user)
            if result.get('success'):
                return jsonify(result), 201
            return jsonify({'error': result.get('error', 'Failed to create API key')}), 400
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            return jsonify({'error': 'Failed to create API key'}), 500

    @app.route('/api/v1/api-keys/<key_id>', methods=['DELETE'])
    @require_auth
    def delete_api_key(key_id):
        try:
            from .services.api_key_service import revoke_organization_api_key
            org_id = g.current_user.get('organization_id')
            result = revoke_organization_api_key(org_id, key_id, g.current_user)
            if result.get('success'):
                return jsonify(result), 200
            error = result.get('error', 'Failed to revoke API key')
            if 'not found' in error.lower():
                return jsonify({'error': error}), 404
            return jsonify({'error': error}), 400
        except Exception as e:
            logger.error(f"Error deleting API key: {e}")
            return jsonify({'error': 'Failed to delete API key'}), 500

    # ------------------------------------------------------------------
    # Health + version
    # ------------------------------------------------------------------
    @app.route('/api/v1/health')
    def health_check():
        return {
            'status': 'healthy',
            'version': API_VERSION,
            'build': BUILD_DATE,
            'service': 'TESAIoT Community Edition API',
        }

    @app.route('/api/admin/system/health')
    def admin_health_check():
        return {
            'status': 'healthy',
            'version': API_VERSION,
            'build': BUILD_DATE,
            'service': 'TESAIoT Community Edition API',
            'timestamp': datetime.utcnow().isoformat(),
            'databases': {
                'mongodb': db_manager.mongo_db is not None or db_manager.use_enhanced_pooling,
                'redis': db_manager.redis_client is not None,
                'postgres': db_manager.postgres_pool is not None or db_manager.use_enhanced_pooling,
                'vault': db_manager.vault_client is not None,
                'enhanced_pooling': db_manager.use_enhanced_pooling,
            },
        }

    # ------------------------------------------------------------------
    # WebSocket telemetry (native)
    # ------------------------------------------------------------------
    global socketio
    socketio = None
    try:
        from .services.websocket_telemetry import init_websocket_telemetry_service
        ws_telemetry_service = init_websocket_telemetry_service(app)
        app.add_url_rule('/ws', 'websocket_telemetry',
                         ws_telemetry_service.handle_native_websocket, websocket=True)
        logger.info("WebSocket telemetry service initialized at /ws")

        @app.route('/api/v1/websocket/stats')
        @require_auth
        def websocket_stats():
            return ws_telemetry_service.get_connection_stats()
    except Exception as e:
        logger.warning(f"WebSocket telemetry service init failed: {e}")
        try:
            from .controllers.websocket_native import handle_websocket
            app.add_url_rule('/ws', 'websocket', handle_websocket, websocket=True)
            logger.info("Fallback native WebSocket endpoint registered at /ws")
        except Exception as e2:
            logger.warning(f"Fallback WebSocket endpoint failed: {e2}")

    # Provenance header
    import hashlib
    base_fp = f"{API_VERSION}|{BUILD_DATE}"
    fp_hex = hashlib.sha256(base_fp.encode('utf-8')).hexdigest()[:12]

    @app.after_request
    def add_fingerprint_header(response):
        try:
            response.headers['X-Build-Fingerprint'] = f"{API_VERSION}-{fp_hex}"
        except Exception:
            pass
        return response

    # Standard security headers on every Flask response (the FastAPI
    # device-management mount applies the equivalent set via its
    # DeviceSecurityHeadersMiddleware - this mirrors it for Flask routes).
    @app.after_request
    def add_security_headers(response):
        try:
            response.headers.setdefault('X-Content-Type-Options', 'nosniff')
            response.headers.setdefault('X-Frame-Options', 'DENY')
            response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
            # Auth endpoints return credentials/tokens: never cache them.
            if request.path.startswith('/api/v1/auth'):
                response.headers['Cache-Control'] = 'no-store'
                response.headers['Pragma'] = 'no-cache'
        except Exception:
            pass
        return response

    app.url_map.strict_slashes = False
    logger.info(f"API initialization complete - {len(app.url_map._rules)} routes registered")
    return app
