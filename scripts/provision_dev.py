"""Ajratilgan lokal Compose bazasida dastlabki Django Admin yaratish.

Random parol faqat .secrets/dev-admin.json (0600)ga yoziladi; terminal,
subprocess argumentlari yoki repository source'iga kiritilmaydi.
"""

import json
import os
from pathlib import Path
import secrets
import subprocess


root = Path(__file__).resolve().parent.parent
credentials = root / '.secrets' / 'dev-admin.json'
if credentials.exists():
    print('Lokal Admin credential fayli mavjud; qayta yaratilmagan.')
else:
    username = 'localadmin'
    password = secrets.token_urlsafe(24)
    script = '\n'.join([
        'from django.conf import settings',
        'from django.contrib.auth import get_user_model',
        "assert settings.DEBUG and settings.DATABASES['default']['HOST'] == 'db'",
        'User = get_user_model()',
        f'username = {username!r}',
        'if User.objects.filter(username=username).exists():',
        "    print('EXISTS')",
        'else:',
        f'    User.objects.create_superuser(username=username, password={password!r})',
        "    print('CREATED')",
        '',
    ])
    completed = subprocess.run(
        ['docker', 'compose', '-f', 'docker-compose.yml', '-f',
         'docker-compose.dev.yml', 'exec', '-T', 'backend', 'python',
         'manage.py', 'shell'],
        cwd=root, input=script, text=True, capture_output=True,
    )
    if completed.returncode or 'CREATED' not in completed.stdout.splitlines():
        raise SystemExit('Admin yaratilmagan (mavjud username yoki muhit xatosi). '
                         'Mavjud credential o‘zgartirilmadi; createsuperuser ishlating.')
    credentials.parent.mkdir(mode=0o700, exist_ok=True)
    descriptor = os.open(credentials, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        json.dump({'username': username, 'password': password}, output)
        output.write('\n')
    print('Lokal Admin yaratildi; credential faqat .secrets/dev-admin.json ichida.')
