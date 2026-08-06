# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors

"""Timestamps that reach a browser must say which zone they are in.

The telemetry chart showed times seven hours behind Bangkok because the API
serialised MongoDB's naive datetimes with a bare ``.isoformat()``. A browser
reads an ISO string with no offset as *local* time, so 15:07 UTC rendered as
15:07 Bangkok.

The container runs ``TZ=Asia/Bangkok`` by default, which makes a naive datetime
ambiguous: ``utcnow()`` produces naive UTC, ``now()`` produces naive local, and
the two need opposite corrections. These tests hold the line that the helper
never guesses between them.
"""

import os
import importlib.util
from datetime import datetime, timezone

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_TIMEFMT = os.path.abspath(
    os.path.join(_HERE, '..', '..', 'api', 'utils', 'timefmt.py'))


@pytest.fixture(scope='module')
def timefmt():
    """Load the module by path.

    These tests live outside the ``api`` package on purpose. The Dockerfile does
    ``COPY ./api/ ./api/``, so anything under it ships in the production image;
    and pytest would otherwise walk the ``__init__.py`` chain up to ``api``,
    import the Flask application factory, and fail collection on a machine that
    has no Flask installed.
    """
    spec = importlib.util.spec_from_file_location('timefmt_under_test', _TIMEFMT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# What pymongo hands back for a BSON date: correct UTC instant, no tzinfo.
MONGO_NAIVE_UTC = datetime(2026, 8, 5, 15, 7, 51, 198000)


class TestTheReportedDefect:

    def test_mongo_naive_gains_an_offset(self, timefmt):
        assert MONGO_NAIVE_UTC.isoformat() == '2026-08-05T15:07:51.198000'   # the bug
        assert timefmt.iso_from_utc_naive(MONGO_NAIVE_UTC) == \
            '2026-08-05T15:07:51.198000+00:00'                               # the fix

    def test_output_always_carries_a_zone(self, timefmt):
        for value in (MONGO_NAIVE_UTC,
                      '2026-08-05T15:07:51.198000',
                      '2026-08-05T15:07:51.198Z',
                      '2026-08-05T15:07:51.198+00:00'):
            out = timefmt.iso_from_utc_naive(value)
            assert out.endswith('+00:00'), f'{value!r} produced {out!r}'

    def test_every_input_shape_is_the_same_instant(self, timefmt):
        """A datetime and its string form must not disagree by seven hours."""
        instants = {
            datetime.fromisoformat(timefmt.iso_from_utc_naive(v))
            for v in (MONGO_NAIVE_UTC,
                      '2026-08-05T15:07:51.198000',
                      '2026-08-05T15:07:51.198Z',
                      '2026-08-05T15:07:51.198+00:00')
        }
        assert len(instants) == 1, f'shapes disagreed: {instants}'


class TestNeverProducesInvalidDate:
    """Several call sites append 'Z' themselves; '...+00:00Z' is Invalid Date."""

    @pytest.mark.parametrize('value', [
        MONGO_NAIVE_UTC,
        '2026-08-05T15:07:51.198Z',
        '2026-08-05T15:07:51.198+00:00',
        datetime(2026, 8, 5, 15, 7, 51, tzinfo=timezone.utc),
    ])
    def test_no_trailing_z(self, timefmt, value):
        out = timefmt.iso_from_utc_naive(value)
        assert not out.endswith('Z')
        assert '+00:00Z' not in out
        assert 'ZZ' not in out


class TestRefusesToGuess:
    """The guessing is what caused the bug; the helper must not do it."""

    def test_iso_utc_rejects_a_naive_datetime(self, timefmt):
        with pytest.raises(timefmt.NaiveDatetimeError):
            timefmt.iso_utc(MONGO_NAIVE_UTC)

    def test_iso_utc_rejects_a_naive_string(self, timefmt):
        with pytest.raises(timefmt.NaiveDatetimeError):
            timefmt.iso_utc('2026-08-05T15:07:51.198000')

    def test_iso_utc_accepts_an_aware_datetime(self, timefmt):
        aware = datetime(2026, 8, 5, 15, 7, 51, tzinfo=timezone.utc)
        assert timefmt.iso_utc(aware) == '2026-08-05T15:07:51+00:00'

    def test_local_naive_converts_the_other_way(self, timefmt):
        """device_logs writes datetime.now(); it must not be stamped UTC."""
        out = timefmt.iso_from_local_naive(datetime(2026, 8, 5, 22, 7, 51))
        assert out.endswith('+00:00')
        # Under TZ=Asia/Bangkok this is 15:07 UTC — the opposite correction to
        # the Mongo case, which is precisely why one blanket helper is unsafe.
        assert datetime.fromisoformat(out).tzinfo is not None


class TestPassThrough:

    def test_none_stays_none(self, timefmt):
        assert timefmt.iso_from_utc_naive(None) is None

    def test_unparseable_string_is_returned_unchanged(self, timefmt):
        assert timefmt.iso_from_utc_naive('not-a-date') == 'not-a-date'

    def test_now_utc_is_aware(self, timefmt):
        assert timefmt.now_utc().tzinfo is not None
