"""Real Chrome bilan lokal MVP user flow sinovi; tashqi Python paketlari yo‘q.

Faqat localhost va yangi vaqtinchalik Chrome profili ishlatiladi. Sinov yangi
demo foydalanuvchi yaratadi; parol va tokenlar terminalga chiqarilmaydi.
"""

import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import select
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request


class Browser:
    def __init__(self, executable, directory):
        incoming_read, self.incoming_write = os.pipe()
        self.outgoing_read, outgoing_write = os.pipe()

        def configure_pipes():
            os.dup2(incoming_read, 3)
            os.dup2(outgoing_write, 4)
            os.set_inheritable(3, True)
            os.set_inheritable(4, True)

        self.process = subprocess.Popen(
            [executable, '--headless', '--disable-gpu', '--no-first-run',
             '--no-default-browser-check', '--remote-debugging-pipe',
             '--user-data-dir=' + directory, 'about:blank'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, close_fds=False, preexec_fn=configure_pipes,
        )
        os.close(incoming_read)
        os.close(outgoing_write)
        self.counter = 0
        self.buffer = b''
        target = self.command('Target.createTarget', {'url': 'about:blank'})['targetId']
        self.session = self.command('Target.attachToTarget', {
            'targetId': target, 'flatten': True,
        })['sessionId']
        self.command('Page.enable', session=self.session)
        self.command('Runtime.enable', session=self.session)

    def command(self, method, params=None, session=None):
        self.counter += 1
        identifier = self.counter
        message = {'id': identifier, 'method': method, 'params': params or {}}
        if session:
            message['sessionId'] = session
        os.write(self.incoming_write, json.dumps(message).encode() + b'\0')
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if b'\0' not in self.buffer:
                ready, _, _ = select.select([self.outgoing_read], [], [], 1)
                if not ready:
                    continue
                chunk = os.read(self.outgoing_read, 65536)
                if not chunk:
                    raise RuntimeError('Chrome DevTools pipe yopildi.')
                self.buffer += chunk
            while b'\0' in self.buffer:
                data, self.buffer = self.buffer.split(b'\0', 1)
                response = json.loads(data)
                if response.get('id') == identifier:
                    if 'error' in response:
                        raise RuntimeError(response['error']['message'])
                    return response.get('result', {})
        raise TimeoutError('Chrome DevTools javobi kutilmoqda: ' + method)

    def evaluate(self, expression):
        result = self.command('Runtime.evaluate', {
            'expression': expression, 'returnByValue': True, 'awaitPromise': True,
        }, self.session)
        if 'exceptionDetails' in result:
            raise RuntimeError('Brauzer JavaScript bajarilishi xato berdi.')
        return result.get('result', {}).get('value')

    def wait(self, expression, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if self.evaluate('Boolean(' + expression + ')'):
                    return
            except RuntimeError:
                pass
            time.sleep(0.1)
        raise AssertionError('Brauzerda kutilgan holat topilmadi: ' + expression)

    def navigate(self, url):
        self.command('Page.navigate', {'url': url}, self.session)
        self.wait('document.readyState === "complete" && location.href === ' + json.dumps(url))

    def click(self, selector):
        self.evaluate('document.querySelector(' + json.dumps(selector) + ').click()')

    def key(self, key, code, virtual_key, modifiers=0):
        parameters = {'key': key, 'code': code, 'windowsVirtualKeyCode': virtual_key, 'modifiers': modifiers}
        self.command('Input.dispatchKeyEvent', {'type': 'keyDown', **parameters}, self.session)
        self.command('Input.dispatchKeyEvent', {'type': 'keyUp', **parameters}, self.session)

    def screenshot(self, path):
        result = self.command('Page.captureScreenshot', {'format': 'png'}, self.session)
        Path(path).write_bytes(base64.b64decode(result['data']))

    def close(self):
        try:
            self.command('Browser.close')
        except (RuntimeError, BrokenPipeError):
            pass
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=10)
        os.close(self.incoming_write)
        os.close(self.outgoing_read)


def frontend_regression(browser, origin):
    browser.command('Emulation.setTimezoneOverride', {'timezoneId': 'UTC'}, browser.session)
    browser.navigate(origin + '/tests/index.html')
    browser.wait('["passed", "failed"].includes(document.querySelector("#test-results")?.dataset.status)', timeout=45)
    assert browser.evaluate('document.querySelector("#test-results").dataset.status === "passed"'), browser.evaluate('document.querySelector("#test-results").textContent')
    count = browser.evaluate('Number(document.querySelector("#test-results").dataset.passed)')
    assert count >= 31
    print('PASS: frontend auth/intent/UI regression harness (' + str(count) + ' tekshiruv)', flush=True)


def run(browser, origin, output):
    def page(path):
        browser.navigate(origin + path)

    def result(label):
        print('PASS: ' + label, flush=True)

    def viewport(mobile=False, width=None):
        browser.command('Emulation.setDeviceMetricsOverride', {
            'width': width if width is not None else 390 if mobile else 1440,
            'height': 844 if mobile else 1000,
            'deviceScaleFactor': 1, 'mobile': mobile,
        }, browser.session)

    def save_ready(saved=None):
        state = '' if saved is None else ' && button.getAttribute("aria-pressed") === ' + json.dumps(str(saved).lower())
        browser.wait('(() => { const button = document.querySelector("[data-save-product]"); return button && !button.disabled' + state + '; })()')

    def layout(label, screenshot):
        assert browser.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert browser.evaluate('Array.from(document.querySelectorAll(".product-visual img")).every(image => getComputedStyle(image).objectFit === "contain")')
        browser.screenshot(output / screenshot)
        result(label)

    def responsive_cards(label):
        # DOM nusxalari yetarli ustun va uzun matnni tekshiradi; API/DB o‘zgarmaydi.
        browser.evaluate('''(() => {
            const grid = document.querySelector('.product-grid');
            const template = grid.querySelector('.product-card');
            for (let index = 0; index < 6; index += 1) {
                const card = template.cloneNode(true);
                card.dataset.smokeClone = 'true';
                if (index === 0) {
                    card.querySelector('.product-name a').textContent =
                        'Dorivor giyohlardan tayyorlangan maxsus aralashma ' +
                        'JudaUzunMahsulotNomiUzluksizYozilgandaHamSig‘ishiKerak';
                    const save = card.querySelector('[data-save-product]');
                    if (save) {
                        save.setAttribute('aria-pressed', 'true');
                        save.querySelector('span').textContent = 'Saqlangan';
                    }
                }
                grid.append(card);
            }
        })()''')
        try:
            for width, columns in ((280, 2), (320, 2), (390, 2), (768, 3), (1024, 4), (1440, 5), (1600, 5)):
                viewport(width < 700, width)
                checks = browser.evaluate('''(() => {
                    const close = (left, right) => Math.abs(left - right) <= 2;
                    const fits = (node) => node.scrollWidth <= node.clientWidth + 1;
                    const grid = document.querySelector('.product-grid');
                    const cards = Array.from(grid.querySelectorAll('.product-card'));
                    return {
                        columns: getComputedStyle(grid).gridTemplateColumns.split(' ').length,
                        firstRow: cards.filter(card => close(card.getBoundingClientRect().top, cards[0].getBoundingClientRect().top)).length,
                        noOverflow: document.documentElement.scrollWidth <= innerWidth,
                        cards: cards.every(card => {
                            const visual = card.querySelector('.product-visual');
                            const content = card.querySelector('.product-card-content');
                            const title = card.querySelector('.product-name');
                            const availability = card.querySelector('.availability');
                            const price = card.querySelector('.price');
                            const footer = card.querySelector('.product-card-footer');
                            const [details, action] = footer.children;
                            const box = card.getBoundingClientRect();
                            const imageBox = visual.getBoundingClientRect();
                            const infoBox = content.getBoundingClientRect();
                            const detailsBox = details.getBoundingClientRect();
                            const actionBox = action.getBoundingClientRect();
                            const footerBox = footer.getBoundingClientRect();
                            const ordered = imageBox.bottom <= infoBox.top + 1 &&
                                title.getBoundingClientRect().bottom <= availability.getBoundingClientRect().top + 1 &&
                                availability.getBoundingClientRect().bottom <= price.getBoundingClientRect().top + 1 &&
                                price.getBoundingClientRect().bottom <= detailsBox.top + 1;
                            const buttons = [details, action].every(button => {
                                const buttonBox = button.getBoundingClientRect();
                                return buttonBox.height >= 44 && fits(button) &&
                                    getComputedStyle(button).borderRadius === '12px' &&
                                    close(buttonBox.left + buttonBox.width / 2, footerBox.left + footerBox.width / 2);
                            });
                            const images = Array.from(visual.querySelectorAll('img')).every(image => getComputedStyle(image).objectFit === 'contain');
                            return ordered && buttons && images && fits(card) && fits(title) && fits(availability) &&
                                title.scrollHeight <= title.clientHeight + 1 &&
                                actionBox.top >= detailsBox.bottom &&
                                close(detailsBox.width, actionBox.width) &&
                                close(imageBox.left, box.left + 1) && close(imageBox.width, box.width - 2);
                        }),
                    };
                })()''')
                assert checks == {'columns': columns, 'firstRow': columns, 'noOverflow': True, 'cards': True}, f'{label} {width}px: {checks}'
                result(f'{label} {width}px: {columns} ustun, vertikal kartalar, uzun matn va 44px tugmalar, overflow yo‘q')
        finally:
            browser.evaluate('document.querySelectorAll("[data-smoke-clone]").forEach(card => card.remove())')
            viewport()

    def confirm_logout(check_cancel=False):
        browser.wait('!document.querySelector("#logout-button").hidden')
        if check_cancel:
            browser.evaluate('''(() => {
                window.__herbalSmokeLogoutRequests = 0;
                const fetch = window.fetch;
                window.fetch = (...args) => {
                    if (new URL(args[0], location.href).pathname === '/api/v1/auth/logout/') {
                        window.__herbalSmokeLogoutRequests += 1;
                    }
                    return fetch(...args);
                };
            })()''')
            browser.click('#logout-button')
            browser.wait('document.querySelector("#logout-confirmation").open && document.activeElement.id === "logout-cancel"')
            assert browser.evaluate('document.querySelector("#logout-dialog-title").textContent === "Hisobdan chiqish" && document.querySelector("#logout-dialog-description").textContent === "Hisobingizdan haqiqatan ham chiqmoqchimisiz?"')
            browser.screenshot(output / 'logout-desktop.png')
            browser.key('Tab', 'Tab', 9)
            browser.wait('document.activeElement.id === "logout-confirm"')
            browser.key('Tab', 'Tab', 9, modifiers=8)
            browser.wait('document.activeElement.id === "logout-cancel"')
            browser.key('Escape', 'Escape', 27)
            browser.wait('!document.querySelector("#logout-confirmation").open && document.activeElement.id === "logout-button"')
            browser.click('#logout-button')
            browser.click('#logout-cancel')
            browser.wait('!document.querySelector("#logout-confirmation").open && document.activeElement.id === "logout-button"')
            assert browser.evaluate('window.__herbalSmokeLogoutRequests === 0 && !document.querySelector("#logout-button").hidden && document.querySelector("#nav-auth-link").hidden')
            result('logout desktop: dastlabki focus, Tab/Shift+Tab, Escape va Bekor sessiyani saqlaydi, logout so‘rovi yo‘q')
            viewport(True)
            browser.click('#logout-button')
            browser.wait('document.querySelector("#logout-confirmation").open')
            assert browser.evaluate('''(() => {
                const dialog = document.querySelector('#logout-confirmation');
                const box = dialog.getBoundingClientRect();
                return document.documentElement.scrollWidth <= innerWidth && box.left >= 0 && box.right <= innerWidth &&
                    Array.from(dialog.querySelectorAll('button')).every(button => button.getBoundingClientRect().height >= 44 && button.scrollWidth <= button.clientWidth);
            })()''')
            browser.screenshot(output / 'logout-mobile.png')
            browser.click('#logout-cancel')
            browser.wait('!document.querySelector("#logout-confirmation").open')
            assert browser.evaluate('window.__herbalSmokeLogoutRequests === 0 && !document.querySelector("#logout-button").hidden')
            result('logout 390px mobile: dialog/tugmalar sig‘adi, Bekor sessiyani saqlaydi')
        browser.click('#logout-button')
        browser.wait('document.querySelector("#logout-confirmation").open')
        browser.click('#logout-confirm')
        browser.wait('location.pathname.endsWith("index.html") && document.querySelectorAll(".category-card").length >= 3')
        result('logout Ha, chiqish mavjud logout oqimini bajaradi')
        viewport()

    def password_visibility():
        assert browser.evaluate('document.querySelector("#password-toggle").type === "button"')
        browser.click('#password-toggle')
        assert browser.evaluate('document.querySelector("#password").type === "text" && document.querySelector("#password-toggle").getAttribute("aria-pressed") === "true"')
        browser.click('#password-toggle')
        assert browser.evaluate('document.querySelector("#password").type === "password" && document.querySelector("#password-toggle").getAttribute("aria-pressed") === "false"')

    browser.command('Emulation.setTimezoneOverride', {'timezoneId': 'UTC'}, browser.session)
    viewport()
    page('/')
    browser.wait('document.querySelectorAll(".category-card").length >= 3')
    assert not browser.evaluate('Boolean(document.querySelector("[data-back]"))')
    result('public kategoriyalar va bosh sahifa')
    browser.screenshot(output / 'home-desktop.png')
    category = browser.evaluate('document.querySelector(".category-card").getAttribute("href")')
    page(category)
    browser.wait('document.querySelectorAll(".product-card").length > 0')
    save_ready(False)
    assert browser.evaluate('Array.from(document.querySelectorAll(".product-card")).every(card => Array.from(card.querySelectorAll("a")).some(link => link.textContent.trim() === "Batafsil"))')
    product = browser.evaluate('Array.from(document.querySelector(".product-card").querySelectorAll("a")).find(link => link.textContent.trim() === "Batafsil").getAttribute("href")')
    layout('kategoriya kartalari, alohida Batafsil va contain rasmlar', 'category-desktop.png')
    responsive_cards('katalog')
    page(product)
    save_ready(False)
    product_id = browser.evaluate('document.querySelector("[data-save-product]").dataset.saveProduct')
    assert browser.evaluate('document.querySelector("#product-back").getAttribute("href") === ' + json.dumps(category))
    assert browser.evaluate('Array.from(document.images).every(image => image.complete && image.naturalWidth > 0)')
    assert browser.evaluate('document.body.innerText.includes("namuna")')
    result('category → product detail va rasm')
    browser.screenshot(output / 'desktop.png')

    username = 'browser_' + secrets.token_hex(5)
    password = secrets.token_urlsafe(24)
    browser.click('[data-save-product]')
    browser.wait('location.pathname.endsWith("register.html") && document.querySelector("#auth-form")')
    browser.evaluate('document.querySelector("#username").value=' + json.dumps(username))
    browser.evaluate('document.querySelector("#password").value=' + json.dumps(password))
    password_visibility()
    assert browser.evaluate('document.querySelector("#password").value === ' + json.dumps(password))
    browser.click('#auth-submit')
    browser.wait('location.pathname.endsWith("favorites.html") && document.querySelectorAll("[data-remove-product]").length === 1')
    result('guest Save → register → avtomatik saqlash')
    assert browser.evaluate('Array.from(document.querySelectorAll(".saved-date")).every(node => /^Saqlangan: \\d{2}\\.\\d{2}\\.\\d{4}$/.test(node.textContent.trim()))')
    layout('saqlanganlar desktop kartalari va sana', 'favorites-desktop.png')
    responsive_cards('saqlanganlar')
    viewport(True)
    layout('saqlanganlar 390px mobile kartalari', 'favorites-mobile.png')
    viewport()
    assert browser.evaluate('!document.cookie.includes("refresh_token")')
    assert browser.evaluate('Object.keys(sessionStorage).every(k => !/token|access|refresh/i.test(k))')
    assert browser.evaluate('localStorage.length === 0')
    result('HttpOnly refresh va token storage chegaralari')
    browser.click('[data-remove-product]')
    browser.wait('document.querySelectorAll("[data-remove-product]").length === 0')
    result('favoritesdan o‘chirish va empty state')

    page(product)
    save_ready(False)
    browser.click('[data-save-product]')
    save_ready(True)
    assert browser.evaluate('location.pathname.endsWith("product.html")')
    result('yangi sahifada silent refresh → Save')
    page(product)
    save_ready(True)
    assert browser.evaluate('document.querySelector("[data-save-product]").textContent.trim() === "Saqlangan"')
    assert browser.evaluate('document.querySelector("[data-save-product] path").getAttribute("d") === "M6 4h12v17l-6-4-6 4Z"')
    result('reload haqiqiy Saqlangan holatini va bookmark ikonkasini tiklaydi')
    browser.command('Network.enable', session=browser.session)
    browser.command('Network.setBlockedURLs', {'urls': ['*/api/v1/me/saved-products/*']}, browser.session)
    browser.click('[data-save-product]')
    browser.wait('!document.querySelector("[data-save-product]").disabled && document.querySelector("#notice").classList.contains("is-error") && !document.querySelector("#notice").hidden')
    assert browser.evaluate('document.querySelector("[data-save-product]").getAttribute("aria-pressed") === "true" && document.querySelector("[data-save-product]").textContent.trim() === "Saqlangan"')
    browser.command('Network.setBlockedURLs', {'urls': []}, browser.session)
    browser.click('[data-save-product]')
    save_ready(False)
    browser.command('Network.setBlockedURLs', {'urls': ['*/api/v1/me/saved-products/*']}, browser.session)
    browser.click('[data-save-product]')
    browser.wait('!document.querySelector("[data-save-product]").disabled && document.querySelector("#notice").classList.contains("is-error") && !document.querySelector("#notice").hidden')
    assert browser.evaluate('document.querySelector("[data-save-product]").getAttribute("aria-pressed") === "false" && document.querySelector("[data-save-product]").textContent.trim() === "Saqlash"')
    browser.command('Network.setBlockedURLs', {'urls': []}, browser.session)
    browser.click('[data-save-product]')
    save_ready(True)
    result('Save ↔ Saved toggle, POST/DELETE network xatolari va qayta urinish')
    page(category)
    browser.wait('document.querySelector(' + json.dumps('[data-save-product="' + product_id + '"]') + ')?.getAttribute("aria-pressed") === "true"')
    result('kategoriya sahifasida ham haqiqiy favorites holati')
    confirm_logout(check_cancel=True)
    page(product)
    save_ready(False)
    browser.click('[data-save-product]')
    browser.wait('location.pathname.endsWith("register.html") && document.querySelector("#switch-auth")')
    browser.click('#switch-auth')
    browser.wait('location.pathname.endsWith("login.html") && document.querySelector("#auth-form")')
    browser.evaluate('document.querySelector("#username").value=' + json.dumps(username))
    browser.evaluate('document.querySelector("#password").value=' + json.dumps(password))
    password_visibility()
    browser.click('#auth-submit')
    browser.wait('location.pathname.endsWith("favorites.html") && document.querySelectorAll("[data-remove-product]").length === 1')
    result('logout → guest Save → login → idempotent avtomatik Save')
    page(product)
    save_ready(True)
    result('qayta login qilinganda detail Saqlangan holatini tiklaydi')

    confirm_logout()
    page(product)
    save_ready(False)
    browser.click('[data-save-product]')
    browser.wait('location.pathname.endsWith("register.html") && document.querySelector("#auth-form")')
    browser.evaluate('window.__herbalSmokeReload = true')
    browser.command('Page.reload', session=browser.session)
    browser.wait('!window.__herbalSmokeReload && document.readyState === "complete" && document.querySelector("#auth-form")')
    assert browser.evaluate('sessionStorage.getItem("herbalStore.pendingSave") !== null')
    result('auth reload pending Save ni saqlaydi')
    browser.click('#auth-submit')
    browser.wait('document.querySelector("#username").getAttribute("aria-invalid") === "true"')
    assert browser.evaluate('sessionStorage.getItem("herbalStore.pendingSave") !== null')
    browser.click('#cancel-auth')
    browser.wait('location.pathname.endsWith("product.html") && document.querySelector("[data-save-product]")')
    assert browser.evaluate('sessionStorage.getItem("herbalStore.pendingSave") === null')
    result('auth validation intentni saqlaydi, Bekor uni tozalaydi')
    browser.click('[data-save-product]')
    browser.wait('location.pathname.endsWith("register.html") && document.querySelector("#auth-form")')
    history = browser.command('Page.getNavigationHistory', session=browser.session)
    browser.command('Page.navigateToHistoryEntry', {
        'entryId': history['entries'][history['currentIndex'] - 1]['id'],
    }, browser.session)
    browser.wait('location.pathname.endsWith("product.html") && document.querySelector("[data-save-product]")')
    assert browser.evaluate('sessionStorage.getItem("herbalStore.pendingSave") === null')
    result('browser Back va pending Save cancel')

    browser.command('Page.navigate', {'url': origin + '/favorites.html'}, browser.session)
    browser.wait('location.pathname.endsWith("login.html") && document.querySelector("#auth-form")')
    result('guest favorites protected sahifasi login ochadi')

    browser.command('Network.enable', session=browser.session)
    browser.command('Network.setBlockedURLs', {'urls': ['*/api/v1/categories/*']}, browser.session)
    page('/')
    browser.wait('document.querySelector("#page-content .state.error button")')
    browser.command('Network.setBlockedURLs', {'urls': []}, browser.session)
    browser.click('#page-content .state.error button')
    browser.wait('document.querySelectorAll(".category-card").length >= 3')
    result('network xato va Qayta urinish orqali recovery')

    viewport(True)
    page('/')
    browser.wait('document.querySelectorAll(".category-card").length >= 3')
    assert browser.evaluate('document.documentElement.scrollWidth <= innerWidth')
    browser.screenshot(output / 'mobile.png')
    result('390px mobile layout (horizontal scroll yo‘q)')
    page(category)
    save_ready(False)
    layout('kategoriya 390px mobile kartalari', 'category-mobile.png')
    page(product)
    save_ready(False)
    layout('detail 390px mobile layout', 'product-mobile.png')
    page('/register.html')
    browser.wait('document.querySelector("#password-toggle")')
    layout('registration 390px mobile layout', 'register-mobile.png')
    page('/login.html')
    browser.wait('document.querySelector("#password-toggle")')
    layout('login 390px mobile layout', 'login-mobile.png')

    frontend_regression(browser, origin)

    credentials_path = Path(__file__).resolve().parent.parent / '.secrets' / 'dev-admin.json'
    if credentials_path.exists():
        viewport()
        credentials = json.loads(credentials_path.read_text())
        browser.command('Page.navigate', {'url': origin + '/admin/'}, browser.session)
        browser.wait('Boolean(document.querySelector("#id_username"))')
        browser.evaluate('document.querySelector("#id_username").value=' + json.dumps(credentials['username']))
        browser.evaluate('document.querySelector("#id_password").value=' + json.dumps(credentials['password']))
        browser.click('input[type="submit"]')
        browser.wait('location.pathname === "/admin/" && !document.querySelector("#id_password")')
        page('/admin/catalog/product/')
        browser.wait('Boolean(document.querySelector("#result_list"))')
        result('haqiqiy Django Admin login va katalog boshqaruvi')
        page('/admin/catalog/product/' + product_id + '/change/')
        browser.wait('document.querySelector("[data-image-preview] img[data-current-image]")?.complete')
        assert browser.evaluate('document.querySelector("[data-image-preview] img").naturalWidth > 0')
        browser.screenshot(output / 'admin-product-desktop.png')
        browser.evaluate('''(async () => {
            const canvas = document.createElement('canvas');
            canvas.width = 12; canvas.height = 8;
            canvas.getContext('2d').fillRect(0, 0, 12, 8);
            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
            const transfer = new DataTransfer();
            transfer.items.add(new File([blob], 'ui-preview.png', {type: 'image/png'}));
            const input = document.querySelector('#id_image');
            input.files = transfer.files;
            input.dispatchEvent(new Event('change', {bubbles: true}));
        })()''')
        browser.wait('(() => { const image = document.querySelector("[data-image-preview] img"); return image.src.startsWith("blob:") && !image.hidden && image.complete && image.naturalWidth === 12; })()')
        browser.evaluate('''(() => {
            const input = document.querySelector('#id_image');
            input.files = new DataTransfer().files;
            input.dispatchEvent(new Event('change', {bubbles: true}));
        })()''')
        browser.wait('(() => { const image = document.querySelector("[data-image-preview] img"); return !image.hidden && image.getAttribute("src") === image.dataset.currentImage; })()')
        result('Django Admin mavjud/yangi rasm preview va tanlovni bekor qilish (formasiz saqlashsiz)')
        page('/admin/catalog/product/add/')
        browser.wait('document.querySelector("[data-image-preview] img")?.hidden')
        result('Django Admin yangi mahsulot uchun bo‘sh preview')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--origin', default='http://127.0.0.1:8080')
    parser.add_argument('--chrome', default='/opt/google/chrome/chrome')
    parser.add_argument('--output', default='/tmp/herbal-store-browser')
    parser.add_argument('--regression-only', action='store_true', help='Faqat mock API regressionlari; yangi hisob yoki katalog yozuvi yaratilmaydi.')
    args = parser.parse_args()
    parsed = urllib.parse.urlsplit(args.origin)
    if parsed.hostname not in {'localhost', '127.0.0.1'} or parsed.scheme != 'http':
        parser.error('Faqat lokal HTTP Herbal Store origin ishlatiladi.')
    with urllib.request.urlopen(args.origin + '/health/', timeout=5) as response:
        assert json.load(response)['status'] == 'ok'
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='herbal-store-chrome-', ignore_cleanup_errors=True) as directory:
        browser = Browser(args.chrome, directory)
        try:
            if args.regression_only:
                frontend_regression(browser, args.origin)
            else:
                run(browser, args.origin, output)
        except Exception:
            print('Browser holati:', browser.evaluate('({path: location.pathname, title: document.title, notice: document.querySelector("#notice")?.textContent, form: document.querySelector("#form-message")?.textContent})'))
            browser.screenshot(output / 'failure.png')
            raise
        finally:
            browser.close()
    print('Browser smoke PASS; screenshots: ' + str(output))


if __name__ == '__main__':
    main()
