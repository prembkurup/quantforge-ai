"""Read-only dashboard API for QuantForge AI."""

from quantforge.dashboard.api import app, create_app
from quantforge.dashboard.service import DashboardService

__all__ = ["DashboardService", "app", "create_app"]
