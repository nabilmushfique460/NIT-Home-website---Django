import re
from typing import Optional
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

# Password complexity validator verifying strength policies
class ComplexityPasswordValidator:

    def validate(self, password: str, user: Optional[object] = None) -> None:
        # Check minimum length requirement
        if len(password) < 8:
            raise ValidationError(
                _('Password must be at least 8 characters long.'),
                code='password_too_short'
            )
        # Check uppercase letter requirement
        if not re.search('[A-Z]', password):
            raise ValidationError(
                _('Password must contain at least one uppercase letter (A-Z).'),
                code='password_no_upper'
            )
        # Check lowercase letter requirement
        if not re.search('[a-z]', password):
            raise ValidationError(
                _('Password must contain at least one lowercase letter (a-z).'),
                code='password_no_lower'
            )
        # Check numeric digit requirement
        if not re.search('[0-9]', password):
            raise ValidationError(
                _('Password must contain at least one number (0-9).'),
                code='password_no_number'
            )
        # Check special character requirement
        if not re.search('[^A-Za-z0-9]', password):
            raise ValidationError(
                _('Password must contain at least one special character (e.g. !@#$%^&*).'),
                code='password_no_special'
            )

    def get_help_text(self) -> str:
        return _(
            'Your password must be at least 8 characters long and contain '
            'at least one uppercase letter, one lowercase letter, one digit, '
            'and one special character.'
        )

# Helper function executing complexity validation against a password string
def validate_strong_password(password: str) -> None:
    validator = ComplexityPasswordValidator()
    validator.validate(password)
