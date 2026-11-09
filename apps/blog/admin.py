from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.overrides import FORMFIELD_OVERRIDES_INLINE
from unfold.sections import TableSection
from unfold.widgets import UnfoldAdminTextareaWidget

from django.contrib import admin
from django.db import models
from django.db.models import Count, Prefetch, QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.text import Truncator

from apps.blog.models import Category, Comment, Post, Tag

COMMENT_PREVIEW_LENGTH = 60
INLINE_COMMENTS_PER_PAGE = 10
INLINE_BODY_ROWS = 2
SECTION_HEIGHT_PX = 300

POST_CHANGELIST_URL_NAME = "admin:blog_post_changelist"
COMMENT_CHANGELIST_URL_NAME = "admin:blog_comment_changelist"
TAG_CHANGE_URL_NAME = "admin:blog_tag_change"
COMMENT_POST_FILTER_PARAM = "post__id__exact"


def short_text(text: str) -> str:
    """Body shortened to COMMENT_PREVIEW_LENGTH characters."""
    return Truncator(text).chars(COMMENT_PREVIEW_LENGTH)


# A section is shown when you click a row in the list (the row expands).


class CategoryPostsSection(TableSection):
    verbose_name = "Posts in this category"
    related_name = "posts"
    fields = ("title", "author", "status", "created_at")
    height = SECTION_HEIGHT_PX


class PostCommentsSection(TableSection):
    verbose_name = "Comments"
    related_name = "comments"
    fields = ("author", "comment_body", "created_at")
    height = SECTION_HEIGHT_PX

    @display(description="Comment")
    def comment_body(self, instance: Comment) -> str:
        return short_text(instance.body)


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "display_posts_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    list_sections = (CategoryPostsSection,)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Category]:
        return (
            super()
            .get_queryset(request)
            .annotate(posts_count=Count("posts", distinct=True))
            # For the section: all posts of the page in one query
            .prefetch_related(
                Prefetch(
                    "posts",
                    queryset=Post.objects.select_related("author"),
                )
            )
        )

    @display(description="Posts", ordering="posts_count")
    def display_posts_count(self, obj: Category) -> int:
        return obj.posts_count


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug", "display_posts_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request: HttpRequest) -> QuerySet[Tag]:
        return (
            super()
            .get_queryset(request)
            .annotate(posts_count=Count("posts", distinct=True))
        )

    @display(description="Posts", ordering="posts_count")
    def display_posts_count(self, obj: Tag) -> int:
        return obj.posts_count


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("display_post", "author", "display_body", "created_at")
    list_select_related = ("post", "author")
    list_filter = (
        ("post", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("body", "author__email", "post__title")
    autocomplete_fields = ("post", "author")
    readonly_fields = ("created_at",)

    @display(description="Post", ordering="post__title")
    def display_post(self, obj: Comment) -> str:
        return obj.post.title

    @display(description="Comment")
    def display_body(self, obj: Comment) -> str:
        return short_text(obj.body)


class CommentInline(TabularInline):
    model = Comment
    fields = ("author", "body", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("author",)
    extra = 0
    tab = True  # own tab on the post page
    per_page = INLINE_COMMENTS_PER_PAGE
    formfield_overrides = {
        **FORMFIELD_OVERRIDES_INLINE,
        models.TextField: {
            "widget": UnfoldAdminTextareaWidget(attrs={"rows": INLINE_BODY_ROWS}),
        },
    }

    def get_queryset(self, request: HttpRequest) -> QuerySet[Comment]:
        return super().get_queryset(request).select_related("author")


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = (
        "display_header",
        "display_status",
        "category",
        "display_tags",
        "display_comments_count",
        "created_at",
    )
    list_select_related = ("author", "category")
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("tags", MultipleRelatedDropdownFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("title", "body", "author__email")
    list_sections = (PostCommentsSection,)

    actions = ("publish_selected", "move_to_drafts")
    actions_row = ("toggle_status",)
    actions_list = ("publish_all_drafts",)
    actions_detail = ("open_comments",)
    actions_submit_line = ("save_and_publish",)

    fieldsets = (
        (
            "Content",
            {"classes": ["tab"], "fields": ("title", "slug", "body")},
        ),
        (
            "Classification",
            {"classes": ["tab"], "fields": ("category", "tags", "status")},
        ),
        (
            "Meta",
            {"classes": ["tab"], "fields": ("author", "created_at", "updated_at")},
        ),
    )
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("author", "category", "tags")
    readonly_fields = ("created_at", "updated_at")
    formfield_overrides = {
        models.TextField: {"widget": WysiwygWidget},
    }
    warn_unsaved_form = True
    inlines = (CommentInline,)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Post]:
        """Everything the list needs in a fixed number of queries."""
        return (
            super()
            .get_queryset(request)
            .annotate(comments_count=Count("comments", distinct=True))
            .prefetch_related(
                "tags",
                Prefetch(
                    "comments",
                    queryset=Comment.objects.select_related("author"),
                ),
            )
        )

    @display(description="Post", header=True, ordering="title")
    def display_header(self, obj: Post) -> list[str]:
        author_name: str = obj.author.full_name or obj.author.email
        return [obj.title, f"by {author_name}"]

    @display(
        description="Status",
        ordering="status",
        label={
            Post.Status.PUBLISHED: "success",
            Post.Status.DRAFT: "warning",
        },
    )
    def display_status(self, obj: Post) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(description="Tags", dropdown=True)
    def display_tags(self, obj: Post) -> dict:
        # len(...all()) uses prefetch_related; .count() would query every row
        tags: list[Tag] = list(obj.tags.all())
        return {
            "title": f"{len(tags)} tags",
            "items": [
                {
                    "title": tag.name,
                    "link": reverse(TAG_CHANGE_URL_NAME, args=(tag.pk,)),
                }
                for tag in tags
            ],
        }

    @display(description="Comments", ordering="comments_count")
    def display_comments_count(self, obj: Post) -> int:
        return obj.comments_count

    def _changelist_url(self) -> str:
        return reverse(POST_CHANGELIST_URL_NAME)

    @action(
        description="Publish selected posts",
        icon="publish",
        permissions=["change"],
    )
    def publish_selected(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated: int = queryset.update(status=Post.Status.PUBLISHED)
        self.message_user(request, f"{updated} post(s) published.")

    @action(
        description="Move selected posts to drafts",
        icon="unpublished",
        permissions=["change"],
    )
    def move_to_drafts(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated: int = queryset.update(status=Post.Status.DRAFT)
        self.message_user(request, f"{updated} post(s) moved to drafts.")

    @action(
        description="Publish / unpublish",
        url_path="toggle-status",
        icon="swap_horiz",
        permissions=["change"],
    )
    def toggle_status(
        self, request: HttpRequest, object_id: int
    ) -> HttpResponseRedirect:
        post: Post = Post.objects.get(pk=object_id)
        if post.status == Post.Status.PUBLISHED:
            post.status = Post.Status.DRAFT
        else:
            post.status = Post.Status.PUBLISHED
        post.save(update_fields=("status", "updated_at"))

        self.message_user(
            request, f"“{post.title}” is now {post.get_status_display().lower()}."
        )
        # Go back to the same page of the list (with filters)
        return HttpResponseRedirect(
            request.headers.get("referer") or self._changelist_url()
        )

    @action(
        description="Publish all drafts",
        url_path="publish-all-drafts",
        icon="done_all",
        variant=ActionVariant.PRIMARY,
        permissions=["change"],
    )
    def publish_all_drafts(self, request: HttpRequest) -> HttpResponseRedirect:
        updated: int = Post.objects.filter(status=Post.Status.DRAFT).update(
            status=Post.Status.PUBLISHED
        )
        self.message_user(request, f"{updated} draft(s) published.")
        return HttpResponseRedirect(self._changelist_url())

    @action(
        description="Open comments",
        url_path="comments",
        icon="forum",
    )
    def open_comments(
        self, request: HttpRequest, object_id: int
    ) -> HttpResponseRedirect:
        url: str = reverse(COMMENT_CHANGELIST_URL_NAME)
        return HttpResponseRedirect(f"{url}?{COMMENT_POST_FILTER_PARAM}={object_id}")

    @action(description="Save & publish", permissions=["change"])
    def save_and_publish(self, request: HttpRequest, obj: Post) -> None:
        # Runs after the object is saved
        obj.status = Post.Status.PUBLISHED
        obj.save(update_fields=("status", "updated_at"))
        self.message_user(request, f"“{obj.title}” is published.")