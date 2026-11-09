"""
Callbacks for the UNFOLD settings (sidebar badge and dashboard).

In settings they are referenced as strings, e.g. "apps.blog.callbacks.drafts_badge",
so Unfold imports this module only after Django apps are loaded.
"""

import json
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import HttpRequest
from django.urls import reverse

from apps.blog.models import Category, Comment, Post

User = get_user_model()

TOP_AUTHORS_LIMIT = 5
PERCENT = 100
CHART_COLOR = "var(--color-primary-600)"
CHART_BAR_MAX_THICKNESS = 36
PUBLISHED_PROGRESS_CLASS = "progress-published"  # static/css/admin.css
DRAFT_PROGRESS_CLASS = "progress-draft"
CATEGORY_CHANGELIST_URL_NAME = "admin:blog_category_changelist"
POST_CHANGELIST_URL_NAME = "admin:blog_post_changelist"
USER_CHANGELIST_URL_NAME = "admin:auths_user_changelist"
COMMENT_CHANGELIST_URL_NAME = "admin:blog_comment_changelist"
POST_STATUS_PARAM = "status__exact"
VIEW_USER_PERMISSION = "auths.view_user"


def drafts_badge(request: HttpRequest) -> int | None:
    """Number of drafts next to 'Posts' in the sidebar (hidden when 0)."""
    drafts: int = Post.objects.filter(status=Post.Status.DRAFT).count()
    return drafts or None


def _percent(part: int, total: int) -> int:
    if total == 0:
        return 0
    return round(part * PERCENT / total)


def _cards(request: HttpRequest, posts_stats: dict[str, int]) -> list[dict[str, Any]]:
    posts_url: str = reverse(POST_CHANGELIST_URL_NAME)
    # Only users who may open the user list get a link on the card
    users_url: str | None = (
        reverse(USER_CHANGELIST_URL_NAME)
        if request.user.has_perm(VIEW_USER_PERMISSION)
        else None
    )
    return [
        {
            "title": "Users",
            "value": User.objects.count(),
            "icon": "person",
            "link": users_url,
        },
        {
            "title": "Published posts",
            "value": posts_stats["published"],
            "icon": "article",
            "link": f"{posts_url}?{POST_STATUS_PARAM}={Post.Status.PUBLISHED}",
        },
        {
            "title": "Drafts",
            "value": posts_stats["drafts"],
            "icon": "edit_document",
            "link": f"{posts_url}?{POST_STATUS_PARAM}={Post.Status.DRAFT}",
        },
        {
            "title": "Comments",
            "value": Comment.objects.count(),
            "icon": "forum",
            "link": reverse(COMMENT_CHANGELIST_URL_NAME),
        },
    ]


def _posts_per_category_chart() -> str:
    """Chart.js data (labels + datasets) as a JSON string."""
    categories = Category.objects.annotate(posts_count=Count("posts")).order_by(
        "-posts_count", "name"
    )
    without_category: int = Post.objects.filter(category__isnull=True).count()

    labels: list[str] = [category.name for category in categories]
    values: list[int] = [category.posts_count for category in categories]
    if without_category:
        labels.append("No category")
        values.append(without_category)

    return json.dumps(
        {
            "labels": labels,
            "datasets": [
                {
                    "label": "Posts",
                    "data": values,
                    "backgroundColor": CHART_COLOR,
                    "maxBarThickness": CHART_BAR_MAX_THICKNESS,
                },
            ],
        }
    )


def _top_authors_table() -> dict[str, list]:
    authors = (
        User.objects.annotate(
            posts_count=Count("posts", distinct=True),
            published_count=Count(
                "posts",
                filter=Q(posts__status=Post.Status.PUBLISHED),
                distinct=True,
            ),
        )
        .filter(posts_count__gt=0)
        .order_by("-posts_count", "email")[:TOP_AUTHORS_LIMIT]
    )
    return {
        "headers": ["#", "Author", "Email", "Posts", "Published"],
        "rows": [
            [
                place,
                f"{author.first_name} {author.last_name}",
                author.email,
                author.posts_count,
                author.published_count,
            ]
            for place, author in enumerate(authors, start=1)
        ],
    }


def _posts_progress(posts_stats: dict[str, int]) -> list[dict[str, Any]]:
    total: int = posts_stats["total"]
    published_share: int = _percent(posts_stats["published"], total)
    # The two bars always add up to 100% (no rounding gap)
    draft_share: int = PERCENT - published_share if total else 0
    return [
        {
            "title": "Published",
            "description": f"{posts_stats['published']} · {published_share}%",
            "value": published_share,
            "progress_class": PUBLISHED_PROGRESS_CLASS,
        },
        {
            "title": "Drafts",
            "description": f"{posts_stats['drafts']} · {draft_share}%",
            "value": draft_share,
            "progress_class": DRAFT_PROGRESS_CLASS,
        },
    ]


def dashboard_callback(request: HttpRequest, context: dict[str, Any]) -> dict[str, Any]:
    """Adds the dashboard data to the context of templates/admin/index.html."""
    # All post numbers in one query
    posts_stats: dict[str, int] = Post.objects.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count("id", filter=Q(status=Post.Status.DRAFT)),
    )

    context.update(
        {
            "dashboard_cards": _cards(request, posts_stats),
            "posts_per_category_chart": _posts_per_category_chart(),
            "top_authors_table": _top_authors_table(),
            "posts_progress": _posts_progress(posts_stats),
            "categories_url": reverse(CATEGORY_CHANGELIST_URL_NAME),
        }
    )
    return context