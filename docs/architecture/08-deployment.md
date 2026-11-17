# 08 — Docker, Nginx, PostgreSQL & AWS EC2 Deployment

## 1. Production topology

```text
Internet / DNS
    ↓ HTTPS 443
AWS EC2 Security Group
    ↓
Docker Compose
├── nginx
│   ├── static frontend build/files
│   ├── /static/ shared volume
│   ├── /media/ shared volume
│   └── reverse proxy /api/, /admin/, /health/
├── backend (Gunicorn + Django/DRF)
└── db (PostgreSQL)
```

MVPda Nginx, backend va PostgreSQL bitta EC2 instance ichida ishlaydi. Bu xarajat va boshqaruvni kamaytiradi, lekin single point of failure ekanligi hujjatlashtiriladi.

## 2. Docker image

- `backend/Dockerfile`: Django dependencies va app; non-root userdan ishga tushirish, production WSGI uchun Gunicorn.
- `deploy/nginx/Dockerfile`: Nginx base image, Nginx konfiguratsiyasi, frontend HTML/CSS/JS assetlari.
- PostgreSQL uchun rasmiy image va versiyasi aniq pin qilingan tag ishlatiladi.
- `latest` kabi suzuvchi taglarga productionda ko‘r-ko‘rona tayanilmaydi.

## 3. Compose fayllari

- `docker-compose.yml`: xizmatlarning umumiy bazaviy ta’rifi, network va persistent volume.
- `docker-compose.dev.yml`: lokal development override, kerak bo‘lsa source bind-mount va development command.
- `docker-compose.prod.yml`: production image/command, restart policy, ports, healthcheck va production sozlamalari.

Fayllar ketma-ket qo‘shilib ishlatiladi. `.env` Compose variable substitution uchun root'da bo‘ladi; `.env` Git'ga qo‘shilmaydi. `.env.example`da faqat placeholder/nomaqbul bo‘lmagan namuna qiymatlar.

## 4. Networks

- `app_network`: Nginx va backend.
- `db_network`: backend va database; `internal: true` qilish ko‘rib chiqiladi.
- PostgreSQL `ports` bilan public hostga publish qilinmaydi.
- Gunicorn porti ham tashqi internetga publish qilinmaydi; Nginx Docker service nomi bilan ulanadi.

## 5. Volumes

- `postgres_data`: PostgreSQL data directory.
- `media_data`: Django uploaded product images.
- `static_data`: `collectstatic` natijasi.

Backend va Nginx `media_data` va `static_data`ni mos read/write yoki read-only rejimda mount qiladi. Volume container o‘chirilishidan ma’lumotni saqlaydi, ammo server/disk yo‘qolishiga qarshi mustaqil backup o‘rnini bosa olmaydi.

## 6. Nginx routing

| Path | Yo‘nalish |
|---|---|
| `/` va `.html` sahifalar | Frontend statik fayllari |
| `/api/` | `backend:8000` |
| `/admin/` | `backend:8000` |
| `/static/` | `static_data` |
| `/media/` | `media_data` |
| `/health/` | Backend health endpointi yoki Nginx health route siyosati |

Nginx HTTPS terminatsiya qilsa, backendga `X-Forwarded-Proto` kabi kerakli headerlar to‘g‘ri uzatiladi. Django faqat ishonchli reverse proxy yuborgan headerlarga tayanadi.

## 7. Port/security group

- 22/SSH: faqat administratorning ishonchli IP manzilidan.
- 80/HTTP: redirect va sertifikat talablari uchun.
- 443/HTTPS: public traffic.
- 8000/Gunicorn: public emas.
- 5432/PostgreSQL: public emas.

## 8. Production setup

1. AWS akkauntida ayni vaqtdagi Free Tier/credit shartlarini tekshirish.
2. EC2 instance va Security Group yaratish.
3. SSH key bilan xavfsiz ulanish.
4. Docker Engine/Compose plugin o‘rnatish.
5. Git repository'ni clone qilish.
6. Serverda secret `.env` yaratish.
7. Production Compose bilan images build/pull va containers start.
8. DB readiness, migrations va `collectstatic`ni release jarayonida bajarish.
9. Django superuser yaratish.
10. Domen DNS A recordini EC2 public/static IP'ga yo‘naltirish.
11. TLS sertifikat va avtomatik yangilanishni sozlash (quyidagi ikki bosqichli Nginx bootstrapping qoidasi bo‘yicha).
12. Smoke test: public API, auth, Favorites, Admin, media, HTTPS.

## 9. HTTPS bootstrapping — implementatsiyaga tayyor qaror

Nginx birinchi marta sertifikatsiz ishga tushganda mavjud bo‘lmagan sertifikat path'iga murojaat qilib xatoga tushmasligi kerak. Shu sabab:

1. Dastlab HTTP-only Nginx konfiguratsiyasi bilan port 80 da sayt va `/.well-known/acme-challenge/` webroot ishlaydi.
2. Hostda Certbot webroot usuli bilan domen sertifikati olinadi. ACME webroot volume/host path Nginxga beriladi.
3. Sertifikat fayllari read-only mount qilinadi va production HTTPS Nginx konfiguratsiyasi yoqiladi.
4. Yangilanish job'i Certbot renew bajaradi; sertifikat yangilangach Nginxga reload yuboriladi.
5. HTTP → HTTPS redirect TLS to‘liq ishga tushgandan keyin yoqiladi; renewal tekshiruvlari to‘silib qolmasin.

Bu alohida Docker service qo‘shishni majbur qilmaydi: Certbot hostda yurishi mumkin. DNS, server IP va port 80/443 deploy vaqtida tekshiriladi.

## 10. Media va frontend freshness

API Catalog response'lariga dastlab `Cache-Control: no-store` qo‘yiladi. Browser Nginx orqali media URLga kiradi. Yangi Product rasmi yuklansa storage yangi nom/URL bergani uchun eski rasm cache'si narx yoki mavjudlik haqidagi ma’lumotlarni eski qilib ko‘rsatmasligi kerak. Static HTML cache siyosati yangi frontend deploydan keyin yangilanishni ta’minlasin.

## 11. EC2 xarajat xavfi

Free Tier eligibility akkaunt ochilgan sana, plan, instance turi, disk, public IPv4, trafik va boshqa shartlarga bog‘liq. Deploy paytida AWS billing/Free Tier sahifasi qayta tekshiriladi; doimiy ravishda “bepul” deb taxmin qilinmaydi.

## 12. Single-server limitation

Bu MVP uchun maqbul, lekin Nginx, Django va DB bir EC2 instance ichida bo‘lgani sababli instance to‘xtasa butun sayt ishlamay qoladi. Trafik yoki biznes SLA talabi oshsa, alohida managed database, object storage/CDN, monitoring va redundant deployment keyingi arxitektura qarori bo‘ladi.
