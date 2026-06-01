from services.ai_client import generate_response
import time


def generate_quiz(topic: str, level: str, lang: str = "id") -> str:
    """
    Menghasilkan 5 soal kuis pilihan ganda menggunakan Gemini AI
    berdasarkan topik dan tingkat kesulitan yang diberikan.
    Dilengkapi retry otomatis hingga 3 kali jika server sibuk.

    Args:
        topic (str): Topik soal yang ingin dibuat.
        level (str): Tingkat kesulitan soal (mudah/sedang/sulit).
        lang (str): Kode bahasa, "id" untuk Indonesia, "en" untuk Inggris.

    Returns:
        str: String JSON berisi daftar soal pilihan ganda.

    Raises:
        Exception: Jika server tetap tidak merespons setelah 3 percobaan.
    """
    if lang == "en":
        prompt = f"""Create 5 multiple choice questions about "{topic}" with difficulty level {level}.
Return ONLY valid JSON, no other text, no markdown. Format:
[
  {{
    "question": "Question here?",
    "options": ["A. option1", "B. option2", "C. option3", "D. option4"],
    "answer": 0
  }}
]
"answer" is the index (0-3) of the correct answer. Write all questions and options in English."""
    else:
        prompt = f"""Buat 5 soal pilihan ganda tentang "{topic}" dengan tingkat kesulitan {level}.
Kembalikan HANYA JSON valid, tidak ada teks lain, tidak ada markdown. Format:
[
  {{
    "question": "Pertanyaan di sini?",
    "options": ["A. opsi1", "B. opsi2", "C. opsi3", "D. opsi4"],
    "answer": 0
  }}
]
"answer" adalah index (0-3) dari jawaban yang benar. Tulis semua soal dalam Bahasa Indonesia."""

    # Retry hingga 3 kali jika server sedang tidak tersedia
    for attempt in range(3):
        try:
            return generate_response(prompt)
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                if attempt < 2:
                    time.sleep((attempt + 1) * 3)
                    continue
            raise e

    raise Exception("Server sedang sibuk, coba beberapa saat lagi.")
