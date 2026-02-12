"""
User Serializers.

Ref: .blueprint/auth.md §5 (API Endpoints)
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model (read-only for sensitive fields).

    Used for /api/auth/me/ endpoint.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone",
            "is_verified",
            "avatar_url",
            "membership_tier",
            "is_staff",
            "date_joined",
        ]
        read_only_fields = ["id", "is_verified", "membership_tier", "is_staff", "date_joined"]


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.

    Used for PUT /api/auth/me/ endpoint.
    """

    class Meta:
        model = User
        fields = ["email", "phone", "avatar_url"]

    def validate_phone(self, value):
        """Ensure phone number is unique if provided."""
        if value:
            user = self.instance
            if User.objects.exclude(pk=user.pk).filter(phone=value).exists():
                raise serializers.ValidationError("This phone number is already in use.")
        return value

    def validate_email(self, value):
        """Ensure email is unique if provided."""
        if value:
            user = self.instance
            if User.objects.exclude(pk=user.pk).filter(email=value).exists():
                raise serializers.ValidationError("This email is already in use.")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    Used for POST /api/auth/register/ endpoint.
    Ref: auth.md §3 - Password must use PBKDF2 (Django default).
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ["username", "email", "password", "password_confirm", "phone"]

    def validate(self, attrs):
        """Ensure passwords match."""
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def validate_email(self, value):
        """Ensure email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        """Create user with hashed password (PBKDF2)."""
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)  # Uses PBKDF2 by default (Ref: auth.md §3)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.

    Used for POST /api/auth/login/ endpoint.
    """

    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
    )
