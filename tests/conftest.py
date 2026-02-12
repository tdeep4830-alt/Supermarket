"""
Pytest Configuration for Online Supermarket.

Ref: .blueprint/infra.md §7 - Automated Testing
"""
import pytest


@pytest.fixture(scope="session")
def django_db_setup():
    """Configure test database."""
    pass


@pytest.fixture
def api_client():
    """Provide Django test client."""
    from django.test import Client
    return Client()
