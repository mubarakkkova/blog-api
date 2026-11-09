"""
Small helpers for the UNFOLD settings (links, permissions, environment badge).

This module is imported from settings/base.py, so it must NOT import models:
Django apps are not loaded yet at that moment.
"""

from django.http import HttpRequest
from django.urls import reverse

from settings.conf import ENV_ID

POST_CHANGELIST_URL_NAME = "admin:blog_post_changelist"
POST_STATUS_PARAM = "status__exact"
STATUS_PUBLISHED = "published"
STATUS_DRAFT = "draft"

ENV_LOCAL = "local"
ENV_PROD = "prod"
ENVIRONMENT_BADGES: dict[str, list[str]] = {
    ENV_LOCAL: ["Local", "warning"],  # orange
    ENV_PROD: ["Production", "danger"],  # red
}


def environment_callback(request: HttpRequest) -> list[str] | None:
    """Badge in the admin header: Local or Production."""
    return ENVIRONMENT_BADGES.get(ENV_ID)


def is_superuser(request: HttpRequest) -> bool:
    """Sidebar items with this permission are visible only to superusers."""
    return request.user.is_superuser


def _posts_url(status: str | None = None) -> str:
    url: str = reverse(POST_CHANGELIST_URL_NAME)
    if status is None:
        return url
    return f"{url}?{POST_STATUS_PARAM}={status}"


def all_posts_link(request: HttpRequest) -> str:
    return _posts_url()


def published_posts_link(request: HttpRequest) -> str:
    return _posts_url(STATUS_PUBLISHED)


def draft_posts_link(request: HttpRequest) -> str:
    return _posts_url(STATUS_DRAFT)


def is_all_posts_tab_active(request: HttpRequest) -> bool:
    """'All' tab is active when the list is not filtered by status."""
    return POST_STATUS_PARAM not in request.GET