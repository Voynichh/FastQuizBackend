from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.quiz.models import Category


class Command(BaseCommand):
    help = (
        "fixtures/ altındaki kategori ve soru verisini yükler. Veritabanında zaten kategori "
        "varsa atlar (veritabanındaki mevcut veri ezilmesin); --force ile yeniden yükler."
    )

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Veri olsa bile yeniden yükle")

    def handle(self, *args, force=False, **options):
        if Category.objects.exists() and not force:
            self.stdout.write("Veri zaten var, atlandı (yeniden yüklemek için --force).")
            return
        fixtures = settings.BASE_DIR / "fixtures"
        files = [fixtures / "categories.json", *sorted(fixtures.glob("questions_*.json"))]
        call_command("loaddata", *map(str, files), verbosity=0)
        self.stdout.write(self.style.SUCCESS(f"{len(files)} fixture dosyası yüklendi."))
