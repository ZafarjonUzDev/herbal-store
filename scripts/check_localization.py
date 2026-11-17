"""Run Django checks in a disposable PostgreSQL cluster, without using live data.

No Docker service is started, stopped or migrated. Connection settings and media
paths are supplied explicitly; the project's .env and .secrets are not inspected.
"""

import argparse
import os
from pathlib import Path
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def postgres_binaries():
    candidates = sorted(
        Path('/usr/lib/postgresql').glob('*/bin'),
        key=lambda path: tuple(int(part) for part in path.parent.name.split('.')),
        reverse=True,
    )
    for candidate in candidates:
        if (candidate / 'initdb').is_file() and (candidate / 'pg_ctl').is_file():
            return candidate
    executable = shutil.which('initdb')
    return Path(executable).parent if executable else None


def run(label, command, environment, cwd=None):
    print('\nRUN: ' + label, flush=True)
    subprocess.run(command, env=environment, cwd=cwd, check=True)
    print('PASS: ' + label, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, default=PROJECT_ROOT / '.venv/bin/python')
    parser.add_argument('--project-root', type=Path, default=PROJECT_ROOT, help='Optional source snapshot to verify with the same isolated runner.')
    parser.add_argument('--postgres-bin', type=Path, default=postgres_binaries())
    parser.add_argument('--restore-dump', type=Path, help='Restore an approved custom-format backup into the new isolated database before migrating it.')
    parser.add_argument('--browser', action='store_true', help='Also run actual frontend/API/Admin Chrome checks with generic test fixtures in the fresh temporary database.')
    parser.add_argument('--keep-data', action='store_true', help='Keep only this run\'s temporary cluster files after stopping it.')
    parser.add_argument('--label', action='append', default=[], help='Optional Django test label; repeat to select several modules.')
    args = parser.parse_args()
    project_root = args.project_root.absolute()
    if not args.python.is_file():
        parser.error('Python environment not found: ' + str(args.python))
    if not (project_root / 'backend/manage.py').is_file():
        parser.error('Project backend not found: ' + str(project_root))
    if args.postgres_bin is None:
        parser.error('PostgreSQL server binaries not found; pass --postgres-bin.')
    if args.restore_dump is not None and not args.restore_dump.is_file():
        parser.error('Backup not found: ' + str(args.restore_dump))
    if args.browser and args.restore_dump is not None:
        parser.error('--browser requires a fresh test database; do not combine with --restore-dump.')
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        parser.error('Run as a regular user; initdb cannot run as root.')

    directory = Path(tempfile.mkdtemp(prefix='herbal-localization-', dir='/tmp'))
    data = directory / 'postgres'
    socket_directory = directory / 'socket'
    socket_directory.mkdir(mode=0o700)
    (directory / 'media').mkdir()
    (directory / 'static').mkdir()
    environment = {key: value for key, value in os.environ.items() if not key.startswith('PG')}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]

    environment.update({
        'DJANGO_SECRET_KEY': secrets.token_urlsafe(64),
        'DJANGO_DEBUG': 'true',
        'DJANGO_ALLOWED_HOSTS': 'localhost,127.0.0.1,testserver',
        'DJANGO_CSRF_TRUSTED_ORIGINS': 'http://localhost:8080,http://127.0.0.1:8080',
        'DJANGO_TIME_ZONE': 'Asia/Tashkent',
        'POSTGRES_DB': 'herbal_localization',
        'POSTGRES_USER': 'herbal_test',
        'POSTGRES_PASSWORD': '',
        'POSTGRES_HOST': '127.0.0.1',
        'POSTGRES_PORT': str(port),
        'JWT_ACCESS_MINUTES': '15',
        'JWT_REFRESH_DAYS': '7',
        'DJANGO_SETTINGS_MODULE': 'herbal_localization_test_settings',
        'PYTHON_DOTENV_DISABLED': '1',
        'PYTHONPATH': os.pathsep.join((str(directory), str(project_root / 'backend'))),
        'PYTHONUNBUFFERED': '1',
        'HERBAL_LOCALIZATION_TEST_DIRECTORY': str(directory),
        'HERBAL_LOCALIZATION_PROJECT_ROOT': str(project_root),
    })
    (directory / 'herbal_localization_test_settings.py').write_text(
        'from config.settings import *\n'
        f'MEDIA_ROOT = {str(directory / "media")!r}\n'
        f'STATIC_ROOT = {str(directory / "static")!r}\n'
        "DATABASES['default']['TEST'] = {'NAME': 'test_herbal_localization'}\n",
        encoding='utf-8',
    )
    binary = lambda name: str(args.postgres_bin / name)
    started = False
    succeeded = False
    print('Isolated PostgreSQL directory: ' + str(directory), flush=True)
    print('Existing Docker services, live database and media remain untouched.', flush=True)
    try:
        run('initdb (new temporary directory)', [
            binary('initdb'), '-D', str(data), '--username=herbal_test',
            '--auth-local=trust', '--auth-host=trust', '--encoding=UTF8', '--no-locale',
        ], environment)
        options = shlex.join(['-h', '127.0.0.1', '-p', str(port), '-k', str(socket_directory)])
        run('start isolated PostgreSQL on localhost', [
            binary('pg_ctl'), '-D', str(data), '-l', str(directory / 'postgres.log'),
            '-o', options, '-w', 'start',
        ], environment)
        started = True
        run('create isolated database', [
            binary('createdb'), '-h', '127.0.0.1', '-p', str(port), '-U', 'herbal_test',
            '--maintenance-db=postgres', 'herbal_localization',
        ], environment)
        python = str(args.python.absolute())
        manage = [python, 'manage.py']
        backend = project_root / 'backend'
        run('Django system check', manage + ['check'], environment, backend)
        run('migration drift', manage + ['makemigrations', '--check', '--dry-run'], environment, backend)
        before = None
        if args.restore_dump is not None:
            run('restore backup into isolated database', [
                binary('pg_restore'), '--exit-on-error', '--no-owner', '--no-acl',
                '-h', '127.0.0.1', '-p', str(port), '-U', 'herbal_test',
                '-d', 'herbal_localization', str(args.restore_dump.resolve()),
            ], environment)
            before = subprocess.check_output([
                python, str(PROJECT_ROOT / 'scripts/catalog_integrity.py'),
            ], env=environment, cwd=backend)
            (directory / 'integrity-before.json').write_bytes(before)
        run('migrate isolated database', manage + ['migrate', '--noinput'], environment, backend)
        if before is not None:
            after = subprocess.check_output([
                python, str(PROJECT_ROOT / 'scripts/catalog_integrity.py'),
            ], env=environment, cwd=backend)
            (directory / 'integrity-after.json').write_bytes(after)
            if before != after:
                raise RuntimeError('Existing catalog/account/favorite fingerprints changed during isolated migration.')
            print('PASS: restored catalog/account/favorite counts and fingerprints preserved.', flush=True)
        run('Django regression suite', manage + ['test', '--noinput', *args.label], environment, backend)
        run('OpenAPI validation', manage + ['spectacular', '--validate', '--fail-on-warn', '--file', str(directory / 'openapi.yaml')], environment, backend)
        run('dependency consistency', [python, '-m', 'pip', 'check'], environment, backend)
        if args.browser:
            run('actual Chrome frontend/API/Admin integration', [
                python, str(PROJECT_ROOT / 'scripts/localization_browser.py'),
            ], environment, backend)
        succeeded = True
    finally:
        if started:
            print('\nStopping only the isolated temporary PostgreSQL cluster.', flush=True)
            subprocess.run([
                binary('pg_ctl'), '-D', str(data), '-m', 'fast', '-w', 'stop',
            ], env=environment, check=True)
        if args.keep_data:
            print('Temporary files retained: ' + str(directory), flush=True)
        else:
            shutil.rmtree(directory)
    if succeeded:
        print('\nPASS: isolated PostgreSQL/Django checks; no live migration was applied.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
