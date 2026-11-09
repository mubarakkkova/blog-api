from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter
from unfold.decorators import action, display
from unfold.forms import AdminPasswordChangeForm

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, QuerySet
from django.http import HttpRequest

from apps.auths.forms import UserAdminChangeForm, UserAdminCreationForm
from apps.auths.models import User

USERS_PER_PAGE = 50

# Group is registered by django.contrib.auth with the plain admin.
# Register it again with Unfold so it gets the same look.
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    """Group admin with Unfold styles."""


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """User admin: Django's UserAdmin adapted to email login (no username)."""

    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = (
        "display_header",
        "display_is_active",
        "display_is_staff",
        "display_posts_count",
    )
    list_filter = (
        ("is_active", BooleanRadioFilter),
        ("is_staff", BooleanRadioFilter),
    )
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    list_per_page = USERS_PER_PAGE
    readonly_fields = ("last_login",)
    filter_horizontal = ("groups", "user_permissions")
    actions = ("activate_users", "deactivate_users")

    # "classes": ["tab"] turns every fieldset into a tab
    fieldsets = (
        (
            "Personal info",
            {
                "classes": ["tab"],
                "fields": ("email", "password", "first_name", "last_name"),
            },
        ),
        (
            "Permissions",
            {
                "classes": ["tab"],
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Important dates",
            {
                "classes": ["tab"],
                "fields": ("last_login",),
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        """Count posts in the same query as the users (no query per row)."""
        return (
            super()
            .get_queryset(request)
            .annotate(posts_count=Count("posts", distinct=True))
        )

    @display(description="User", header=True, ordering="last_name")
    def display_header(self, obj: User) -> list[str]:
        # (title, subtitle, initials in a circle)
        return [obj.full_name, obj.email, obj.initials]

    @display(
        description="Active",
        ordering="is_active",
        label={"active": "success", "inactive": "danger"},
    )
    def display_is_active(self, obj: User) -> tuple[str, str]:
        if obj.is_active:
            return "active", "Active"
        return "inactive", "Inactive"

    @display(
        description="Staff",
        ordering="is_staff",
        label={"staff": "info"},  # regular users get a neutral label
    )
    def display_is_staff(self, obj: User) -> tuple[str, str]:
        if obj.is_staff:
            return "staff", "Staff"
        return "user", "Regular"

    @display(description="Posts", ordering="posts_count")
    def display_posts_count(self, obj: User) -> int:
        return obj.posts_count

    @action(description="Activate selected users", permissions=["change"])
    def activate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        updated: int = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) activated.")

    @action(description="Deactivate selected users", permissions=["change"])
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        updated: int = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated.")