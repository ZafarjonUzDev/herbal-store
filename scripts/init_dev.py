"""Faqat lokal development uchun yangi, maxfiy .env yaratadi."""

import os
from pathlib import Path
import secrets


root = Path(__file__).resolve().parent.parent
target = root / '.env'
if target.exists():
    print('.env mavjud; qiymatlar saqlandi.')
else:
    content = (root / '.env.example').read_text()
    content = content.replace(
        'CHANGE_ME_GENERATE_NEW_SECRET_FOR_EACH_ENVIRONMENT', secrets.token_urlsafe(64)
    ).replace('CHANGE_ME_USE_A_STRONG_UNIQUE_PASSWORD', secrets.token_urlsafe(40))
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        output.write(content)
    print('Lokal .env yaratildi (0600); maxfiy qiymatlar chiqarilmadi.')
