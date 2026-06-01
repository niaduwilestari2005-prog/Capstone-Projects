from services.ai_client import generate_response


def ask_ai(question: str, lang: str = "id") -> str:
    """
    Mengirim pertanyaan ke Gemini AI dan mengembalikan jawabannya.
    Mendukung dua bahasa: Indonesia (default) dan Inggris.

    Args:
        question (str): Pertanyaan yang diajukan pengguna.
        lang (str): Kode bahasa, "id" untuk Indonesia, "en" untuk Inggris.

    Returns:
        str: Jawaban dari Gemini AI.
    """
    if lang == "en":
        prompt = f"Answer the following question clearly and in English:\n{question}"
    else:
        prompt = f"Jawab pertanyaan berikut dengan jelas dalam Bahasa Indonesia:\n{question}"
    return generate_response(prompt)
