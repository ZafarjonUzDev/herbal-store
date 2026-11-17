"""Actual browser integration for check_localization.py --browser only.

All fixtures and writes belong to its fresh temporary PostgreSQL database.
No live credentials, .env, translation service or external API is used.
"""

import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from browser_smoke import Browser


def main():
    directory = Path(os.environ.get('HERBAL_LOCALIZATION_TEST_DIRECTORY', '/nonexistent'))
    if not (
        directory.parent == Path('/tmp') and directory.name.startswith('herbal-localization-')
        and (directory / 'herbal_localization_test_settings.py').is_file()
        and os.environ.get('POSTGRES_DB') == 'herbal_localization'
        and os.environ.get('POSTGRES_HOST') == '127.0.0.1'
        and os.environ.get('PYTHON_DOTENV_DISABLED') == '1'
    ):
        raise RuntimeError('Use check_localization.py --browser with its fresh isolated database.')
    import django
    django.setup()
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.core.files.base import ContentFile
    from django.db import connection
    from PIL import Image
    from apps.catalog.models import Category, CategoryTranslation, Product, ProductTranslation
    from apps.favorites.models import SavedProduct

    if Category.objects.exists() or Product.objects.exists() or get_user_model().objects.exists():
        raise RuntimeError('Browser fixtures require a fresh empty temporary database.')
    with connection.cursor() as cursor:
        cursor.execute('SHOW data_directory')
        if not Path(cursor.fetchone()[0]).is_relative_to(directory):
            raise RuntimeError('Connected PostgreSQL is outside the isolated test directory.')

    category = Category.objects.create(name='Sinov toifasi', slug='browser-category')
    CategoryTranslation.objects.create(category=category, language='ru', name='Тестовая категория')
    image_file = directory / 'fixture.png'
    Image.new('RGB', (40, 60), '#254b3c').save(image_file)
    products = []
    for index in range(2):
        product = Product(
            category=category, name=f'Sinov mahsuloti {index + 1}',
            slug=f'browser-product-{index + 1}', price='12345.50', is_available=index == 0,
            description='Faqat dastur sinovi uchun tavsif.',
            detailed_information='Faqat dastur sinovi uchun ma’lumot.',
        )
        product.image.save(f'fixture-{index}.png', ContentFile(image_file.read_bytes()), save=True)
        products.append(product)
    ProductTranslation.objects.create(
        product=products[0], language='ru', name='Тестовое название',
        description='Тестовое описание.',
        detailed_information='Тестовые сведения. Только для проверки программы.',
    )
    User = get_user_model()
    password = secrets.token_urlsafe(24)
    existing = User.objects.create_user(username='browser_existing', password=password)
    admin_user = User.objects.create_superuser(username='browser_admin', password=password)

    (directory / 'herbal_localization_browser_settings.py').write_text(
        'from herbal_localization_test_settings import *\n'
        "ROOT_URLCONF = 'herbal_localization_browser_urls'\n", encoding='utf-8',
    )
    project_root = Path(os.environ['HERBAL_LOCALIZATION_PROJECT_ROOT'])
    (directory / 'herbal_localization_browser_urls.py').write_text(
        'from config.urls import urlpatterns\n'
        'from django.conf import settings\n'
        'from django.urls import re_path\n'
        'from django.views.static import serve\n'
        'urlpatterns = list(urlpatterns) + [\n'
        "    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),\n"
        f"    re_path(r'^(?P<path>.*)$', lambda request, path: serve(request, path or 'index.html', document_root={str(project_root / 'frontend')!r})),\n"
        ']\n', encoding='utf-8',
    )
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    environment = dict(os.environ, DJANGO_SETTINGS_MODULE='herbal_localization_browser_settings')
    output = directory / 'browser'
    output.mkdir()
    server_log = (directory / 'browser-server.log').open('w', encoding='utf-8')
    server = subprocess.Popen(
        [sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload'],
        cwd=project_root / 'backend', env=environment, stdout=server_log, stderr=server_log,
    )
    browser = None
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(origin + '/health/', timeout=1) as response:
                    if json.load(response)['status'] == 'ok':
                        break
            except (OSError, ValueError):
                if server.poll() is not None:
                    raise RuntimeError('Isolated Django browser server failed to start.')
                time.sleep(0.1)
        else:
            raise RuntimeError('Isolated Django browser server did not become ready.')
        with tempfile.TemporaryDirectory(prefix='herbal-localization-chrome-', dir=directory) as profile:
            browser = Browser('/opt/google/chrome/chrome', profile)
            run_browser(browser, origin, output, image_file, products, category, existing, admin_user, password)
            browser.close()
            browser = None
    except Exception:
        if browser is not None:
            browser.screenshot(output / 'failure.png')
        raise
    finally:
        if browser is not None:
            browser.close()
        server.terminate()
        server.wait(timeout=15)
        server_log.close()
        connection.close()
    print('PASS: actual Chrome integration; screenshots: ' + str(output), flush=True)


def run_browser(browser, origin, output, image_file, products, category, existing, admin_user, password):
    from django.contrib.auth import get_user_model
    from apps.catalog.models import Category, Product
    from apps.favorites.models import SavedProduct

    def passed(label):
        print('PASS: ' + label, flush=True)

    def page(path):
        browser.navigate(origin + path)

    def fill(selector, value):
        browser.evaluate('document.querySelector(' + json.dumps(selector) + ').value = ' + json.dumps(str(value)))

    def save_ready(saved):
        browser.wait('document.querySelector("[data-save-product]")?.disabled === false && document.querySelector("[data-save-product]").getAttribute("aria-pressed") === ' + json.dumps(str(saved).lower()))

    def language(code):
        browser.click(f'[data-language="{code}"]')
        browser.wait('document.documentElement.lang === ' + json.dumps(code) + ' && document.querySelector("[data-language=\\"' + code + '\\"]")?.getAttribute("aria-pressed") === "true"')

    def reload_page():
        browser.evaluate('window.__beforeLocalizationReload = true')
        browser.command('Page.reload', session=browser.session)
        browser.wait('!window.__beforeLocalizationReload && document.readyState === "complete" && document.querySelector("[data-language]")')

    def logout():
        browser.wait('document.querySelector("#logout-button")?.hidden === false')
        browser.click('#logout-button')
        browser.wait('document.querySelector("#logout-confirmation").open')
        assert browser.evaluate('document.querySelector("#logout-dialog-title").textContent === ' + json.dumps('Выход из аккаунта' if browser.evaluate('document.documentElement.lang') == 'ru' else 'Hisobdan chiqish'))
        browser.click('#logout-cancel')
        assert browser.evaluate('!document.querySelector("#logout-confirmation").open && !document.querySelector("#logout-button").hidden')
        browser.click('#logout-button')
        browser.click('#logout-confirm')
        browser.wait('location.pathname.endsWith("index.html") && document.querySelector(".category-card")')

    def auth_submit(username):
        fill('#username', username)
        fill('#password', password)
        browser.click('#auth-submit')
        browser.wait('location.pathname.endsWith("favorites.html") && document.querySelectorAll("[data-remove-product]").length === 1')

    def api(path):
        return browser.evaluate('fetch(' + json.dumps(path) + ').then(response => response.json())')

    def image_input():
        root = browser.command('DOM.getDocument', session=browser.session)['root']['nodeId']
        node = browser.command('DOM.querySelector', {'nodeId': root, 'selector': '#id_image'}, browser.session)['nodeId']
        browser.command('DOM.setFileInputFiles', {'nodeId': node, 'files': [str(image_file)]}, browser.session)

    page('/product.html?slug=' + products[0].slug)
    save_ready(False)
    assert browser.evaluate('document.documentElement.lang === "uz" && document.querySelector("#page-title").textContent === "Sinov mahsuloti 1"')
    default = api('/api/v1/products/' + products[0].slug + '/')
    assert 'language' not in default and default['name'] == 'Sinov mahsuloti 1'
    initial = api('/api/v1/products/' + products[0].slug + '/?lang=uz')
    language('ru')
    save_ready(False)
    assert browser.evaluate('document.querySelector("#page-title").textContent === "Тестовое название" && document.querySelector(".instruction-text").textContent.includes("Тестовые сведения")')
    russian = api('/api/v1/products/' + products[0].slug + '/?lang=ru')
    assert all(initial[field] == russian[field] for field in ('id', 'slug', 'price', 'image', 'is_available'))
    assert initial['language'] == 'uz' and russian['language'] == 'ru'
    browser.click('[data-save-product]')
    browser.wait('location.pathname.endsWith("register.html") && document.querySelector("#switch-auth")')
    intent = browser.evaluate('sessionStorage.getItem("herbalStore.pendingSave")')
    language('uz')
    assert browser.evaluate('sessionStorage.getItem("herbalStore.pendingSave")') == intent
    reload_page()
    assert browser.evaluate('sessionStorage.getItem("herbalStore.pendingSave")') == intent
    language('ru')
    browser.click('#switch-auth')
    browser.wait('location.pathname.endsWith("login.html") && document.querySelector("#auth-form")')
    browser.click('#auth-submit')
    browser.wait('document.querySelector("#username-error").textContent === "Введите имя пользователя."')
    auth_submit(existing.username)
    assert SavedProduct.objects.filter(user=existing, product=products[0]).count() == 1
    passed('real guest Save → UZ/RU switch/reload → login → single pending Save')

    page('/product.html?slug=' + products[0].slug)
    save_ready(True)
    language('uz')
    save_ready(True)
    reload_page()
    save_ready(True)
    assert browser.evaluate('document.querySelector("[data-save-product]").textContent.includes("Saqlangan")')
    language('ru')
    save_ready(True)
    assert browser.evaluate('document.querySelector("[data-save-product]").textContent.includes("Сохранено")')
    cookies = browser.command('Network.getCookies', {'urls': [origin + '/api/v1/auth/']}, browser.session)['cookies']
    assert any(cookie['name'] == 'refresh_token' and cookie['httpOnly'] for cookie in cookies)
    assert not browser.evaluate('document.cookie.includes("refresh_token=")')
    assert browser.evaluate('Object.keys(localStorage).every(key => key === "herbalStore.language") && !sessionStorage.getItem("herbalStore.pendingSave")')
    browser.click('[data-save-product]')
    save_ready(False)
    assert not SavedProduct.objects.filter(user=existing, product=products[0]).exists()
    browser.click('[data-save-product]')
    save_ready(True)
    passed('real bookmark toggle/reload/language persistence and HttpOnly/token-storage boundaries')

    page('/category.html?slug=' + category.slug)
    browser.wait('document.querySelectorAll(".product-card").length === 2')
    for code in ('uz', 'ru'):
        language(code)
        browser.wait('document.querySelectorAll(".product-card").length === 2')
        for width, columns in ((390, 2), (1024, 4), (1440, 5)):
            browser.command('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 1000, 'deviceScaleFactor': 1, 'mobile': width < 700}, browser.session)
            assert browser.evaluate('document.documentElement.scrollWidth <= innerWidth && getComputedStyle(document.querySelector(".product-grid")).gridTemplateColumns.split(" ").length === ' + str(columns))
            browser.screenshot(output / f'catalog-{code}-{width}.png')
    passed('actual UZ/RU responsive catalog at 390/1024/1440px')

    logout()
    page('/product.html?slug=' + products[1].slug)
    save_ready(False)
    assert browser.evaluate('document.querySelector("#page-title").textContent === "Перевод ещё не добавлен" && document.querySelector(".translation-notice") && !document.querySelector(".instruction-text") && !document.body.innerText.includes("Faqat dastur sinovi")')
    missing = api('/api/v1/products/' + products[1].slug + '/?lang=ru')
    assert missing['translation_available'] is False and missing['name'] is None and missing['detailed_information'] is None
    browser.click('[data-save-product]')
    browser.wait('location.pathname.endsWith("register.html") && document.querySelector("#auth-form")')
    reload_page()
    auth_submit('browser_registered')
    registered = get_user_model().objects.get(username='browser_registered')
    assert SavedProduct.objects.filter(user=registered, product=products[1]).count() == 1
    assert not SavedProduct.objects.filter(user=registered, product=products[0]).exists()
    assert browser.evaluate('document.documentElement.lang === "ru" && document.querySelector(".product-name").textContent.includes("Перевод ещё не добавлен")')
    browser.click('[data-remove-product]')
    browser.wait('!document.querySelector("[data-remove-product]") && document.body.innerText.includes("Сохраните первый товар")')
    assert not SavedProduct.objects.filter(user=registered).exists()
    passed('missing RU stays explicit; real guest registration → Save → localized Favorites/remove')

    browser.command('Page.navigate', {'url': origin + '/admin/'}, browser.session)
    browser.wait('document.querySelector("#id_username")')
    fill('#id_username', admin_user.username)
    fill('#id_password', password)
    browser.click('input[type="submit"]')
    browser.wait('location.pathname === "/admin/" && !document.querySelector("#id_password")')
    page('/admin/catalog/category/add/')
    fill('#id_name', 'Admin sinov toifasi')
    fill('#id_slug', 'browser-admin-category')
    fill('#id_ru_name', 'Тестовая категория администратора')
    browser.click('input[name="_save"]')
    browser.wait('location.pathname === "/admin/catalog/category/"')
    admin_category = Category.objects.get(slug='browser-admin-category')
    assert admin_category.translations.get(language='ru').name == 'Тестовая категория администратора'
    page(f'/admin/catalog/category/{admin_category.pk}/change/')
    fill('#id_ru_name', 'Тестовая категория после изменения')
    browser.click('input[name="_save"]')
    browser.wait('location.pathname === "/admin/catalog/category/"')
    assert admin_category.translations.get(language='ru').name == 'Тестовая категория после изменения'

    page('/admin/catalog/product/add/')
    for selector, value in (
        ('#id_category', admin_category.pk), ('#id_name', 'Admin sinov mahsuloti'),
        ('#id_slug', 'browser-admin-product'), ('#id_price', '12500.50'),
        ('#id_description', 'Sinov tavsifi.'), ('#id_detailed_information', 'Faqat dastur sinovi uchun.'),
        ('#id_ru_name', 'Тестовое название администратора'),
    ):
        fill(selector, value)
    assert browser.evaluate('document.body.innerText.includes("Umumiy ma’lumotlar") && document.body.innerText.includes("O‘zbekcha (UZ)") && document.body.innerText.includes("Ruscha (RU)")')
    image_input()
    browser.wait('document.querySelector("[data-image-preview] img").src.startsWith("blob:") && document.querySelector("[data-image-preview] img").naturalWidth > 0')
    browser.click('input[name="_save"]')
    browser.wait('document.querySelector(".errorlist") && document.querySelector("#id_ru_description")')
    assert not Product.objects.filter(slug='browser-admin-product').exists()
    fill('#id_ru_description', 'Тестовое описание администратора.')
    fill('#id_ru_detailed_information', 'Тестовые сведения администратора.')
    image_input()
    browser.click('input[name="_save"]')
    browser.wait('location.pathname === "/admin/catalog/product/"')
    admin_product = Product.objects.get(slug='browser-admin-product')
    original_id = admin_product.pk
    assert admin_product.translations.count() == 2
    page(f'/admin/catalog/product/{admin_product.pk}/change/')
    browser.wait('document.querySelector("[data-image-preview] img").naturalWidth > 0')
    fill('#id_name', 'Admin yangilangan sinov mahsuloti')
    fill('#id_ru_name', 'Тестовое название после изменения')
    fill('#id_price', '13000.50')
    browser.screenshot(output / 'admin-product-uz-ru.png')
    browser.click('input[name="_save"]')
    browser.wait('location.pathname === "/admin/catalog/product/"')
    admin_product.refresh_from_db()
    assert admin_product.pk == original_id and admin_product.translations.count() == 2
    assert admin_product.translations.get(language='uz').name == 'Admin yangilangan sinov mahsuloti'
    assert admin_product.translations.get(language='ru').name == 'Тестовое название после изменения'
    page(f'/admin/catalog/product/{admin_product.pk}/delete/')
    browser.click('input[type="submit"]')
    browser.wait('location.pathname === "/admin/catalog/product/"')
    assert not Product.objects.filter(pk=original_id).exists()
    page(f'/admin/catalog/category/{admin_category.pk}/delete/')
    browser.click('input[type="submit"]')
    browser.wait('location.pathname === "/admin/catalog/category/"')
    assert not Category.objects.filter(pk=admin_category.pk).exists()
    assert Product.objects.filter(pk__in=[product.pk for product in products]).count() == 2
    assert SavedProduct.objects.filter(user=existing, product=products[0]).count() == 1
    passed('native Admin UZ/RU category/product CRUD, partial RU rollback, one ID and live image preview')


if __name__ == '__main__':
    main()
