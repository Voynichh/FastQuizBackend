"""Skor tablosu sorguları ve oyuncu adı doğrulaması.

Sıralama kuralı: puan (yüksek) → ortalama cevap süresi (düşük) → önce kaydeden → id.
"""

import re
import string
import unicodedata

from django.conf import settings
from django.db.models import Q

from apps.common.exceptions import ValidationFailed

from .models import ScoreEntry

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 20
# İzin verilen karakterler: Latin harfler (aksanlılar dahil: ç ğ ı ö ş ü é ñ ...), ASCII rakamlar,
# boşluk, alt çizgi, tire ve nokta. Kiril/Yunan gibi Latin'e benzeyen harfler (homoglif) reddedilir.
_ALLOWED_BASE = set(string.ascii_letters + string.digits + "ıİ _.-")

# Normalize edilmiş (ASCII, küçük harf) küfür kökleri. >=5 karakterliler ad içinde
# aranır; kısalar yalnızca tam kelime olarak eşleşir (Sikke/Dickens gibi adlar geçsin).
_PROFANITY = {
    # Türkçe
    "amk", "aq", "sik", "pic", "got", "yarak", "ibne", "gavat", "kahpe",
    "sikik", "siktir", "sikeyim", "orospu", "pezevenk", "yarrak", "amcik",
    "gotveren", "ananisikeyim", "oruspu", "orosbu",
    # İngilizce
    "fuck", "shit", "cunt", "dick", "cock", "slut", "rape",
    "fucker", "fucking", "fuckyou", "bitch", "whore", "pussy", "nigger", "nigga",
    "faggot", "bastard", "asshole", "bullshit", "shitty", "shithead", "motherfucker",
}  # fmt: skip
_SUBSTRING_MIN = 5
_SHORT = {w for w in _PROFANITY if len(w) < _SUBSTRING_MIN}
_LONG = {w for w in _PROFANITY if len(w) >= _SUBSTRING_MIN}

_TR_MAP = str.maketrans("çğıöşüâîû", "cgiosuaiu")
_LEET = str.maketrans("013457", "oieast")


def _normalize(text: str) -> str:
    text = text.replace("İ", "i").replace("I", "i").lower().translate(_TR_MAP)
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch)).translate(_LEET)


def _squash(text: str) -> str:
    """Ardışık tekrar eden harfleri teke indirir: shiit → shit, siiktir → siktir."""
    return re.sub(r"(.)\1+", r"\1", text)


def contains_profanity(name: str) -> bool:
    normalized = _normalize(name)
    words = [w for w in re.split(r"[ _.\-]+", normalized) if w]
    squashed_words = [_squash(w) for w in words]
    if any(w in _SHORT or sq in _SHORT for w, sq in zip(words, squashed_words, strict=True)):
        return True
    # Harfler boşluk/noktalarla ayrılmış olabilir (s i k t i r, f.u.c.k)
    compact = re.sub(r"[ _.\-]+", "", normalized)
    candidates = {compact, _squash(compact)}
    if any(bad in candidate for bad in _LONG for candidate in candidates):
        return True
    # "f u c k" gibi tek tek harflerden oluşan kısa kökler
    return len(words) > 1 and all(len(w) == 1 for w in words) and _squash(compact) in _SHORT


def _base_char(ch: str) -> str:
    """Aksanı atılmış temel karakter (ş → s, é → e); ayrışmayan karakterler olduğu gibi kalır."""
    decomposed = [c for c in unicodedata.normalize("NFD", ch) if not unicodedata.combining(c)]
    return decomposed[0] if len(decomposed) == 1 else ""


def _has_only_allowed_chars(name: str) -> bool:
    return all(_base_char(ch) in _ALLOWED_BASE for ch in name)


def validate_player_name(raw: str) -> str:
    """Temizlenmiş adı döner; geçersizse `validation_error` (400) fırlatır."""
    name = unicodedata.normalize("NFC", (raw or "").strip())
    if not NAME_MIN_LENGTH <= len(name) <= NAME_MAX_LENGTH:
        raise ValidationFailed(
            "Geçersiz isim.",
            details={"player_name": [f"İsim {NAME_MIN_LENGTH}-{NAME_MAX_LENGTH} karakter olmalı."]},
        )
    if not _has_only_allowed_chars(name):
        raise ValidationFailed(
            "Geçersiz isim.",
            details={
                "player_name": ["İsim yalnızca Latin harf, rakam, boşluk ve _ - . içerebilir."]
            },
        )
    if contains_profanity(name):
        raise ValidationFailed(
            "Geçersiz isim.", details={"player_name": ["Lütfen uygun bir isim seç."]}
        )
    return name


def _before(category, score, avg_response_ms, created_at=None, entry_id=None):
    """Verilen değerlerin ÖNÜNDE yer alan kayıtlar için filtre."""
    q = Q(score__gt=score) | Q(score=score, avg_response_ms__lt=avg_response_ms)
    tie = Q(score=score, avg_response_ms=avg_response_ms)
    if created_at is not None:
        q |= tie & (Q(created_at__lt=created_at) | Q(created_at=created_at, id__lt=entry_id))
    else:
        q |= tie  # henüz kaydedilmemiş skor: eşitlikte herkes önde sayılır
    queryset = ScoreEntry.objects.filter(q)
    return queryset.filter(category=category) if category is not None else queryset


def rank_of(entry: ScoreEntry) -> int:
    """Kaydedilmiş bir skorun kategori içindeki sırası (1 tabanlı)."""
    return (
        _before(
            entry.category_id,
            entry.score,
            entry.avg_response_ms,
            created_at=entry.created_at,
            entry_id=entry.id,
        ).count()
        + 1
    )


def estimated_rank(category, *, score: int, avg_response_ms: int) -> int:
    """Henüz kaydedilmemiş bir skor için tahmini sıra."""
    return _before(getattr(category, "id", category), score, avg_response_ms).count() + 1


def top_entries(category=None) -> list[dict]:
    """İlk N skor (kategori verilmezse genel). Sıra numarası eklenmiş sözlük listesi."""
    queryset = ScoreEntry.objects.all()
    if category is not None:
        queryset = queryset.filter(category=category)
    rows = queryset.values(
        "player_name", "score", "correct_count", "avg_response_ms", "created_at"
    )[: settings.LEADERBOARD_SIZE]
    return [{"rank": i, **row} for i, row in enumerate(rows, start=1)]
