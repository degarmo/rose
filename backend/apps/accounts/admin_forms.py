"""The confirmation page's form for an action on members (apps.accounts.member_actions):
only the fields that action needs. The fresh two-step code is checked by the action itself,
once for the whole batch."""

from django import forms
from django.utils import timezone

CONFIRM_WORD = "ERASE"

LENGTHS = [("7", "7 days"), ("30", "30 days"), ("custom", "Until a date")]


def _field(name):
    return {
        "rule": forms.CharField(
            label="Rule broken",
            max_length=200,
            help_text="The house rule or guideline this relates to.",
            widget=forms.TextInput(attrs={"list": "rose-rules", "autocomplete": "off"}),
        ),
        "reason": forms.CharField(
            label="Reason",
            max_length=2000,
            help_text="Goes in the log with your name and the time. The member reads it in "
            "Settings, under Notices, for moderation decisions.",
            widget=forms.Textarea(attrs={"rows": 3}),
        ),
        "length": forms.ChoiceField(
            label="How long", choices=LENGTHS, initial="7", widget=forms.RadioSelect
        ),
        "until": forms.DateField(
            label="Last day",
            required=False,
            help_text="For “Until a date”.",
            widget=forms.DateInput(attrs={"type": "date"}),
        ),
        "block_email": forms.BooleanField(
            label="Block re-registration with this email", required=False
        ),
        "include_email": forms.BooleanField(
            label="Include email addresses",
            required=False,
            help_text="The export is logged; with email addresses, it is logged as such.",
        ),
        "confirm": forms.CharField(
            label=f"Type {CONFIRM_WORD} to confirm",
            max_length=10,
            widget=forms.TextInput(attrs={"autocomplete": "off"}),
        ),
        "code": forms.CharField(
            label="Six-digit code from your authenticator app",
            max_length=8,
            help_text="A new code, not one you have just used to log in.",
            widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code"}),
        ),
    }[name]


class MemberActionForm(forms.Form):
    def __init__(self, spec, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in spec.fields:
            self.fields[name] = _field(name)

    def clean_until(self):
        until = self.cleaned_data.get("until")
        if self.data.get("length") == "custom":
            if until is None:
                raise forms.ValidationError("Choose the last day.")
            if until < timezone.localdate():
                raise forms.ValidationError("Choose a day from today on.")
        return until

    def clean_confirm(self):
        value = self.cleaned_data["confirm"].strip()
        if value != CONFIRM_WORD:
            raise forms.ValidationError(f"Type {CONFIRM_WORD} in capitals.")
        return value
