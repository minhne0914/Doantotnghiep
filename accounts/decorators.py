"""Role-based access decorators.

Tránh dùng raw string 'patient'/'doctor' rải rác - chỉ dùng UserRole.
"""

from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from accounts.models import UserRole


def _check_role(required_role):
    """Factory tạo decorator kiểm tra role. Refactor để DRY giữa patient/doctor."""

    def decorator(function):
        @wraps(function)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, 'user', None)
            if user is None or not user.is_authenticated:
                return redirect('login')
            if user.role != required_role:
                raise PermissionDenied('Bạn không có quyền truy cập trang này.')
            return function(request, *args, **kwargs)

        return wrapper

    return decorator


user_is_patient = _check_role(UserRole.PATIENT)
user_is_doctor = _check_role(UserRole.DOCTOR)
