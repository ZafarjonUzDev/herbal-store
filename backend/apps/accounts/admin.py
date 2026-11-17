"""Django standart UserAdmin imkoniyatlarini saqlaymiz."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group

from .models import User

class UzbekPermissionLabelsMixin:
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        field = super().formfield_for_manytomany(db_field, request, **kwargs)
        if field is not None and db_field.name in ('permissions', 'user_permissions'):
            field.queryset = field.queryset.select_related('content_type')
            field.label_from_instance = self.permission_label
        return field

    @staticmethod
    def permission_label(permission):
        actions = {'add': 'Qo‘shish', 'change': 'Tahrirlash', 'delete': 'O‘chirish', 'view': 'Ko‘rish'}
        action = actions.get(permission.codename.split('_', 1)[0])
        model = permission.content_type.model_class()
        if action and model is not None:
            return f'{model._meta.app_config.verbose_name} | {model._meta.verbose_name} | {action}'
        return permission.name


@admin.register(User)
class HerbalUserAdmin(UzbekPermissionLabelsMixin, UserAdmin):
    pass


admin.site.unregister(Group)


@admin.register(Group)
class HerbalGroupAdmin(UzbekPermissionLabelsMixin, GroupAdmin):
    pass
