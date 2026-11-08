from typing import Any 

from django.core.management.base import BaseCommand, CommandParser

DEFAULT_USERS = 20
DEFAULT_POSTS = 100 
DEFAULT_COMMENTS = 500

class Command(BaseCommand):
    help = "Fill the database with fake data"

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

    def handle(self, *arg: Any, **options: Any) -> None:
        self.stdout.write(str(options))