# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESAIoT Community Edition - API entry point.

Uses the Flask application factory pattern. Run with: python -m api.app
"""

import os
import sys
import logging

# Ensure the package root (the directory containing the `api/` package) is on
# sys.path so `from utils.secret_manager import ...` style imports resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import create_app, API_VERSION, BUILD_DATE  # noqa: E402

ENV = os.getenv('FLASK_ENV', 'production')
PORT = int(os.getenv('API_PORT', '5566'))
HOST = os.getenv('API_HOST', '0.0.0.0')

app = create_app(ENV)


@app.route('/')
def index():
    return {
        'service': 'TESAIoT Community Edition API',
        'version': API_VERSION,
        'build': BUILD_DATE,
        'status': 'running',
        'endpoints': {
            'health': '/api/v1/health',
            'auth': '/api/v1/auth/login',
            'devices': '/api/v1/devices',
            'certificates': '/api/v1/certificates',
        },
    }


@app.route('/version')
def version():
    # SECURITY: app version only. Runtime details (Python version, environment)
    # aid attacker fingerprinting and are not returned.
    return {
        'api_version': API_VERSION,
    }


if __name__ == '__main__':
    logging.getLogger(__name__).info(
        f"TESAIoT Community Edition API {API_VERSION} starting on {HOST}:{PORT} ({ENV})"
    )
    app.run(
        host=HOST,
        port=PORT,
        debug=(ENV == 'development'),
        use_reloader=(ENV == 'development'),
    )
