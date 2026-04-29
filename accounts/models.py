from django.contrib.auth.models import AbstractUser
from django.db import models

from accounts.managers import UserManager
from accounts.validators import (
    get_avatar_validators,
    validate_phone_number,
)


GENDER_CHOICES = (
    ('male', 'Male'),
    ('female', 'Female'),
)


class UserRole(models.TextChoices):
    """Tập trung danh sách role để tránh lặp magic string ('patient'/'doctor')."""

    PATIENT = 'patient', 'Patient'
    DOCTOR = 'doctor', 'Doctor'


class User(AbstractUser):
    username = None
    role = models.CharField(
        max_length=12,
        choices=UserRole.choices,
        db_index=True,
        error_messages={'required': 'Role must be provided'},
    )
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, blank=True, null=True, default=''
    )
    email = models.EmailField(
        unique=True,
        blank=False,
        error_messages={'unique': 'A user with that email already exists.'},
    )
    phone_number = models.CharField(
        unique=True,
        blank=True,
        null=True,
        max_length=20,
        validators=[validate_phone_number],
        error_messages={'unique': 'A user with that phone number already exists.'},
    )
    image = models.ImageField(
        null=True,
        blank=True,
        default='avatar.png',
        upload_to='avatars/',
        validators=get_avatar_validators(),
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return self.email

    # Vẫn giữ tương thích ngược với code dùng __unicode__ ở Python 2
    def __unicode__(self):
        return self.email

    @property
    def is_doctor(self):
        return self.role == UserRole.DOCTOR

    @property
    def is_patient(self):
        return self.role == UserRole.PATIENT

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email

    def save(self, *args, **kwargs):
        """Bảo vệ trường role: chỉ cho phép thay đổi khi có cờ _bypass_role_check.

        Tránh privilege escalation nếu request đến từ form không kiểm soát.
        """
        if self.pk is not None and not getattr(self, '_bypass_role_check', False):
            try:
                original_role = type(self).objects.values_list('role', flat=True).get(pk=self.pk)
            except type(self).DoesNotExist:
                original_role = None
            if original_role and original_role != self.role:
                self.role = original_role
        super().save(*args, **kwargs)


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='doctor_profile'
    )
    specialization = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    qualifications = models.TextField(blank=True, null=True, help_text='Bằng cấp chuyên môn')
    experience = models.TextField(blank=True, null=True, help_text='Kinh nghiệm làm việc')
    biography = models.TextField(blank=True, null=True, help_text='Giới thiệu bản thân')

    def __str__(self):
        return f'Profile of Dr. {self.user.first_name} {self.user.last_name}'
