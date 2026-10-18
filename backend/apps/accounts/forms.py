from django import forms
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm

from .models import User


class UserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "display_name")


class UserChangeForm(BaseUserChangeForm):
    class Meta:
        model = User
        fields = ("email", "display_name", "legal_name", "phone")
        widgets = {"phone": forms.TextInput(attrs={"autocomplete": "off"})}
