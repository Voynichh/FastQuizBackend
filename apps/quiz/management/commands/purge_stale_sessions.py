from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.quiz.models import QuizSession


class Command(BaseCommand):
    help = (
        "Terk edilmiş ya da hiç bitmemiş eski quiz oturumlarını (ve soru satırlarını) siler. "
        "Skor tablosuna yazılmış oturumlara dokunmaz."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours", type=int, default=24, help="Bitmemiş oturumlar için eşik (saat)"
        )
        parser.add_argument(
            "--completed-days",
            type=int,
            default=7,
            help="Tamamlanmış ama skoru kaydedilmemiş oturumlar için eşik (gün)",
        )
        parser.add_argument("--dry-run", action="store_true", help="Silmeden sayıyı göster")

    def handle(self, *args, hours, completed_days, dry_run, **options):
        now = timezone.now()
        unfinished = ~Q(status=QuizSession.Status.COMPLETED) & Q(
            last_activity_at__lt=now - timedelta(hours=hours)
        )
        unsaved = Q(status=QuizSession.Status.COMPLETED) & Q(
            finished_at__lt=now - timedelta(days=completed_days)
        )
        # Skoru kaydedilmiş oturum silinirse ScoreEntry de cascade ile silinirdi: hariç tut
        stale = QuizSession.objects.filter(unfinished | unsaved, score_entry__isnull=True)
        count = stale.count()
        if dry_run:
            self.stdout.write(f"{count} oturum silinecekti (dry-run).")
            return
        stale.delete()
        self.stdout.write(self.style.SUCCESS(f"{count} eski oturum silindi."))
