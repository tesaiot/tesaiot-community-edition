# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors

"""A Trust M UID is hex, so its letter case carries no meaning.

The device reports its UID uppercase in the MQTT client id; the platform stores
it lowercase when the device bundle is generated. An exact string match rejected
a device whose record was sitting right there, with the misleading log line
"Trust M device not pre-registered".

Two separate places had to change, and testing only one would have missed it:
the Mongo lookup that finds the device, and the comparisons that validate it one
step later. These tests cover both shapes.
"""

import os
import sys
import types
import importlib.util

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_API_DIR = os.path.abspath(os.path.join(_HERE, '..', '..', 'api'))

# A real UID as the chip reports it, and as the platform stores it.
UID_UPPER = 'CD16339301001C000500000A01BB820003004000AE801010712440'
UID_LOWER = UID_UPPER.lower()


@pytest.fixture(scope='module')
def mqtt_auth():
    """Load mqtt_auth_service with a stub for the one package import it makes.

    The module does ``from ..core.database import get_db, get_vault`` at import
    time. Building a synthetic package tree around it is enough to reach the two
    pure helpers under test without starting Flask, Mongo or Vault.
    """
    root = 'ce_api_under_test'
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


class TestLookupFragment:
    """_trustm_uid_match builds the Mongo query that finds the device."""

    def test_uppercase_client_id_can_match_a_lowercase_record(self, mqtt_auth):
        frag = mqtt_auth._trustm_uid_match(UID_UPPER)
        assert UID_LOWER in frag['$in'], 'stored-lowercase record would not be found'

    def test_lowercase_client_id_can_match_an_uppercase_record(self, mqtt_auth):
        frag = mqtt_auth._trustm_uid_match(UID_LOWER)
        assert UID_UPPER in frag['$in']

    def test_stays_an_indexable_in_clause(self, mqtt_auth):
        """A case-insensitive regex would work but would not use the index."""
        frag = mqtt_auth._trustm_uid_match(UID_UPPER)
        assert set(frag.keys()) == {'$in'}
        assert isinstance(frag['$in'], list)
        assert len(frag['$in']) <= 3      # {as-given, lower, upper}, deduplicated

    def test_empty_uid_is_passed_through_untouched(self, mqtt_auth):
        """Never turn a missing UID into a query that matches something."""
        assert mqtt_auth._trustm_uid_match('') == ''
        assert mqtt_auth._trustm_uid_match(None) is None


class TestComparison:
    """_uid_equal validates the device once the lookup has found it."""

    def test_case_differences_still_match(self, mqtt_auth):
        assert mqtt_auth._uid_equal(UID_UPPER, UID_LOWER)
        assert mqtt_auth._uid_equal(UID_LOWER, UID_UPPER)

    def test_surrounding_whitespace_is_ignored(self, mqtt_auth):
        assert mqtt_auth._uid_equal(f'  {UID_UPPER}  ', UID_LOWER)

    def test_a_genuinely_different_uid_is_rejected(self, mqtt_auth):
        assert not mqtt_auth._uid_equal(UID_UPPER, UID_LOWER[:-1] + 'f')

    @pytest.mark.parametrize('a,b', [
        (None, UID_LOWER), (UID_UPPER, None), ('', UID_LOWER),
        (UID_UPPER, ''), (None, None), ('', ''),
    ])
    def test_missing_values_never_compare_equal(self, mqtt_auth, a, b):
        """Two absent UIDs must not authenticate a device against each other."""
        assert not mqtt_auth._uid_equal(a, b)
