"""UZ/RU browser regressions using a static frontend and mocked API only.

Run a static server, then: python3 frontend/tests/localization_smoke.py --origin
http://127.0.0.1:8766. No database, accounts or catalog data are changed.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from browser_smoke import Browser, frontend_regression

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--origin', default='http://127.0.0.1:8766')
parser.add_argument('--chrome', default='/opt/google/chrome/chrome')
args = parser.parse_args()
origin = urlsplit(args.origin)
if origin.scheme != 'http' or origin.hostname not in {'localhost', '127.0.0.1'} or origin.username or origin.password or origin.path not in {'', '/'} or origin.query or origin.fragment:
    parser.error('Only a localhost HTTP origin is allowed.')
ORIGIN = args.origin.rstrip('/')
MOCK = r'''(() => {
  const response = (data, status = 200) => Promise.resolve(new Response(status === 204 ? null : JSON.stringify(data), {status, headers: {'Content-Type': 'application/json'}}));
  const category = (lang) => ({id: 1, slug: 'fixture-category', name: lang === 'ru' ? 'RU fixture #1' : 'UZ fixture #1', language: lang, translation_available: true});
  const product = (lang) => ({id: 7, slug: 'fixture-product', name: lang === 'ru' ? 'RU fixture #7' : 'UZ fixture #7', description: 'Fixture description', detailed_information: 'Fixture instructions', price: '35000.00', image: null, is_available: true, category: category(lang), language: lang, translation_available: true, saved_at: '2026-10-13T21:30:00Z'});
  const originalFetch = window.fetch;
  window.fetch = (path, options = {}) => {
    if (!String(path).startsWith('/api/')) return originalFetch(path, options);
    const url = new URL(path, location.origin);
    const lang = url.searchParams.get('lang') || 'uz';
    const auth = sessionStorage.getItem('fixture.auth') === 'true';
    const saved = sessionStorage.getItem('fixture.saved') === 'true';
    const method = options.method || 'GET';
    if (url.pathname.endsWith('/csrf/')) return response({csrfToken: 'fixture-csrf'});
    if (url.pathname.endsWith('/token/refresh/')) return response(auth ? {access: 'fixture-only-memory-access'} : {}, auth ? 200 : 401);
    if (url.pathname.endsWith('/token/') || url.pathname.endsWith('/register/')) {sessionStorage.setItem('fixture.auth', 'true'); return response({access: 'fixture-only-memory-access'});}
    if (url.pathname.endsWith('/logout/')) {sessionStorage.removeItem('fixture.auth'); return response(null, 204);}
    if (url.pathname === '/api/v1/categories/') return response([category(lang)]);
    if (url.pathname.startsWith('/api/v1/categories/')) return response({category: category(lang), products: [product(lang)]});
    if (url.pathname.startsWith('/api/v1/products/')) return response(product(lang));
    if (url.pathname.startsWith('/api/v1/me/saved-products/')) {
      if (!auth) return response({}, 401);
      if (method === 'GET') return response(saved ? [product(lang)] : []);
      if (method === 'POST') {sessionStorage.setItem('fixture.saved', 'true'); return response({product_id: 7}, saved ? 200 : 201);}
      sessionStorage.removeItem('fixture.saved'); return response(null, 204);
    }
    return response({}, 500);
  };
})()'''

with tempfile.TemporaryDirectory(prefix='herbal-i18n-browser-', ignore_cleanup_errors=True) as directory:
    browser = Browser(args.chrome, directory)
    try:
        frontend_regression(browser, ORIGIN)
        browser.command('Page.addScriptToEvaluateOnNewDocument', {'source': MOCK}, browser.session)
        browser.navigate(ORIGIN + '/product.html?slug=fixture-product')
        browser.wait('document.querySelector("[data-save-product]") && !document.querySelector("[data-save-product]").disabled')
        browser.click('[data-save-product]')
        browser.wait('location.pathname === "/register.html" && document.querySelector("#auth-form")')
        browser.click('[data-language="ru"]')
        browser.wait('document.documentElement.lang === "ru" && document.querySelector("#auth-form")')
        assert browser.evaluate('JSON.parse(sessionStorage.getItem("herbalStore.pendingSave")).productId === 7')
        browser.click('#switch-auth')
        browser.wait('location.pathname === "/login.html" && document.documentElement.lang === "ru" && document.querySelector("#auth-form")')
        browser.evaluate('document.querySelector("#username").value="fixture"; document.querySelector("#password").value="fixture-only-password"; document.querySelector("#auth-form").requestSubmit()')
        browser.wait('location.pathname === "/favorites.html" && document.querySelector("[data-product-id=\\"7\\"]")')
        assert browser.evaluate('sessionStorage.getItem("herbalStore.pendingSave") === null && document.querySelector(".product-name").textContent === "RU fixture #7"')
        browser.click('[data-language="uz"]')
        browser.wait('document.documentElement.lang === "uz" && document.querySelector("[data-product-id=\\"7\\"]")')
        assert browser.evaluate('document.querySelector(".product-name").textContent === "UZ fixture #7" && !document.querySelector("#logout-button").hidden')
        print('PASS: real language reload preserves Guest Save → RU Login → automatic Favorites and authenticated UZ reload', flush=True)
        browser.click('#logout-button')
        browser.click('#logout-confirm')
        browser.wait('location.pathname === "/index.html" && document.querySelector(".category-card")')
        browser.evaluate('sessionStorage.removeItem("fixture.saved")')
        browser.navigate(ORIGIN + '/product.html?slug=fixture-product')
        browser.wait('document.querySelector("[data-save-product]") && !document.querySelector("[data-save-product]").disabled')
        browser.click('[data-save-product]')
        browser.wait('location.pathname === "/register.html" && document.querySelector("#auth-form")')
        browser.click('[data-language="ru"]')
        browser.wait('document.documentElement.lang === "ru" && document.querySelector("#auth-form")')
        browser.evaluate('document.querySelector("#username").value="fixture-new"; document.querySelector("#password").value="fixture-only-password"; document.querySelector("#auth-form").requestSubmit()')
        browser.wait('location.pathname === "/favorites.html" && document.querySelector("[data-product-id=\\"7\\"]")')
        assert browser.evaluate('sessionStorage.getItem("herbalStore.pendingSave") === null && document.querySelector(".product-name").textContent === "RU fixture #7"')
        print('PASS: real language reload preserves Guest Save → RU Registration → automatic Favorites', flush=True)
        checks = 0
        for language in ['uz', 'ru']:
            browser.evaluate('localStorage.setItem("herbalStore.language", ' + json.dumps(language) + ')')
            for width in [280, 360, 393, 480, 500, 600, 700, 768, 1000, 1400, 1600]:
                browser.command('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False}, browser.session)
                for page in ['category.html?slug=fixture-category', 'favorites.html']:
                    browser.navigate(ORIGIN + '/' + page)
                    browser.wait('document.querySelector("#page-content[aria-busy=false]") && document.querySelector(".product-card")')
                    state = browser.evaluate('''(() => ({
                      overflow: document.documentElement.scrollWidth > innerWidth,
                      columns: getComputedStyle(document.querySelector('.product-grid')).gridTemplateColumns.split(' ').length,
                      badButtons: [...document.querySelectorAll('.product-card .details-button, .product-card .save-button')].some(b => b.scrollWidth > b.clientWidth + 1 || b.getBoundingClientRect().height < 44),
                      width: innerWidth,
                    }))()''')
                    expected = 2 if width < 700 else 3 if width < 1000 else 4 if width < 1400 else 5
                    assert not state['overflow'] and not state['badButtons'] and state['columns'] == expected, (language, page, width, state)
                    checks += 1
        print('PASS: UZ/RU category/Favorites responsive checks at 280–1600px (' + str(checks) + ' scenarios)', flush=True)
    except Exception:
        print(browser.evaluate('({url: location.href, lang: document.documentElement.lang, text: document.body.innerText.slice(-2000)})'), flush=True)
        raise
    finally:
        browser.close()
