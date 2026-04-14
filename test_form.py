import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mlhospital.settings")
django.setup()

from accounts.forms import PatientRegistrationForm

form = PatientRegistrationForm({
    'first_name': 'Test',
    'last_name': 'User',
    'email': 'test@example.com',
    'phone_number': '0123456789',
    'password1': 'StrongPassword123!',
    'password2': 'StrongPassword123!',
    'gender': 'male'
})

print("Is valid?", form.is_valid())
if not form.is_valid():
    print("Errors:", form.errors)
