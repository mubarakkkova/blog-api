from unfold.forms import UserChangeForm, UserCreationForm

from apps.auths.models import User


class UserAdminCreationForm(UserCreationForm):
    """'Add user' form: email, first name, last name and password twice."""

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")

    def clean_email(self) -> str:
        """Store emails in lowercase, like UserManager does."""
        return self.cleaned_data["email"].lower()


class UserAdminChangeForm(UserChangeForm):
    """Edit form for our User (Django's form is built for `username`)."""

    class Meta:
        model = User
        fields = "__all__"

    def clean_email(self) -> str:
        return self.cleaned_data["email"].lower()