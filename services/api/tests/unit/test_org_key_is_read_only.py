# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors

"""An organisation API key can read; it must not write.

The synthetic principal an org key is bound to has role ``user``, which holds
only VIEW permissions, and the comment in ``_validate_api_key_request`` says an
org key "can read but not mutate". That is true only for routes that go through
``@require_permission``. The telemetry *ingest* routes are guarded by
``require_api_key``, ``require_api_key_or_mtls`` and ``require_telemetry_ingest``,
which call the same validator and never look at the role or the scopes, so a key
made for reading was accepted as a credential to write.

Measured against a running CE before this file existed: the key issued with the
default scopes (``devices:read telemetry:read organizations:read``) answered 200
to ``POST /api/v1/telemetry`` for a device it had no relation to, and the row
was stored.

The cases below separate the three write decorators from the one read decorator
that is meant to accept an org key, and keep the device key working on the write
routes: a fix that closed everything would pass the refusals and break ingest.

Flask and PyJWT are needed to build the routes; where they are not installed the
module is skipped, as the rest of this folder avoids importing the application.
"""

import importlib.util
import os
import sys
import types

import pytest

flask = pytest.importorskip('flask')
pytest.importorskip('jwt')

_HERE = os.path.dirname(os.path.abspath(__file__))
_API_DIR = os.path.abspath(os.path.join(_HERE, '..', '..', 'api'))

ORG_KEY = 'tesaiot_org_abc12345_' + 'a' * 32
DEVICE_KEY = 'tesa_dak_' + 'b' * 32


class _Collection:
    def update_one(self, *a, **k):
        return None


class _Db:
    api_keys = _Collection()
    devices = _Collection()


@pytest.fixture(scope='module')
def auth():
    """core/auth.py loaded by path with stubs for the database and the org-key store."""
    root = 'ce_api_orgkey'
    pkg = types.ModuleType(root)
    pkg.__path__ = [_API_DIR]
    sys.modules[root] = pkg

    core = types.ModuleType(f'{root}.core')
    core.__path__ = [os.path.join(_API_DIR, 'core')]
    sys.modules[f'{root}.core'] = core

    database = types.ModuleType(f'{root}.core.database')
    database.get_db = lambda: _Db()
    database.get_redis = lambda: None
    sys.modules[f'{root}.core.database'] = database

    services = types.ModuleType(f'{root}.services')
    services.__path__ = [os.path.join(_API_DIR, 'services')]
    sys.modules[f'{root}.services'] = services

    orgsvc = types.ModuleType(f'{root}.services.org_api_key_service')

    def validate_api_key(key):
        if key == ORG_KEY:
            return {'id': 'k1', 'organization_id': 'org-1', 'scopes': ['devices:read', 'telemetry:read'], 'name': 'reader'}
        return None
    orgsvc.validate_api_key = validate_api_key
    sys.modules[f'{root}.services.org_api_key_service'] = orgsvc
    services.org_api_key_service = orgsvc

    for name in ('rbac', 'auth'):
        spec = importlib.util.spec_from_file_location(
            f'{root}.core.{name}', os.path.join(_API_DIR, 'core', f'{name}.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[f'{root}.core.{name}'] = module
        spec.loader.exec_module(module)
        setattr(core, name, module)
    return sys.modules[f'{root}.core.auth']


@pytest.fixture()
def client(auth, monkeypatch):
    # a device key is validated by a store this test does not have: say what it would answer
    monkeypatch.setattr(auth, 'validate_device_api_key',
                        lambda db, key: {'device_id': 'dev-1', 'organization_id': 'org-1'} if key == DEVICE_KEY else None)
    app = flask.Flask('orgkey')
    seen = {'calls': 0}

    def handler():
        seen['calls'] += 1
        return flask.jsonify({'ok': True, 'who': getattr(flask.g, 'device_id', None)})

    for path, deco in (('/ingest', auth.require_telemetry_ingest), ('/strict', auth.require_api_key),
                       ('/mtls_or_key', auth.require_api_key_or_mtls), ('/readable', auth.require_auth_or_api_key)):
        app.add_url_rule(path, path.strip('/'), deco(handler), methods=['GET', 'POST'])
    c = app.test_client()
    c.seen = seen
    return c


WRITE_ROUTES = ['/ingest', '/strict', '/mtls_or_key']


class TestTheOrgKeyCannotWrite:

    @pytest.mark.parametrize('route', WRITE_ROUTES)
    def test_header_form_is_refused_and_the_handler_never_runs(self, client, route):
        r = client.post(route, headers={'X-API-KEY': ORG_KEY}, json={'data': {'t': 1}})
        assert r.status_code == 403, r.get_data(as_text=True)
        assert r.get_json()['code'] == 'API_KEY_READ_ONLY'
        assert client.seen['calls'] == 0

    @pytest.mark.parametrize('route', WRITE_ROUTES)
    def test_query_form_is_refused_too(self, client, route):
        r = client.post(f'{route}?api_key={ORG_KEY}', json={'data': {'t': 1}})
        assert r.status_code == 403
        assert client.seen['calls'] == 0

    @pytest.mark.parametrize('route', WRITE_ROUTES)
    def test_the_other_header_spellings_are_refused(self, client, route):
        for h in ('X-API-Key', 'X-Api-Key'):
            assert client.post(route, headers={h: ORG_KEY}, json={'data': {}}).status_code == 403
        # duplicated header, comma-joined: the first value is the key
        assert client.post(route, headers={'X-API-KEY': f'{ORG_KEY}, {ORG_KEY}'}, json={'data': {}}).status_code == 403
        assert client.seen['calls'] == 0

    @pytest.mark.parametrize('route', WRITE_ROUTES)
    def test_a_key_that_is_not_valid_is_still_401_not_403(self, client, route):
        # 403 is "valid, but not for this"; an unknown key must not learn which keys exist
        r = client.post(route, headers={'X-API-KEY': 'tesaiot_org_abc12345_' + 'f' * 32}, json={})
        assert r.status_code == 401


class TestWhatStillWorks:

    def test_the_org_key_still_reads_where_a_read_route_accepts_it(self, client):
        r = client.get('/readable', headers={'X-API-KEY': ORG_KEY})
        assert r.status_code == 200
        assert client.seen['calls'] == 1

    @pytest.mark.parametrize('route', WRITE_ROUTES)
    def test_a_device_key_still_writes_as_its_device(self, client, route):
        r = client.post(route, headers={'X-API-KEY': DEVICE_KEY}, json={'data': {'t': 1}})
        assert r.status_code == 200, r.get_data(as_text=True)
        assert client.seen['calls'] == 1

    def test_no_credential_at_all_is_still_401(self, client):
        assert client.post('/ingest', json={}).status_code == 401
