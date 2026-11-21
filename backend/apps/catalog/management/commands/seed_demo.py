"""Lokal katalogni aniq belgilangan, neytral demo yozuvlari bilan to‘ldirish."""

from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont

from apps.catalog.models import Category, Product


DEMO_CATEGORIES = (
    ('demo-giyohlar', 'Giyohlar — namuna', (225, 235, 222)),
    ('demo-choylar', 'Choylar — namuna', (235, 231, 213)),
    ('demo-tabiiy-mahsulotlar', 'Tabiiy mahsulotlar — namuna', (242, 224, 203)),
)
DEMO_PRODUCTS = (
    ('demo-moychechak', 'Moychechak — namuna', 'demo-giyohlar', '35000.00', True),
    ('demo-yalpiz', 'Yalpiz — namuna', 'demo-giyohlar', '30000.00', True),
    ('demo-limon-oti', 'Limon o‘ti — namuna', 'demo-choylar', '45000.00', False),
    ('demo-namatak', 'Na’matak — namuna', 'demo-choylar', '50000.00', True),
    ('demo-asal', 'Asal — namuna', 'demo-tabiiy-mahsulotlar', '90000.00', True),
    ('demo-qora-sedana', 'Qora sedana — namuna', 'demo-tabiiy-mahsulotlar', '40000.00', True),
)


def demo_image(color):
    image = Image.new('RGB', (900, 675), color)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((255, 100, 645, 575), radius=36, fill=(252, 251, 246))
    draw.line((305, 245, 595, 245), fill=(178, 190, 172), width=3)
    draw.text(
        (450, 200), 'HERBAL STORE', fill=(72, 94, 69),
        font=ImageFont.load_default(size=26), anchor='mm',
    )
    draw.text(
        (450, 340), 'DEMO', fill=(72, 94, 69),
        font=ImageFont.load_default(size=64), anchor='mm',
    )
    draw.text(
        (450, 430), 'NAMUNA', fill=(108, 123, 99),
        font=ImageFont.load_default(size=25), anchor='mm',
    )
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


class Command(BaseCommand):
    help = 'DEBUG=True lokal muhit uchun 3 kategoriya va 6 demo mahsulot yaratadi.'
    
    def add_arguments(self, parser): 
        parser.add_argument(
            '--allow-prod',
            action='store_true',
            help='DEBUG=False muhitida ham demo katalog yaratishga ruxsat berish.',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed_demo faqat DEBUG=True bo‘lgan lokal muhitda ishlaydi.')

        categories = {}
        colors = {}
        created_categories = 0
        created_products = 0
        with transaction.atomic():
            for slug, name, color in DEMO_CATEGORIES:
                category, created = Category.objects.get_or_create(slug=slug, defaults={'name': name})
                categories[slug] = category
                colors[slug] = color
                created_categories += int(created)

            for slug, name, category_slug, price, available in DEMO_PRODUCTS:
                product, created = Product.objects.get_or_create(
                    slug=slug,
                    defaults={
                        'category': categories[category_slug],
                        'name': name,
                        'price': Decimal(price),
                        'is_available': available,
                        'description': 'Katalogni ko‘rsatish uchun yaratilgan demo mahsulot; narxi namunaviy.',
                        'detailed_information': (
                            'DEMO MA’LUMOT. Ushbu yozuv katalog imkoniyatlarini ko‘rsatish uchun yaratilgan. '
                            'Rasm shartli belgi. Haqiqiy mahsulotning tarkibi, yo‘riqnomasi va narxi '
                            'do‘kon tomonidan tasdiqlanmagan. Bu matn tibbiy yoki qo‘llash bo‘yicha tavsiya emas.'
                        ),
                    },
                )
                if created:
                    product.image.save(f'{slug}.png', ContentFile(demo_image(colors[category_slug])), save=True)
                    created_products += 1

        self.stdout.write(self.style.SUCCESS(
            f'Demo katalog: {created_categories} yangi kategoriya, {created_products} yangi mahsulot. '
            'Mavjud yozuvlar o‘zgartirilmadi.'
        ))
