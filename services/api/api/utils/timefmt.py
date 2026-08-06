# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""One way to put a timestamp on the wire.

A browser reads an ISO string with no offset as *local* time. The api container
runs with ``TZ=Asia/Bangkok`` by default (docker-compose.yml sets
``TZ: ${TZ:-Asia/Bangkok}``), so a naive datetime here means one of two opposite
things depending on where it came from:

    datetime.utcnow()   -> naive, actually UTC       (renders 7h early)
    datetime.now()      -> naive, actually container-local (renders correctly, by luck)

Both look identical once they are ``datetime`` objects, which is exactly how the
telemetry chart ended up seven hours behind while the device log next to it was
accidentally right. No helper can tell them apart, so this module does not try:
:func:`iso_utc` refuses a naive value outright, and the caller has to say which
kind it holds by choosing :func:`iso_from_utc_naive` or :func:`iso_from_local_naive`.

Guessing is the bug. Making the caller state the assumption is the fix.

Never append ``'Z'`` to the result. These functions already emit ``+00:00``, and
``"...+00:00Z"`` parses as ``Invalid Date`` in every browser. Several call sites
in this codebase append their own ``'Z'`` to a value they built themselves —
those are correct as they stand and must be left alone.
"""

from datetime import datetime, timezone
from typing import Optional, Union


class NaiveDatetimeError(ValueError):
    """Raised when a datetime carries no timezone and none was declared."""


def now_utc() -> datetime:
    """The only correct way to take 'now' in this codebase."""
    return datetime.now(timezone.utc)


def iso_utc(value: Union[datetime, str, None]) -> Optional[str]:
    """Serialise an *aware* datetime (or ISO string) as UTC ISO 8601.

    Raises :class:`NaiveDatetimeError` on a naive datetime. That is deliberate:
    a naive value is ambiguous, and silently stamping UTC on one that actually
    held container-local time moves it seven hours into the future.

    Use :func:`iso_from_utc_naive` when you know the value is UTC — a datetime
    read back from MongoDB, for instance, since BSON stores UTC and pymongo
    hands it back without a tzinfo.
    """
    if value is None:
        return None

    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return value          # not a timestamp we understand; pass through
        return iso_utc(parsed)

    if not isinstance(value, datetime):
        return value

    if value.tzinfo is None:
        raise NaiveDatetimeError(
            'refusing to serialise a naive datetime: say what it means with '
            'iso_from_utc_naive() or iso_from_local_naive()'
        )

    return value.astimezone(timezone.utc).isoformat()


def _parse(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def iso_from_utc_naive(value: Union[datetime, str, None]) -> Optional[str]:
    """Serialise a value that is UTC but carries no tzinfo.

    The normal case for anything read out of MongoDB: BSON dates are UTC, and
    pymongo returns them naive. Also the right choice for anything produced by
    ``datetime.utcnow()``.

    Strings are handled too, because the same field arrives as a datetime from
    one caller and as an already-serialised string from another — and a string
    without an offset is exactly as ambiguous as a naive datetime.
    """
    if isinstance(value, str):
        parsed = _parse(value)
        if parsed is None:
            return value          # not a timestamp we understand; pass through
        value = parsed

    if isinstance(value, datetime) and value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return iso_utc(value)


def iso_from_local_naive(value: Union[datetime, str, None]) -> Optional[str]:
    """Serialise a value written by ``datetime.now()`` — container local time.

    Only for data whose *writer* used a naive local clock. Converting it here
    makes the value honest on the wire without having to migrate the stored
    rows first.
    """
    if isinstance(value, str):
        parsed = _parse(value)
        if parsed is None:
            return value
        value = parsed

    if isinstance(value, datetime) and value.tzinfo is None:
        value = value.astimezone()      # interpret in the container's zone
    return iso_utc(value)
