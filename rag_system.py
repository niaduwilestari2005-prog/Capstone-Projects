from pypdf import PdfReader
from services.ai_client import legacy_model
import io


# =============================================================
# EXTRACT PDF TEXT
# =============================================================

def extract_pdf_text(pdf_file) -> str:
    """
    Mengekstrak teks dari file PDF.
    Mendukung input berupa file object maupun bytes.
    Jika PDF berupa scan/gambar, mengembalikan pesan error informatif.

    Args:
        pdf_file: File PDF (file object atau bytes).

    Returns:
        str: Teks hasil ekstraksi, atau pesan error jika gagal.
    """
    try:
        if hasattr(pdf_file, 'read'):
            pdf_bytes = pdf_file.read()
            pdf_file = io.BytesIO(pdf_bytes)

        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"

        if not text.strip():
            return f"[PDF ini berupa gambar/scan dan tidak bisa dibaca sebagai teks. Total {len(reader.pages)} halaman.]"

        return text.strip()
    except Exception as e:
        return f"Error membaca PDF: {e}"


# =============================================================
# SPLIT TEXT
# =============================================================

def split_chunks(text: str, chunk_size: int = 500) -> list:
    """
    Memecah teks panjang menjadi potongan-potongan (chunks)
    dengan ukuran tertentu agar lebih mudah diproses.

    Args:
        text (str): Teks yang akan dipecah.
        chunk_size (int): Jumlah karakter per chunk. Default 500.

    Returns:
        list: Daftar string potongan teks.
    """
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i+chunk_size])
    return chunks


# =============================================================
# RETRIEVE RELEVANT CONTEXT
# =============================================================

def retrieve_relevant_chunks(question: str, chunks: list) -> str:
    """
    Mencari potongan teks yang paling relevan dengan pertanyaan
    menggunakan metode pencocokan kata kunci sederhana.
    Mengambil 3 chunk dengan skor relevansi tertinggi.

    Args:
        question (str): Pertanyaan dari pengguna.
        chunks (list): Daftar potongan teks dari dokumen.

    Returns:
        str: Gabungan teks dari chunk-chunk paling relevan.
    """
    relevant = []
    for chunk in chunks:
        score = 0
        for word in question.lower().split():
            if word in chunk.lower():
                score += 1
        if score > 0:
            relevant.append((score, chunk))
    relevant.sort(reverse=True)
    top_chunks = [c[1] for c in relevant[:3]]
    return "\n".join(top_chunks)


# =============================================================
# EXTRACT TEXT FROM FILE
# =============================================================

def extract_text_from_file(uploaded_file) -> str:
    """
    Mengekstrak teks dari file yang diupload pengguna.
    Mendukung format .txt dan .pdf.

    Args:
        uploaded_file: File yang diupload melalui Streamlit file uploader.

    Returns:
        str: Teks hasil ekstraksi, atau pesan error jika format tidak didukung.
    """
    filename = uploaded_file.name.lower()
    if filename.endswith(".txt"):
        return uploaded_file.read().decode("utf-8", errors="ignore")
    elif filename.endswith(".pdf"):
        return extract_pdf_text(uploaded_file)
    return "Format file tidak didukung."


# =============================================================
# ASK FROM DOCUMENT
# =============================================================

def ask_from_document(text: str, question: str, lang: str = "id") -> str:
    """
    Menjawab pertanyaan berdasarkan isi dokumen menggunakan Gemini AI.
    Menggunakan teknik RAG (Retrieval-Augmented Generation):
    ambil chunk relevan dari dokumen, lalu gunakan sebagai konteks ke AI.

    Args:
        text (str): Teks lengkap dari dokumen.
        question (str): Pertanyaan dari pengguna.
        lang (str): Kode bahasa, "id" untuk Indonesia, "en" untuk Inggris.

    Returns:
        str: Jawaban dari Gemini AI berdasarkan isi dokumen.
    """
    if not text or len(text.strip()) == 0:
        if lang == "en":
            return "❌ Document is empty or cannot be read."
        return "❌ Dokumen kosong atau tidak bisa dibaca."

    # Pecah dokumen jadi chunks dan ambil yang paling relevan
    chunks = split_chunks(text)
    context = retrieve_relevant_chunks(question, chunks)

    # Fallback: gunakan 2000 karakter pertama jika tidak ada chunk relevan
    if not context.strip():
        context = text[:2000]

    if lang == "en":
        prompt = f"""You are an AI tutor helping answer questions based on a document.
Document content:

{context}

Question: {question}

Answer clearly and in English based on the document content above."""
    else:
        prompt = f"""Kamu adalah AI tutor yang membantu menjawab pertanyaan berdasarkan dokumen.
Berikut isi dokumen:

{context}

Pertanyaan: {question}

Jawab dengan jelas dan mudah dipahami dalam Bahasa Indonesia berdasarkan isi dokumen di atas."""

    response = legacy_model.generate_content(prompt)
    return response.text
