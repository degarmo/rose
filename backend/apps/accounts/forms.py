from unfold.forms import UserChangeForm as BaseUserChangeForm
from unfold.forms import UserCreationForm as BaseUserCreationForm
from unfold.widgets import UnfoldAdminTextInputWidget

from .models import User


class UserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "display_name")


class UserChangeForm(BaseUserChangeForm):
    class Meta:
        model = User
        fields = ("email", "display_name", "legal_name", "phone")
        widgets = {"phone": UnfoldAdminTextInputWidget(attrs={"autocomplete": "off"})}
