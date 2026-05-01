from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import User, DoctorProfile, UserRole


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom UserAdmin kế thừa BaseUserAdmin để giữ tính năng:
    - Hash password tự động khi tạo user qua admin
    - Có form đặt lại mật khẩu riêng
    - Có changelist + permissions tốt
    """

    # Vì USERNAME_FIELD = 'email', không có 'username'
    list_display = (
        'avatar_thumb', 'email', 'full_name', 'role_badge',
        'phone_number', 'is_active', 'date_joined',
    )
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-date_joined',)
    list_per_page = 25
    list_select_related = True

    # Form khi xem/sửa user
    fieldsets = (
        ('Thông tin đăng nhập', {'fields': ('email', 'password')}),
        ('Hồ sơ cá nhân', {'fields': ('first_name', 'last_name', 'gender', 'phone_number', 'image')}),
        ('Phân quyền', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        ('Ngày tháng', {'fields': ('last_login', 'date_joined'), 'classes': ('collapse',)}),
    )

    # Form khi TẠO user mới (admin/users/add/) - hiện cả 2 ô password để hash đúng
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'role', 'first_name', 'last_name',
                       'phone_number', 'password1', 'password2'),
        }),
    )

    actions = ['activate_users', 'deactivate_users']

    # ----- Custom display methods -----
    def full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'.strip() or '-'
    full_name.short_description = 'Họ tên'

    def role_badge(self, obj):
        colors = {
            UserRole.DOCTOR: '#16a34a',
            UserRole.PATIENT: '#3b82f6',
        }
        color = colors.get(obj.role, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:11px;font-weight:bold">{}</span>',
            color, obj.get_role_display() or obj.role or '-',
        )
    role_badge.short_description = 'Vai trò'

    def avatar_thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:32px;height:32px;border-radius:50%;object-fit:cover">',
                obj.image.url,
            )
        return format_html('<span style="color:#9ca3af">—</span>')
    avatar_thumb.short_description = ''

    # ----- Bulk actions -----
    @admin.action(description='Kích hoạt tài khoản đã chọn')
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Đã kích hoạt {updated} tài khoản.')

    @admin.action(description='Vô hiệu hóa tài khoản đã chọn')
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Đã vô hiệu hóa {updated} tài khoản.')


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('doctor_name', 'doctor_email', 'specialization', 'has_qualifications')
    list_filter = ('specialization',)
    search_fields = (
        'user__first_name', 'user__last_name', 'user__email',
        'specialization', 'qualifications',
    )
    list_select_related = ('user',)
    list_per_page = 25

    fieldsets = (
        ('Bác sĩ', {'fields': ('user',)}),
        ('Chuyên môn', {'fields': ('specialization', 'qualifications', 'experience')}),
        ('Giới thiệu', {'fields': ('biography',)}),
    )

    def doctor_name(self, obj):
        return f'BS. {obj.user.first_name} {obj.user.last_name}'
    doctor_name.short_description = 'Bác sĩ'

    def doctor_email(self, obj):
        return obj.user.email
    doctor_email.short_description = 'Email'

    def has_qualifications(self, obj):
        return bool(obj.qualifications)
    has_qualifications.short_description = 'Có bằng cấp?'
    has_qualifications.boolean = True
