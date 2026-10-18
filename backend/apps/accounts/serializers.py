"""The only serializer allowed to describe a person to anyone but staff.

It exposes the display name and nothing else. Private fields (see
PRIVATE_USER_FIELDS) are never included; tests/test_privacy.py enforces this
for every serializer in the project.
"""

from rest_framework import serializers

from .models import User


class PublicUserSerializer(serializers.ModelSerializer):
    """For anything a visitor or another member can see, e.g. an author byline."""

    class Meta:
        model = User
        fields = ["display_name"]
        read_only_fields = fields
