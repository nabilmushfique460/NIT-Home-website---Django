from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class NitAccountAdapter(DefaultAccountAdapter):

    def is_open_for_signup(self, request) -> bool:
        return True


class NitSocialAccountAdapter(DefaultSocialAccountAdapter):

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        # Google OAuth already verified ownership of email address
        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=['is_verified'])
        return user
