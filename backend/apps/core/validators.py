from django.core.validators import RegexValidator

cta_url_validator = RegexValidator(
    regex=r"^(/[^/\s][^\s]*|/|https://[^\s]+|mailto:[^\s]+)$",
    message="Use a site path starting with /, an https:// address, or a mailto: link.",
)
