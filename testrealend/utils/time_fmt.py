"""UTC timestamp serialisation for API responses.

v3 delivery-related timestamps that leave the app are rendered as UTC ISO-8601
with an explicit ``Z`` suffix (e.g. ``2026-01-02T04:29:30Z``) so browsers
cannot misread a naive string as local time (which caused an 8h skew for
UTC+8 users).
"""

from datetime import UTC


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
