import secrets
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        full = f'{self.first_name} {self.last_name}'.strip()
        return full if full else self.email

    def get_short_name(self) -> str:
        return self.first_name if self.first_name else self.email.split('@')[0]

class EmailVerification(models.Model):
    COOLDOWN_SECONDS = 60
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verifications')
    otp_hash = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Verification'
        verbose_name_plural = 'Email Verifications'

    @classmethod
    def can_resend_otp(cls, user) -> tuple[bool, int]:
        last_record = cls.objects.filter(user=user).order_by('-created_at').first()
        if not last_record:
            return (True, 0)
        elapsed = (timezone.now() - last_record.created_at).total_seconds()
        if elapsed < cls.COOLDOWN_SECONDS:
            return (False, max(1, int(cls.COOLDOWN_SECONDS - elapsed)))
        return (True, 0)

    @classmethod
    def generate_otp(cls, user):
        cls.objects.filter(user=user).delete()
        plain_otp = str(secrets.randbelow(900000) + 100000)
        otp_hash = make_password(plain_otp)
        expires_at = timezone.now() + timedelta(minutes=10)
        record = cls.objects.create(user=user, otp_hash=otp_hash, expires_at=expires_at)
        return (plain_otp, record)

    def check_otp(self, plain_otp: str) -> bool:
        if self.attempts >= 5:
            return False
        self.attempts += 1
        self.save(update_fields=['attempts'])
        if timezone.now() > self.expires_at:
            return False
        return check_password(plain_otp.strip(), self.otp_hash)

    def is_valid(self) -> bool:
        return timezone.now() <= self.expires_at and self.attempts < 5

    def __str__(self) -> str:
        return f'OTP verification for {self.user.email} (Expires {self.expires_at})'

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True, help_text='Contact telephone/mobile number')
    street_address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.email}'s Profile ({('Verified' if self.user.is_verified else 'Unverified')})"

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    elif hasattr(instance, 'profile'):
        instance.profile.save()

class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state_or_division = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='Bangladesh')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.full_name} - {self.street_address}, {self.city}'
