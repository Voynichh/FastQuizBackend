"""fixtures/sources/<slug>.json dosyalarından Django fixture'larını üretir.

Kaynak biçimi (her satır bir soru):
    [soru metni, zorluk (1-3), doğru şık, yanlış şık 1, yanlış şık 2, yanlış şık 3]

Çıktı: fixtures/questions_<slug>.json (quiz.question + quiz.choice).
Birincil anahtarlar sabittir, bu yüzden `loaddata` tekrar çalıştırılabilir:
    soru pk   = kategori_pk * 1000 + sıra (1'den başlar)
    şık pk    = soru_pk * 10 + şık_sırası (0 doğru şık, 1-3 yanlış şıklar)

Çalıştırma:  python scripts/build_fixtures.py
Not: kategori pk'leri fixtures/categories.json ile aynı olmalıdır.
"""

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
CREATED_AT = "2026-10-17T00:00:00Z"


def build() -> None:
    categories = json.loads((FIXTURES / "categories.json").read_text(encoding="utf-8"))
    for category in categories:
        slug = category["fields"]["slug"]
        category_pk = category["pk"]
        source = json.loads((FIXTURES / "sources" / f"{slug}.json").read_text(encoding="utf-8"))
        records = []
        for index, (text, difficulty, *choices) in enumerate(source, start=1):
            assert len(choices) == 4, f"{slug} #{index}: 4 şık olmalı"
            question_pk = category_pk * 1000 + index
            records.append(
                {
                    "model": "quiz.question",
                    "pk": question_pk,
                    "fields": {
                        "category": category_pk,
                        "text": text,
                        "difficulty": difficulty,
                        "explanation": None,
                        "is_active": True,
                        # loaddata auto_now alanlarını doldurmaz; sabit tarih çıktıyı kararlı tutar
                        "created_at": CREATED_AT,
                        "updated_at": CREATED_AT,
                    },
                }
            )
            for position, choice_text in enumerate(choices):
                records.append(
                    {
                        "model": "quiz.choice",
                        "pk": question_pk * 10 + position,
                        "fields": {
                            "question": question_pk,
                            "text": choice_text,
                            "is_correct": position == 0,
                        },
                    }
                )
        out = FIXTURES / f"questions_{slug}.json"
        out.write_text(json.dumps(records, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{out.name}: {len(source)} soru")


if __name__ == "__main__":
    build()
