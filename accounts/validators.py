import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexityPasswordValidator:
    """
    Validates that the password contains at least:
    - 8 characters
    - One uppercase letter (A-Z)
    - One lowercase letter (a-z)
    - One numeric digit (0-9)
    - One special character (!@#$%^&* etc.)
    """

    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError(
                _("Password must be at least 8 characters long."),
                code='password_too_short',
            )
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter (A-Z)."),
                code='password_no_upper',
            )
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter (a-z)."),
                code='password_no_lower',
            )
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                _("Password must contain at least one number (0-9)."),
                code='password_no_number',
            )
        if not re.search(r'[^A-Za-z0-9]', password):
            raise ValidationError(
                _("Password must contain at least one special character (e.g. !@#$%^&*)."),
                code='password_no_special',
            )

    def get_help_text(self):
        return _(
            "Your password must be at least 8 characters long and contain at least one uppercase letter, "
            "one lowercase letter, one digit, and one special character."
        )


def validate_strong_password(password: str):
    """Standalone function to validate password complexity."""
    validator = ComplexityPasswordValidator()
    validator.validate(password)
