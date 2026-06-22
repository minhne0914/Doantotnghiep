from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils.html import format_html

from .models import DoctorAccount, DoctorProfile, PatientAccount, User, UserRole


class DoctorProfileInline(admin.StackedInline):
    """Edit professional details on the same page as the doctor's account."""

    model = DoctorProfile
    fk_name = 'user'
    extra = 0
    max_num = 1
    can_delete = False
    verbose_name = 'Hồ sơ chuyên môn'
    verbose_name_plural = 'Hồ sơ chuyên môn bác sĩ'
    fields = ('specialization', 'qualifications', 'experience', 'biography')


class DoctorProfileAdminForm(forms.ModelForm):
    first_name = forms.CharField(label='Tên', max_length=150)
    last_name = forms.CharField(label='Họ', max_length=150, required=False)
    email = forms.EmailField(label='Email')
    gender = forms.ChoiceField(
        label='Giới tính',
        choices=User._meta.get_field('gender').choices,
        required=False,
    )
    phone_number = forms.CharField(label='Số điện thoại', max_length=20, required=False)
    image = forms.ImageField(label='Ảnh đại diện', required=False)

    class Meta:
        model = DoctorProfile
        fields = ('user', 'specialization', 'qualifications', 'experience', 'biography')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user if self.instance and self.instance.pk else None
        self._account_user = user
        if user:
            # The account is displayed as a read-only link on existing profiles.
            # Keep the bound relationship while allowing the edit form to submit.
            if 'user' in self.fields:
                self.fields['user'].required = False
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            self.fields['gender'].initial = user.gender or ''
            self.fields['phone_number'].initial = user.phone_number or ''

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        user_id = self.instance.user_id if self.instance and self.instance.pk else None
        if User.objects.exclude(pk=user_id).filter(email__iexact=email).exists():
            raise forms.ValidationError('Email này đã được sử dụng bởi tài khoản khác.')
        return email

    def save(self, commit=True):
        account_user = (
            self._account_user
            if self._account_user is not None
            else self.cleaned_data['user']
        )
        profile = super().save(commit=False)
        profile.user = account_user
        user = account_user
        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()
        user.email = self.cleaned_data['email']
        user.gender = self.cleaned_data['gender']
        user.phone_number = self.cleaned_data['phone_number'].strip() or None
        if self.cleaned_data.get('image'):
            user.image = self.cleaned_data['image']

        if commit:
            user.save()
            profile.save()
            self.save_m2m()
        return profile


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
    list_display_links = ('email', 'full_name')

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
                       'gender', 'phone_number', 'image', 'password1', 'password2'),
        }),
    )

    actions = ['activate_users', 'deactivate_users']

    def get_fieldsets(self, request, obj=None):
        if obj and obj.role == UserRole.DOCTOR:
            profile_title = 'Hồ sơ cá nhân bác sĩ'
        elif obj and obj.role == UserRole.PATIENT:
            profile_title = 'Hồ sơ cá nhân bệnh nhân'
        else:
            profile_title = 'Hồ sơ cá nhân'

        return (
            ('Thông tin đăng nhập', {'fields': ('email', 'password')}),
            (profile_title, {
                'fields': ('first_name', 'last_name', 'gender', 'phone_number', 'image'),
            }),
            ('Phân quyền', {
                'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
                'classes': ('collapse',),
            }),
            ('Ngày tháng', {'fields': ('last_login', 'date_joined'), 'classes': ('collapse',)}),
        )

    def get_inlines(self, request, obj=None):
        if obj and obj.role == UserRole.DOCTOR:
            return (DoctorProfileInline,)
        return ()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.role == UserRole.DOCTOR:
            DoctorProfile.objects.get_or_create(user=obj)

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


class RoleAccountAdmin(UserAdmin):
    """Shared admin behavior for the dedicated patient and doctor lists."""

    target_role = None
    profile_title = 'Hồ sơ cá nhân'

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 'gender', 'phone_number',
                'image', 'password1', 'password2',
            ),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=self.target_role)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return (
            ('Thông tin đăng nhập', {'fields': ('email', 'password')}),
            (self.profile_title, {
                'fields': ('first_name', 'last_name', 'gender', 'phone_number', 'image'),
            }),
            ('Trạng thái tài khoản', {'fields': ('is_active',)}),
            ('Ngày tháng', {'fields': ('last_login', 'date_joined'), 'classes': ('collapse',)}),
        )

    def save_model(self, request, obj, form, change):
        obj.role = self.target_role
        obj._bypass_role_check = True
        super().save_model(request, obj, form, change)


@admin.register(PatientAccount)
class PatientAccountAdmin(RoleAccountAdmin):
    target_role = UserRole.PATIENT
    profile_title = 'Hồ sơ bệnh nhân'
    # Keep the patient directory focused on locating a patient quickly.
    list_filter = ()
    search_fields = ('first_name', 'last_name', 'email')


@admin.register(DoctorAccount)
class DoctorAccountAdmin(RoleAccountAdmin):
    target_role = UserRole.DOCTOR
    profile_title = 'Hồ sơ bác sĩ'


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    form = DoctorProfileAdminForm
    list_display = ('doctor_name', 'doctor_email', 'specialization', 'has_qualifications')
    list_display_links = ('doctor_name', 'doctor_email')
    list_filter = ('specialization',)
    search_fields = (
        'user__first_name', 'user__last_name', 'user__email',
        'specialization', 'qualifications',
    )
    list_select_related = ('user',)
    list_per_page = 25
    readonly_fields = ('doctor_account',)

    def get_fieldsets(self, request, obj=None):
        account_field = 'doctor_account' if obj else 'user'
        return (
            ('Tài khoản bác sĩ', {
                'fields': (
                    account_field, 'first_name', 'last_name', 'email', 'gender',
                    'phone_number', 'image',
                ),
            }),
            ('Chuyên môn', {'fields': ('specialization', 'qualifications', 'experience')}),
            ('Giới thiệu', {'fields': ('biography',)}),
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = User.objects.filter(role=UserRole.DOCTOR).order_by(
                'first_name', 'last_name', 'email'
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def doctor_name(self, obj):
        return f'BS. {obj.user.first_name} {obj.user.last_name}'
    doctor_name.short_description = 'Bác sĩ'

    def doctor_account(self, obj):
        url = reverse('admin:accounts_doctoraccount_change', args=[obj.user_id])
        return format_html(
            '<a href="{}">{} ({})</a>',
            url,
            obj.user.full_name,
            obj.user.email,
        )
    doctor_account.short_description = 'Tài khoản bác sĩ'

    def doctor_email(self, obj):
        return obj.user.email
    doctor_email.short_description = 'Email'

    def has_qualifications(self, obj):
        return bool(obj.qualifications)
    has_qualifications.short_description = 'Có bằng cấp?'
    has_qualifications.boolean = True
