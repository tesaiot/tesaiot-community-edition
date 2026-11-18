# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors

"""A telemetry read must not hide a value that has already been stored.

``GET /devices/<id>/telemetry/last`` and ``/telemetry`` read through a Redis cache
with a 300 s TTL. The cache is dropped by ``invalidate_telemetry_cache_on_ingest``,
which only ``ingest_device_telemetry`` called. The MQTT bridge (and every HTTPS
device) writes through other routes, so for up to five minutes a reader saw the
value that happened to be cached first.

Measured against a running CE before this file existed: while a device published
every 5 s, both read routes returned the same ``seq=1`` for 70 s.

Two things are held:

* the write path every telemetry POST route shares (``store_mongodb_telemetry``)
  drops the device's cached reads, AFTER the row is stored (before it, a read in
  between would cache the old value again), and a Redis failure never fails the write;
* every function that inserts into the ``telemetry`` collection also drops the
  cache, so a new write path that forgets it is a test failure and not a 5-minute
  staleness found in production. This is a source check, on purpose: the paths
  take a database, Redis, a certificate store and a user, and none of that should
  be needed to know that the line is there.
"""

import ast
import importlib.util
import os
import sys
import types

import pytest

flask = pytest.importorskip('flask')
pytest.importorskip('jsonschema')

_HERE = os.path.dirname(os.path.abspath(__file__))
_API_DIR = os.path.abspath(os.path.join(_HERE, '..', '..', 'api'))


class _Collection:
    def __init__(self, events):
        self.events = events

    def insert_one(self, doc):
        self.events.append(('insert', doc['device_id']))
        return types.SimpleNamespace(inserted_id='abc123')


@pytest.fixture()
def telemetry(monkeypatch):
    """controllers/telemetry.py loaded by path; the database and the cache are recorders."""
    events = []
    root = 'ce_api_stale'
    pkg = types.ModuleType(root)
    pkg.__path__ = [_API_DIR]
    sys.modules[root] = pkg
    for sub in ('controllers', 'core', 'services', 'utils'):
        m = types.ModuleType(f'{root}.{sub}')
        m.__path__ = [os.path.join(_API_DIR, sub)]
        sys.modules[f'{root}.{sub}'] = m

    database = types.ModuleType(f'{root}.core.database')
    database.get_db = lambda: types.SimpleNamespace(telemetry=_Collection(events))
    database.get_postgres = lambda: None
    database.get_redis = lambda: None
    sys.modules[f'{root}.core.database'] = database

    auth = types.ModuleType(f'{root}.core.auth')
    for name in ('require_api_key', 'require_api_key_or_mtls', 'require_auth', 'require_telemetry_ingest'):
        setattr(auth, name, lambda f: f)
    sys.modules[f'{root}.core.auth'] = auth

    cache = types.ModuleType(f'{root}.services.telemetry_cache_service')
    cache.invalidate_telemetry_cache_on_ingest = lambda device_id: events.append(('invalidate', device_id))
    sys.modules[f'{root}.services.telemetry_cache_service'] = cache

    for sub, name in (('utils', 'validation'), ('utils', 'timefmt')):
        spec = importlib.util.spec_from_file_location(f'{root}.{sub}.{name}', os.path.join(_API_DIR, sub, f'{name}.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[f'{root}.{sub}.{name}'] = module
        spec.loader.exec_module(module)

    spec = importlib.util.spec_from_file_location(f'{root}.controllers.telemetry', os.path.join(_API_DIR, 'controllers', 'telemetry.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[f'{root}.controllers.telemetry'] = module
    spec.loader.exec_module(module)
    module._events = events
    module._cache = cache
    return module


class TestTheSharedWritePath:

    def test_a_stored_row_drops_the_devices_cached_reads_after_it(self, telemetry):
        telemetry.store_mongodb_telemetry('ag-soil-01', None, {'t': 1}, {}, 'org-1')
        assert telemetry._events == [('insert', 'ag-soil-01'), ('invalidate', 'ag-soil-01')]

    def test_only_that_devices_cache_is_dropped(self, telemetry):
        telemetry.store_mongodb_telemetry('a-device', None, {}, {})
        telemetry.store_mongodb_telemetry('b-device', None, {}, {})
        assert [e for e in telemetry._events if e[0] == 'invalidate'] == [('invalidate', 'a-device'), ('invalidate', 'b-device')]

    def test_a_redis_failure_never_fails_the_write(self, telemetry):
        def boom(_):
            raise RuntimeError('redis is down')
        # the controller bound the name when it was imported: patch it where it is used
        telemetry.invalidate_telemetry_cache_on_ingest = boom
        assert telemetry.store_mongodb_telemetry('ag-soil-01', None, {}, {}) == 'abc123'
        assert telemetry._events == [('insert', 'ag-soil-01')]


# ---- every write path

def _functions_that_insert_telemetry():
    found = []
    for folder in ('controllers', 'services'):
        base = os.path.join(_API_DIR, folder)
        for fn in sorted(os.listdir(base)):
            if not fn.endswith('.py'):
                continue
            tree = ast.parse(open(os.path.join(base, fn), encoding='utf-8').read())
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                inserts, drops = False, False
                for call in ast.walk(node):
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
                        f = call.func
                        # <something>.telemetry.insert_one(...) / .insert_many(...)
                        if f.attr in ('insert_one', 'insert_many') and isinstance(f.value, ast.Attribute) and f.value.attr == 'telemetry':
                            inserts = True
                        if f.attr in ('invalidate_device_cache', 'invalidate_telemetry_cache_on_ingest'):
                            drops = True
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id in ('invalidate_telemetry_cache_on_ingest', 'drop_telemetry_read_cache'):
                        drops = True
                if inserts:
                    found.append((f'{folder}/{fn}', node.name, drops))
    return found


def test_the_sources_name_the_write_paths_this_test_checks():
    paths = {(f, n) for f, n, _ in _functions_that_insert_telemetry()}
    # if one of these is renamed the check below would silently look at nothing
    assert ('controllers/telemetry.py', 'store_mongodb_telemetry') in paths
    assert ('services/device_service.py', 'ingest_device_telemetry') in paths
    assert len(paths) >= 8


@pytest.mark.parametrize('where,name,drops', _functions_that_insert_telemetry(), ids=lambda v: str(v))
def test_every_function_that_stores_telemetry_drops_the_read_cache(where, name, drops):
    assert drops, f'{where}:{name} inserts into telemetry and never drops the device\'s cached reads'
