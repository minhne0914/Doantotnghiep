from django.contrib.auth.models import AbstractUser
from django.db import models
from accounts.managers import UserManager

GENDER_CHOICES = (
    ('male', 'Male'),
    ('female', 'Female'))


class User(AbstractUser):
    username = None
    role = models.CharField(max_length=12, error_messages={
        'required': "Role must be provided"
    })
    gender = models.CharField(max_length=10, blank=True, null=True, default="")
    email = models.EmailField(unique=True, blank=False,
                              error_messages={
                                  'unique': "A user with that email already exists.",
                              })
    phone_number = models.CharField(unique=True, blank=True, null=True, max_length=20,
                                    error_messages={
                                        'unique': "A user with that phone number already exists."
                                    })
    image = models.ImageField(null=True, blank=True,default='avatar.png', upload_to='avatars/')
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __unicode__(self):
        return self.email

    objects = UserManager()


class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.CharField(max_length=255, blank=True, null=True)
    qualifications = models.TextField(blank=True, null=True, help_text='Bằng cấp chuyên môn')
    experience = models.TextField(blank=True, null=True, help_text='Kinh nghiệm làm việc')
    biography = models.TextField(blank=True, null=True, help_text='Giới thiệu bản thân')

    def __str__(self):
        return f"Profile of Dr. {self.user.first_name} {self.user.last_name}"