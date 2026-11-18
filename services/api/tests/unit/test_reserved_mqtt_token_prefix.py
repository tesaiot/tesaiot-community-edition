# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors

"""A device id must not be able to talk its way into the fleet-wide subscribe.

``emqx_acl`` had a branch for "MQTT API token" clients: a username starting with
``tesa_mqtt_`` may subscribe to ``device/<any>/telemetry`` and ``devices/<any>/...``.
It was written for tokens that an Enterprise service issues. CE has no code that
issues one, and the branch keys on nothing but the username prefix. For a
``server_tls`` device the username must equal its device id, and the device-id
rule accepts ``tesa_mqtt_scene``; so registering a device with that id gave it the
branch.

Measured against a running CE before this file existed: a device registered as
``tesa_mqtt_scene`` connected over WSS, was granted ``device/+/telemetry`` and
received 56 messages from the 4 other devices that were publishing, in 70 s.

Two layers are held here, because either alone is one edit away from the bug:
the ACL no longer has the branch (a ``tesa_mqtt_`` client gets the ordinary
device ACL, which is its own topics only), and the id can no longer be registered.
The tests do not need a broker: the ACL route is called with the database lookup
replaced by what the ordinary device ACL would answer.
"""

import importlib.util
import os
import sys
import types

import pytest

flask = pytest.importorskip('flask')
pytest.importorskip('jsonschema')

_HERE = os.path.dirname(os.path.abspath(__file__))
_API_DIR = os.path.abspath(os.path.join(_HERE, '..', '..', 'api'))
SECRET = 'unit-test-webhook-secret'


@pytest.fixture(scope='module')
def emqx_auth():
    root = 'ce_api_resprefix'
    pkg = types.ModuleType(root)
    pkg.__path__ = [_API_DIR]
    sys.modules[root] = pkg
    for sub in ('controllers', 'core', 'services'):
        m = types.ModuleType(f'{root}.{sub}')
        m.__path__ = [os.path.join(_API_DIR, sub)]
        sys.modules[f'{root}.{sub}'] = m

    database = types.ModuleType(f'{root}.core.database')
    database.get_db = lambda: None
    database.get_vault = lambda: None
    sys.modules[f'{root}.core.database'] = database

    mqtt = types.ModuleType(f'{root}.services.mqtt_auth_service')
    mqtt.validate_mqtt_auth = lambda *a, **k: (False, None)
    mqtt.handle_mqtt_disconnect = lambda *a, **k: None
    mqtt.get_mqtt_auth_stats = lambda *a, **k: {}
    sys.modules[f'{root}.services.mqtt_auth_service'] = mqtt

    name = f'{root}.controllers.emqx_auth'
    spec = importlib.util.spec_from_file_location(name, os.path.join(_API_DIR, 'controllers', 'emqx_auth.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def acl(emqx_auth, monkeypatch):
    """POST the ACL webhook. `ordinary` is what the ordinary device ACL would answer for the client."""
    monkeypatch.setenv('EMQX_WEBHOOK_SECRET', SECRET)
    app = flask.Flask('acl')
    app.register_blueprint(emqx_auth.emqx_auth_bp)
    client = app.test_client()
    asked = []

    def ask(username, action, topic, ordinary=False, client_id=None):
        monkeypatch.setattr(emqx_auth, '_check_device_acl', lambda cid, act, top: (asked.append((cid, act, top)) or ordinary))
        r = client.post('/api/v1/emqx/acl', headers={'Authorization': f'Bearer {SECRET}'},
                        json={'clientid': client_id or username, 'username': username, 'action': action, 'topic': topic})
        return r.get_json()['result'], asked

    return ask


FLEET_TOPICS = ['device/+/telemetry', 'device/ag-valve-01/telemetry', 'devices/ag-valve-01/telemetry/temp', 'device/+/telemetry/#']


class TestNoUsernameIsAToken:

    @pytest.mark.parametrize('topic', FLEET_TOPICS)
    def test_a_tesa_mqtt_username_gets_no_fleet_subscribe(self, acl, topic):
        result, asked = acl('tesa_mqtt_scene', 'subscribe', topic, ordinary=False)
        assert result == 'deny'
        assert asked, 'the ordinary device ACL is what decided it'

    def test_the_answer_is_the_ordinary_ACLs_not_a_special_case(self, acl):
        # the same client may do what any device may do: its own topic, as the ordinary ACL says
        assert acl('tesa_mqtt_scene', 'subscribe', 'devices/tesa_mqtt_scene/commands', ordinary=True)[0] == 'allow'
        assert acl('tesa_mqtt_scene', 'publish', 'devices/tesa_mqtt_scene/telemetry', ordinary=True)[0] == 'allow'
        assert acl('tesa_mqtt_scene', 'publish', 'devices/someone-else/telemetry', ordinary=False)[0] == 'deny'

    def test_a_longer_or_differently_cased_prefix_is_no_different(self, acl):
        for u in ('tesa_mqtt_', 'tesa_mqtt_x' * 4, 'TESA_MQTT_scene'):
            assert acl(u, 'subscribe', 'device/+/telemetry', ordinary=False)[0] == 'deny', u


class TestTheIdCannotBeRegistered:

    @pytest.fixture(scope='class')
    def validation(self):
        spec = importlib.util.spec_from_file_location('validation_under_test', os.path.join(_API_DIR, 'utils', 'validation.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @pytest.mark.parametrize('device_id', ['tesa_mqtt_scene', 'tesa_mqtt_', 'TESA_MQTT_scene', 'Tesa_Mqtt_x1'])
    def test_the_reserved_prefix_is_refused(self, validation, device_id):
        assert validation.validate_device_id(device_id) is False

    @pytest.mark.parametrize('device_id', ['ag-valve-01', 'sensor_10', 'tesa-mqtt-scene', 'my_tesa_mqtt_probe', 'tesa_mqttx', '550e8400-e29b-41d4-a716-446655440000'])
    def test_ordinary_ids_still_pass(self, validation, device_id):
        assert validation.validate_device_id(device_id) is True
