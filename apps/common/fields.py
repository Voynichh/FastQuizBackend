from datetime import UTC

from rest_framework import serializers


class UtcMillisDateTimeField(serializers.DateTimeField):
    """ISO 8601, UTC, milisaniye hassasiyeti: 2026-10-17T08:12:03.120Z (Bölüm 6)."""

    def to_representation(self, value):
        if value is None:
            return None
        return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
