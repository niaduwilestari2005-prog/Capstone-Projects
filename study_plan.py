from services.ai_client import legacy_model
import json


def generate_study_plan(topic: str, days: int, lang: str = "id") -> list:
    """
    Menghasilkan rencana belajar harian menggunakan Gemini AI
    berdasarkan topik dan durasi belajar yang ditentukan pengguna.

    Args:
        topic (str): Topik yang ingin dipelajari.
        days (int): Jumlah hari untuk rencana belajar.
        lang (str): Kode bahasa, "id" untuk Indonesia, "en" untuk Inggris.

    Returns:
        list: Daftar dict berisi rencana per hari (hari, jam, materi,
              penjelasan, aktivitas), atau list kosong jika parsing gagal.
    """
    if lang == "en":
        prompt = f"""Create a study plan for the topic: {topic}

Duration: {days} days

REQUIRED JSON FORMAT:
[
  {{
    "hari": "Day 1",
    "jam": "08:00 - 10:00",
    "materi": "...",
    "penjelasan": "...",
    "aktivitas": "..."
  }}
]
Write ALL content (materi, penjelasan, aktivitas) in English. Return JSON only, no markdown."""
    else:
        prompt = f"""Buat rencana belajar untuk topik: {topic}

Durasi: {days} hari

WAJIB FORMAT JSON seperti ini:
[
  {{
    "hari": "Day 1",
    "jam": "08:00 - 10:00",
    "materi": "...",
    "penjelasan": "...",
    "aktivitas": "..."
  }}
]
Tulis semua konten dalam Bahasa Indonesia. Kembalikan JSON saja, tanpa markdown."""

    response = legacy_model.generate_content(prompt)

    # Bersihkan markdown code block jika ada, lalu parse JSON
    try:
        text = response.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except:
        # Kembalikan list kosong jika respons tidak bisa di-parse
        return []
