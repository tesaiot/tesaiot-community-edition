# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

import os
import hashlib
from flask import Blueprint, jsonify

build_info_bp = Blueprint('build_info', __name__)


def _sha256_file(path):
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


@build_info_bp.route('/info', methods=['GET'])
def build_info():
    """
    Return build/version info and hashes for key files to prove code provenance.
    Safe for production (no secrets).
    """
    # Compute hashes of critical API files
    base_dir = os.path.dirname(os.path.dirname(__file__))  # .../api
    files = {
        'api/__init__.py': os.path.join(base_dir, '__init__.py'),
        'api/controllers/certificate_download_routes.py': os.path.join(base_dir, 'controllers', 'certificate_download_routes.py'),
        'api/services/certificate_service.py': os.path.join(base_dir, 'services', 'certificate_service.py'),
    }
    file_hashes = {rel: _sha256_file(path) for rel, path in files.items()}

    # Version and build metadata
    from .. import API_VERSION, BUILD_DATE  # from api.__init__
    build_hash = os.getenv('BUILD_HASH')  # if passed during docker build

    return jsonify({
        'version': API_VERSION,
        'build_date': BUILD_DATE,
        'build_hash': build_hash,
        'file_hashes': file_hashes,
    }), 200
