"""Read-only fingerprints for catalog, accounts and saved-product integrity.

Run with the intended Django environment, or feed this file to the existing
backend container's Python stdin. Only counts and SHA256 digests are printed.
"""

import hashlib
import json
import os
from pathlib import Path
import sys


def main():
    backend = Path.cwd() if Path('manage.py').is_file() else Path(__file__).resolve().parent.parent / 'backend'
    if backend.is_dir():
        sys.path.insert(0, str(backend))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from django.contrib.auth import get_user_model
    from django.db import connection, transaction
    from apps.catalog.models import Category, Product
    from apps.favorites.models import SavedProduct

    required_blanks = {}

    def fingerprint(model, fields, required=()):
        digest = hashlib.sha256()
        digest.update(json.dumps(fields, separators=(',', ':')).encode('utf-8') + b'\n')
        count = 0
        for field in required:
            required_blanks[f'{model._meta.label_lower}.{field}'] = 0
        for row in model.objects.order_by('pk').values_list(*fields).iterator(chunk_size=1000):
            count += 1
            digest.update(json.dumps(row, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8') + b'\n')
            for field in required:
                value = row[fields.index(field)]
                if not isinstance(value, str) or not value.strip():
                    required_blanks[f'{model._meta.label_lower}.{field}'] += 1
        return {'count': count, 'sha256': digest.hexdigest()}

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        result = {
            'format': 1,
            'categories': fingerprint(Category, (
                'id', 'name', 'slug', 'created_at', 'updated_at',
            ), required=('name',)),
            'products': fingerprint(Product, (
                'id', 'category_id', 'name', 'slug', 'image', 'price',
                'is_available', 'description', 'detailed_information', 'created_at', 'updated_at',
            ), required=('name', 'description', 'detailed_information')),
            'users': fingerprint(get_user_model(), (
                'id', 'username', 'password', 'first_name', 'last_name', 'email',
                'is_superuser', 'is_staff', 'is_active', 'date_joined', 'last_login',
            )),
            'favorites': fingerprint(SavedProduct, (
                'id', 'user_id', 'product_id', 'created_at',
            )),
            'legacy_required_blank_counts': required_blanks,
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
