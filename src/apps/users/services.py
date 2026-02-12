"""
User Services (Write Operations).

Ref: .blueprint/code_sturcture.md §2
Ref: .blueprint/auth.md §5 (Auth API)

Services:
- register_user: Create new user account
- authenticate_user: Validate credentials and return user
- update_user_profile: Update user profile
"""
import logging

from django.contrib.auth import authenticate, get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


def register_user(
    username: str,
    email: str,
    password: str,
    phone: str | None = None,
) -> User:
    """
    Register a new user.

    Ref: auth.md §3 - Password stored using PBKDF2.

    Args:
        username: Unique username
        email: User email address
        password: Plain text password (will be hashed)
        phone: Optional phone number

    Returns:
        Created User instance

    Raises:
        ValueError: If username or email already exists
    """
    if User.objects.filter(username=username).exists():
        raise ValueError("Username already exists")

    if User.objects.filter(email=email).exists():
        raise ValueError("Email already exists")

    if phone and User.objects.filter(phone=phone).exists():
        raise ValueError("Phone number already exists")

    user = User(
        username=username,
        email=email,
        phone=phone,
    )
    user.set_password(password)  # Uses PBKDF2 (Ref: auth.md §3)
    user.save()

    # Note: Do NOT log password or PII (Ref: auth.md §3)
    logger.info("User registered", extra={"user_id": str(user.id)})

    return user


def authenticate_user(username: str, password: str) -> User:
    """
    Authenticate user credentials.

    Ref: auth.md §3 - PII protection, do not log passwords.

    Args:
        username: Username or email
        password: Plain text password

    Returns:
        Authenticated User instance

    Raises:
        AuthenticationError: If credentials are invalid
    """
    # Try authentication with username
    user = authenticate(username=username, password=password)

    if user is None:
        # Try with email as username
        try:
            user_by_email = User.objects.get(email=username)
            user = authenticate(username=user_by_email.username, password=password)
        except User.DoesNotExist:
            pass

    if user is None:
        # Note: Do NOT log the password (Ref: auth.md §3)
        logger.warning("Failed login attempt", extra={"username": username})
        raise AuthenticationError("Invalid username or password")

    if not user.is_active:
        logger.warning("Inactive user login attempt", extra={"user_id": str(user.id)})
        raise AuthenticationError("User account is disabled")

    logger.info("User logged in", extra={"user_id": str(user.id)})
    return user


def update_user_profile(
    user: User,
    email: str | None = None,
    phone: str | None = None,
    avatar_url: str | None = None,
) -> User:
    """
    Update user profile information.

    Args:
        user: User instance to update
        email: New email (optional)
        phone: New phone (optional)
        avatar_url: New avatar URL (optional)

    Returns:
        Updated User instance

    Raises:
        ValueError: If email or phone already in use
    """
    if email is not None and email != user.email:
        if User.objects.exclude(pk=user.pk).filter(email=email).exists():
            raise ValueError("Email already in use")
        user.email = email

    if phone is not None and phone != user.phone:
        if phone and User.objects.exclude(pk=user.pk).filter(phone=phone).exists():
            raise ValueError("Phone number already in use")
        user.phone = phone

    if avatar_url is not None:
        user.avatar_url = avatar_url

    user.save()
    logger.info("User profile updated", extra={"user_id": str(user.id)})

    return user
