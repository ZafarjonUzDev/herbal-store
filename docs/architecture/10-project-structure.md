# 10 — Project Structure

```text
herbal_store/
├── .gitignore
├── .env.example
├── README.md
├── AGENTS.md
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── deploy/
│   └── nginx/
│       ├── Dockerfile
│       ├── nginx.conf
│       └── conf.d/
│           └── default.conf
├── docs/
│   ├── architecture/
│   └── decisions/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   └── apps/
│       ├── __init__.py
│       ├── accounts/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── views.py
│       │   ├── urls.py
│       │   ├── migrations/
│       │   └── tests/
│       ├── catalog/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── views.py
│       │   ├── urls.py
│       │   ├── migrations/
│       │   └── tests/
│       └── favorites/
│           ├── __init__.py
│           ├── admin.py
│           ├── apps.py
│           ├── models.py
│           ├── serializers.py
│           ├── views.py
│           ├── urls.py
│           ├── migrations/
│           └── tests/
└── frontend/
    ├── index.html
    ├── category.html
    ├── product.html
    ├── favorites.html
    ├── login.html
    ├── register.html
    ├── css/
    │   └── main.css
    ├── js/
    │   ├── api.js
    │   ├── auth.js
    │   ├── navigation.js
    │   ├── components/
    │   │   ├── navbar.js
    │   │   ├── category-card.js
    │   │   ├── product-card.js
    │   │   └── favorite-button.js
    │   ├── pages/
    │   │   ├── home.js
    │   │   ├── category.js
    │   │   ├── product.js
    │   │   ├── favorites.js
    │   │   ├── login.js
    │   │   └── register.js
    │   └── utils/
    │       ├── format-price.js
    │       └── notifications.js
    └── assets/
        ├── images/
        └── icons/
```

## Tuzilish haqidagi izohlar

Hujjatlar tarkibida `12-consistency-review.md` va `ADR-007`/`ADR-008`/`ADR-009` fayllari ham bor; ular `docs/architecture` va `docs/decisions` papkalariga joylanadi.

- `.env.example` root'da, chunki Compose umumiy environment qiymatlarini shu yerda hujjatlashtiradi. Real `.env` commit qilinmaydi.
- Frontend uchun alohida Dockerfile yo‘q: frontend assetlari `deploy/nginx/Dockerfile` orqali Nginx image ichiga qo‘shiladi.
- Backenddagi `apps/` Python package bo‘lishi uchun `__init__.py` saqlanadi. `apps` konfiguratsiyasida `AppConfig.name` to‘g‘ri ko‘rsatiladi.
- `tests/` ichidagi `__init__.py` va test fayllari implementatsiya paytida yaratiladi.
- Papkalar blueprint; ularni barcha fayl bilan birdan yaratish shart emas. Bosqichma-bosqich zarur fayllar yaratiladi.
