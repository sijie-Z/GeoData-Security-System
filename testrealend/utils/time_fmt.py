"""UTC timestamp serialisation for API responses.

v3 delivery-related timestamps that leave the app are rendered as UTC ISO-8601
with an explicit ``Z`` suffix (e.g. ``2026-01-02T04:29:30Z``) so browsers
cannot misread a naive string as local time (which caused an 8h skew for
UTC+8 users).
"""

from datetime import UTC, datetime


def parse_utc_iso(value):
    """Parse an ISO-8601 ``time_from``/``time_to`` style value into a NAIVE UTC
    ``datetime`` — the storage convention of every DATETIME column in this
    project (written with ``datetime.now(UTC)``). Accepts ``YYYY-MM-DDTHH:MM:SSZ``
    (the ``utc_iso_z`` output), ``+00:00`` offsets and naive strings (read as
    UTC). Raises ``ValueError`` on anything unparseable so callers can answer
    ``400`` instead of guessing.
    """
    text = str(value).strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).replace(tzinfo=None)


def utc_iso_z(value):
    """Format ``value`` as ``YYYY-MM-DDTHH:MM:SSZ``; None passes through as None.

    Naive datetimes are interpreted as UTC — the storage convention for the
    DATETIME columns, which are written with ``datetime.now(UTC)``.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
