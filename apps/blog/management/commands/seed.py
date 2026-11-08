import random
import re
import time
from typing import Any

from faker import Faker

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils.text import slugify

from apps.blog.models import Category, Comment, Post, Tag

User = get_user_model()

# Defaults for the arguments
DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500

# Users
SEED_PASSWORD = "seedpass123"
EMAIL_DOMAINS = ("example.com", "blog.kz", "mail.com")
INACTIVE_USERS_SHARE = 0.15
STAFF_USERS_SHARE = 0.1
EMAIL_FORBIDDEN_CHARS = re.compile(r"[^a-z0-9.]")
FIRST_DUPLICATE_SUFFIX = 2

# Posts
PUBLISHED_POSTS_SHARE = 0.7
POSTS_WITHOUT_CATEGORY_SHARE = 0.1
MIN_TAGS_PER_POST = 0
MAX_TAGS_PER_POST = 5
MIN_TITLE_WORDS = 3
MAX_TITLE_WORDS = 8
MIN_PARAGRAPHS = 3
MAX_PARAGRAPHS = 6
PARAGRAPH_SEPARATOR = "\n\n"
SLUG_MAX_LEN: int = Post._meta.get_field("slug").max_length

# Comments
MIN_COMMENT_SENTENCES = 1
MAX_COMMENT_SENTENCES = 3

CATEGORY_NAMES = (
    "Python",
    "Django",
    "DevOps",
    "Databases",
    "Frontend",
    "Machine Learning",
    "Security",
    "Career",
)
TAG_NAMES = (
    "beginner",
    "advanced",
    "tutorial",
    "best practices",
    "performance",
    "testing",
    "docker",
    "kubernetes",
    "postgresql",
    "rest api",
    "orm",
    "async",
    "linux",
    "git",
    "ci/cd",
    "javascript",
    "react",
    "pandas",
    "interview",
    "open source",
)

SUMMARY_LABEL_WIDTH = 11
SUMMARY_NUMBER_WIDTH = 4


class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--users",
            type=int,
            default=DEFAULT_USERS,
            help="Number of users to create",
        )
        parser.add_argument(
            "--posts",
            type=int,
            default=DEFAULT_POSTS,
            help="Number of posts to create",
        )
        parser.add_argument(
            "--comments",
            type=int,
            default=DEFAULT_COMMENTS,
            help="Number of comments to create",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing data before seeding",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        users_count: int = options["users"]
        posts_count: int = options["posts"]
        comments_count: int = options["comments"]
        clear: bool = options["clear"]

        self._check_not_negative(
            users=users_count,
            posts=posts_count,
            comments=comments_count,
        )

        self.fake = Faker()
        start_time: float = time.perf_counter()

        # One transaction: if anything fails, nothing is saved.
        with transaction.atomic():
            if clear:
                self._clear()
                self.stdout.write(self.style.WARNING("Existing data deleted."))

            users_created: int = self._create_users(users_count)

            has_users: bool = User.objects.exists()
            if (posts_count or comments_count) and not has_users:
                raise CommandError(
                    "There are no users. Create users first (--users N)."
                )

            categories_created: int = self._create_categories()
            tags_created: int = self._create_tags()
            posts_created: int = self._create_posts(posts_count)
            comments_created: int = self._create_comments(comments_count)

        elapsed: float = time.perf_counter() - start_time

        self._write_line("Users", users_created)
        self._write_line("Categories", categories_created)
        self._write_line("Tags", tags_created)
        self._write_line("Posts", posts_created)
        self._write_line("Comments", comments_created)
        self.stdout.write(self.style.SUCCESS(f"Done in {elapsed:.2f} seconds"))

    def _check_not_negative(self, **counts: int) -> None:
        name: str
        value: int
        for name, value in counts.items():
            if value < 0:
                raise CommandError(f"--{name} must be 0 or greater, got {value}.")

    def _clear(self) -> None:
        """Delete all seeded data. Superusers stay, so you can still log in."""
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Tag.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def _build_email(self, first_name: str, last_name: str, used: set[str]) -> str:
        """emily.johnson@example.com, emily.johnson2@example.com, ..."""
        local_part: str = EMAIL_FORBIDDEN_CHARS.sub(
            "", f"{first_name}.{last_name}".lower()
        )
        domain: str = random.choice(EMAIL_DOMAINS)

        email: str = f"{local_part}@{domain}"
        suffix: int = FIRST_DUPLICATE_SUFFIX
        while email in used:
            email = f"{local_part}{suffix}@{domain}"
            suffix += 1

        used.add(email)
        return email

    def _create_users(self, count: int) -> int:
        if count == 0:
            return 0

        used_emails: set[str] = set(User.objects.values_list("email", flat=True))
        # Hashing is slow on purpose, so we hash the password only once.
        password_hash: str = make_password(SEED_PASSWORD)

        users: list[User] = []
        for _ in range(count):
            first_name: str = self.fake.first_name()
            last_name: str = self.fake.last_name()
            users.append(
                User(
                    email=self._build_email(first_name, last_name, used_emails),
                    first_name=first_name,
                    last_name=last_name,
                    password=password_hash,
                    is_active=random.random() >= INACTIVE_USERS_SHARE,
                    is_staff=random.random() < STAFF_USERS_SHARE,
                )
            )

        User.objects.bulk_create(users)
        return len(users)

    def _create_categories(self) -> int:
        existing: set[str] = set(Category.objects.values_list("name", flat=True))
        categories: list[Category] = [
            Category(name=name, slug=slugify(name))
            for name in CATEGORY_NAMES
            if name not in existing
        ]
        Category.objects.bulk_create(categories)
        return len(categories)

    def _create_tags(self) -> int:
        existing: set[str] = set(Tag.objects.values_list("name", flat=True))
        tags: list[Tag] = [
            Tag(name=name, slug=slugify(name))
            for name in TAG_NAMES
            if name not in existing
        ]
        Tag.objects.bulk_create(tags)
        return len(tags)

    def _build_slug(self, title: str, used: set[str]) -> str:
        """my-post, my-post-2, my-post-3, ... (never longer than the field)."""
        base: str = slugify(title)[:SLUG_MAX_LEN].strip("-")
        slug: str = base
        number: int = FIRST_DUPLICATE_SUFFIX
        while slug in used:
            suffix: str = f"-{number}"
            slug = f"{base[: SLUG_MAX_LEN - len(suffix)].strip('-')}{suffix}"
            number += 1

        used.add(slug)
        return slug

    def _build_title(self) -> str:
        words: int = random.randint(MIN_TITLE_WORDS, MAX_TITLE_WORDS)
        return self.fake.sentence(nb_words=words).rstrip(".")

    def _build_body(self) -> str:
        paragraphs: int = random.randint(MIN_PARAGRAPHS, MAX_PARAGRAPHS)
        return PARAGRAPH_SEPARATOR.join(self.fake.paragraphs(nb=paragraphs))

    def _create_posts(self, count: int) -> int:
        if count == 0:
            return 0

        author_ids: list[int] = list(User.objects.values_list("id", flat=True))
        category_ids: list[int] = list(Category.objects.values_list("id", flat=True))
        tag_ids: list[int] = list(Tag.objects.values_list("id", flat=True))
        used_slugs: set[str] = set(Post.objects.values_list("slug", flat=True))

        posts: list[Post] = []
        for _ in range(count):
            title: str = self._build_title()
            has_category: bool = random.random() >= POSTS_WITHOUT_CATEGORY_SHARE
            is_published: bool = random.random() < PUBLISHED_POSTS_SHARE
            posts.append(
                Post(
                    author_id=random.choice(author_ids),
                    title=title,
                    slug=self._build_slug(title, used_slugs),
                    body=self._build_body(),
                    category_id=random.choice(category_ids) if has_category else None,
                    status=(
                        Post.Status.PUBLISHED if is_published else Post.Status.DRAFT
                    ),
                )
            )

        # After bulk_create the posts already have ids.
        Post.objects.bulk_create(posts)

        max_tags: int = min(MAX_TAGS_PER_POST, len(tag_ids))
        post: Post
        for post in posts:
            tags_count: int = random.randint(MIN_TAGS_PER_POST, max_tags)
            if tags_count:
                post.tags.set(random.sample(tag_ids, k=tags_count))

        return len(posts)

    def _create_comments(self, count: int) -> int:
        if count == 0:
            return 0

        published_post_ids: list[int] = list(
            Post.objects.filter(status=Post.Status.PUBLISHED).values_list(
                "id", flat=True
            )
        )
        if not published_post_ids:
            raise CommandError(
                "There are no published posts to comment on. "
                "Create posts first (--posts N)."
            )

        author_ids: list[int] = list(User.objects.values_list("id", flat=True))

        comments: list[Comment] = []
        for _ in range(count):
            sentences: int = random.randint(
                MIN_COMMENT_SENTENCES, MAX_COMMENT_SENTENCES
            )
            comments.append(
                Comment(
                    post_id=random.choice(published_post_ids),
                    author_id=random.choice(author_ids),
                    body=self.fake.paragraph(
                        nb_sentences=sentences,
                        variable_nb_sentences=False,
                    ),
                )
            )

        Comment.objects.bulk_create(comments)
        return len(comments)

    def _write_line(self, label: str, count: int) -> None:
        title: str = f"{label}:"
        text: str = (
            f"{title:<{SUMMARY_LABEL_WIDTH}}{count:>{SUMMARY_NUMBER_WIDTH}} created"
        )
        self.stdout.write(self.style.SUCCESS(text))