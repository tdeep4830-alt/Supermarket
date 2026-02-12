"""
User URL Configuration.

Ref: .blueprint/auth.md §5 (API Endpoints)
"""
from django.urls import path

from .views import CSRFTokenView, LoginView, LogoutView, MeView, RegisterView

app_name = "users"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("csrf/", CSRFTokenView.as_view(), name="csrf"),
]
