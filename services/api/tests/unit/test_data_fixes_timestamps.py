# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors

"""The call sites, not just the helper.

test_timefmt.py proves the helper is correct. These tests prove the two response
shapers actually use it — a correct helper that nobody calls fixes nothing, and
that is precisely the state this repository was in before.

They also pin the interaction that a helper-only test cannot see: once valid_to
carries an offset, the days_until_expiry arithmetic beside it has to compare
against an *aware* 'now'. Subtracting a naive datetime from an aware one raises
TypeError, the bare except swallows it, and every certificate reports 0 days
remaining. Getting the serialisation right and the arithmetic wrong trades a
visible bug for a quiet one.
"""

import os
import sys
import types
import importlib.util
from datetime import datetime, timedelta, timezone

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_UTILS_DIR = os.path.abspath(os.path.join(_HERE, '..', '..', 'api', 'utils'))


@pytest.fixture(scope='module')
def data_fixes():
    """Load data_fixes under a synthetic package.

    It does ``from .timefmt import ...`` inside the functions, so loading the
    file bare would raise "attempted relative import with no known parent
    package" the moment a test called one. Giving the module a parent package
    whose __path__ is the real utils directory makes that relative import
    resolve to the real timefmt.py — without importing the ``api`` package and
    dragging in Flask.
    """
    pkg_name = 'ce_api_utils_under_test'
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [_UTILS_DIR]
    sys.modules[pkg_name] = pkg

    spec = importlib.util.spec_from_file_location(
        f'{pkg_name}.data_fixes', os.path.join(_UTILS_DIR, 'data_fixes.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# What pymongo hands back for a BSON date: correct UTC instant, no tzinfo.
MONGO_NAIVE_UTC = datetime(2026, 8, 5, 15, 7, 51, 198000)


class TestTelemetryTimestamps:
    """fix_telemetry_data feeds the dashboard telemetry responses."""

    def test_mongo_datetime_gets_an_offset(self, data_fixes):
        out = data_fixes.fix_telemetry_data(
            {'timestamp': MONGO_NAIVE_UTC, 'device_id': 'dev-1'})
        assert out['timestamp'] == '2026-08-05T15:07:51.198000+00:00'

    def test_offsetless_string_gets_an_offset(self, data_fixes):
        """A string used to be passed through untouched — that was the bug."""
        out = data_fixes.fix_telemetry_data(
            {'timestamp': '2026-08-05T15:07:51.198000', 'device_id': 'dev-1'})
        assert out['timestamp'].endswith('+00:00')

    def test_datetime_and_string_agree(self, data_fixes):
        """Same instant in two shapes must not differ by seven hours."""
        a = data_fixes.fix_telemetry_data(
            {'timestamp': MONGO_NAIVE_UTC, 'device_id': 'd'})['timestamp']
        b = data_fixes.fix_telemetry_data(
            {'timestamp': '2026-08-05T15:07:51.198000', 'device_id': 'd'})['timestamp']
        assert datetime.fromisoformat(a) == datetime.fromisoformat(b)

    def test_missing_timestamp_is_aware(self, data_fixes):
        out = data_fixes.fix_telemetry_data({'device_id': 'dev-1'})
        assert datetime.fromisoformat(out['timestamp']).tzinfo is not None

    def test_list_input_still_works(self, data_fixes):
        out = data_fixes.fix_telemetry_data(
            [{'timestamp': MONGO_NAIVE_UTC, 'device_id': 'd'}])
        assert out[0]['timestamp'].endswith('+00:00')


class TestCertificateTimestamps:

    @pytest.mark.parametrize('field', ['valid_from', 'valid_to', 'issued_at'])
    def test_validity_dates_get_an_offset(self, data_fixes, field):
        out = data_fixes.fix_certificate_data(
            {'certificate_id': 'abc123', field: MONGO_NAIVE_UTC})
        assert out[field].endswith('+00:00')

    def test_days_until_expiry_survives_the_offset(self, data_fixes):
        """The regression this file exists for.

        valid_to is aware after the fix. If 'now' stayed naive the subtraction
        raises TypeError, the bare except catches it, and the answer is silently
        0 — indistinguishable from a certificate that expires today.
        """
        expires_in_90 = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=90)
        out = data_fixes.fix_certificate_data(
            {'certificate_id': 'abc123', 'valid_to': expires_in_90})
        assert out['days_until_expiry'] == pytest.approx(90, abs=1)

    def test_expired_certificate_clamps_to_zero(self, data_fixes):
        expired = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=5)
        out = data_fixes.fix_certificate_data(
            {'certificate_id': 'abc123', 'valid_to': expired})
        assert out['days_until_expiry'] == 0

    def test_unparseable_valid_to_does_not_raise(self, data_fixes):
        out = data_fixes.fix_certificate_data(
            {'certificate_id': 'abc123', 'valid_to': 'not-a-date'})
        assert out['days_until_expiry'] == 0


class TestNoInvalidDates:
    """'...+00:00Z' is Invalid Date in every browser."""

    def test_telemetry_never_double_stamps(self, data_fixes):
        for value in (MONGO_NAIVE_UTC,
                      '2026-08-05T15:07:51.198Z',
                      '2026-08-05T15:07:51.198+00:00'):
            out = data_fixes.fix_telemetry_data(
                {'timestamp': value, 'device_id': 'd'})['timestamp']
            assert '+00:00Z' not in out and not out.endswith('Z')
