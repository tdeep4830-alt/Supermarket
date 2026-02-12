"""
User Views (Auth API).

Ref: .blueprint/auth.md §5 (API Endpoints)
Ref: .blueprint/code_sturcture.md §2

Endpoints:
- POST /api/auth/register/ - User registration
- POST /api/auth/login/ - User login
- POST /api/auth/logout/ - User logout
- GET /api/auth/me/ - Get current user
- PUT /api/auth/me/ - Update current user
"""
import logging

from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from .services import AuthenticationError, authenticate_user

logger = logging.getLogger(__name__)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RegisterView(APIView):
    """
    User Registration API.

    POST /api/auth/register/
    Ref: auth.md §4 - AllowAny permission
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Register a new user."""
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation failed", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()

        # Auto-login after registration
        login(request, user)

        return Response(
            {
                "message": "Registration successful",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginView(APIView):
    """
    User Login API.

    POST /api/auth/login/
    Ref: auth.md §4 - AllowAny permission
    Ref: auth.md §3 - Session-based authentication
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Authenticate user and create session."""
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation failed", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = authenticate_user(
                username=serializer.validated_data["username"],
                password=serializer.validated_data["password"],
            )
        except AuthenticationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Create session (Ref: auth.md §1)
        login(request, user)

        # Ensure CSRF token is set in response
        get_token(request)

        return Response(
            {
                "message": "Login successful",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    User Logout API.

    POST /api/auth/logout/
    Ref: auth.md §4 - IsAuthenticated permission
    Ref: auth.md §1 - Server-side logout (advantage of Session over JWT)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Destroy user session."""
        user_id = str(request.user.id)
        logout(request)

        logger.info("User logged out", extra={"user_id": user_id})

        return Response(
            {"message": "Logout successful"},
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    """
    Current User API.

    GET /api/auth/me/ - Get current user info
    PUT /api/auth/me/ - Update current user info
    Ref: auth.md §4 - IsAuthenticated permission
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current authenticated user."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        """Update current user profile."""
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return Response(
                {"error": "Validation failed", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        return Response(
            UserSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFTokenView(APIView):
    """
    CSRF Token API.

    GET /api/auth/csrf/
    Returns CSRF token for frontend to use in subsequent requests.
    Ref: auth.md §7 - Frontend needs CSRF token
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Get CSRF token."""
        csrf_token = get_token(request)
        return Response(
            {"csrfToken": csrf_token},
            status=status.HTTP_200_OK,
        )
