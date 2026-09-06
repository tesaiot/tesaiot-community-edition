# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors

"""A client certificate authenticates the device it was issued to, and no other.

certificate_service.py forces the certificate CN to the device id at issuance,
so the webhook's job is a comparison. It used to be

    client_id in peer_cert_cn or peer_cert_cn.startswith(client_id)

which is a containment test. Measured against a live broker before this file
existed: sensor-10's own genuine, correctly-issued certificate connected with
client_id=sensor-1, received CONNACK 0, published to device/sensor-1/telemetry
and subscribed to device/sensor-1/commands. Any device id that is a substring or
prefix of another's was a key to that other device.

These cases are the ones that distinguish equality from containment; a test that
only checked sensor-1 against sensor-1 would have passed against the bug.
"""

import importlib.util
import os
import sys
import types

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_API_DIR = os.path.abspath(os.path.join(_HERE, '..', '..', 'api'))


@pytest.fixture(scope='module')
def mqtt_auth():
    """Load mqtt_auth_service with a stub for the one package import it makes."""
    root = 'ce_api_cn_binding'
    pkg = types.ModuleType(root)
    pkg.__path__ = [_API_DIR]
    sys.modules[root] = pkg

    core = types.ModuleType(f'{root}.core')
    core.__path__ = [os.path.join(_API_DIR, 'core')]
    sys.modules[f'{root}.core'] = core

    database = types.ModuleType(f'{root}.core.database')
    database.get_db = lambda: None
    database.get_vault = lambda: None
    sys.modules[f'{root}.core.database'] = database

    services = types.ModuleType(f'{root}.services')
    services.__path__ = [os.path.join(_API_DIR, 'services')]
    sys.modules[f'{root}.services'] = services

    name = f'{root}.services.mqtt_auth_service'
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(_API_DIR, 'services', 'mqtt_auth_service.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestTheDeviceItsCertificateWasIssuedTo:
    def test_a_device_authenticates_as_itself(self, mqtt_auth):
        assert mqtt_auth._cn_matches_device_id('sensor-1', 'sensor-1') is True

    def test_a_longer_id_does_not_authenticate_as_its_prefix(self, mqtt_auth):
        # The reproduction: cert CN=sensor-10, connecting as sensor-1.
        assert mqtt_auth._cn_matches_device_id('sensor-10', 'sensor-1') is False

    def test_a_prefix_does_not_authenticate_as_the_longer_id(self, mqtt_auth):
        assert mqtt_auth._cn_matches_device_id('sensor-1', 'sensor-10') is False

    @pytest.mark.parametrize('cn,client_id', [
        ('plant-a-pump-3', 'pump-3'),        # containment anywhere in the string
        ('gw-01-sensor', 'gw-01'),           # prefix
        ('sensor', 'sensor-1'),              # the other direction
        ('SENSOR-1', 'sensor-1'),            # a device id is not case-folded
        ('sensor-1 ', 'sensor-1'),           # trailing space is a different id
    ])
    def test_near_misses_are_refused(self, mqtt_auth, cn, client_id):
        assert mqtt_auth._cn_matches_device_id(cn, client_id) is False

    @pytest.mark.parametrize('cn,client_id', [
        ('', 'sensor-1'),
        ('sensor-1', ''),
        (None, 'sensor-1'),
        ('sensor-1', None),
        (None, None),
    ])
    def test_absent_values_never_authenticate(self, mqtt_auth, cn, client_id):
        assert mqtt_auth._cn_matches_device_id(cn, client_id) is False
