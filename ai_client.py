import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv
import google.generativeai as genai_legacy

# Load API key dari file .env
load_dotenv()

# ============================================================
# INISIALISASI CLIENT GEMINI (terpusat di sini)
# Semua modul yang butuh Gemini AI menggunakan client ini
# ============================================================
genai_legacy.configure(api_key=os.getenv("GEMINI_API_KEY")) 
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Model untuk rag_system dan study_plan yang pakai genai_legacy
legacy_model = genai_legacy.GenerativeModel("gemini-2.5-flash-lite")


def generate_response(prompt: str) -> str:
    """
    Mengirim prompt ke Gemini API dan mengembalikan teks responnya.
    Dilengkapi retry otomatis hingga 3 kali jika server sedang sibuk (503/429).

    Args:
        prompt (str): Teks prompt yang akan dikirim ke Gemini.

    Returns:
        str: Teks respons dari Gemini, atau string kosong jika tidak ada output.

    Raises:
        Exception: Jika error bukan 503/429, atau sudah 3 kali retry gagal.
    """
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            # response.text bisa None kalau model return kosong/tool-only
            text = response.text
            if text is None:
                # Coba ambil dari candidates langsung
                try:
                    parts = response.candidates[0].content.parts
                    text = "".join(p.text for p in parts if hasattr(p, "text") and p.text)
                except Exception:
                    text = ""
            return text or ""
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e) or "429" in str(e):
                if attempt < 2:
                    time.sleep((attempt + 1) * 3)
                    continue
            raise e
    raise Exception("Server sedang sibuk, coba beberapa saat lagi.")
