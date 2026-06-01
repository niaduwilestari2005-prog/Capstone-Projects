# 🤖 LearnAI — Platform Pembelajaran Berbasis AI

LearnAI adalah aplikasi web interaktif berbasis **Streamlit** yang memanfaatkan **Google Gemini AI** untuk membantu pengguna belajar secara cerdas dan personal. Aplikasi ini dilengkapi fitur tanya-jawab AI, pembuatan kuis otomatis, analisis dokumen, dan pembuatan rencana belajar.

---

## ✨ Fitur Utama

- 💬 **QA System** — Tanya jawab dengan AI berbasis Gemini
- 📝 **Quiz Generator** — Generate kuis otomatis dari materi
- 📄 **RAG System** — Upload dokumen dan tanya berdasarkan isinya
- 📅 **Study Plan** — Buat rencana belajar yang dipersonalisasi
- 👤 **Manajemen User & Sesi** — Simpan riwayat chat per pengguna

---

## 🛠️ Teknologi yang Digunakan

- [Python 3.13](https://www.python.org/)
- [Streamlit](https://streamlit.io/)
- [Google Gemini API](https://ai.google.dev/)

---

## ⚙️ Cara Menjalankan

### 1. Clone Repository
```bash
git clone https://github.com/username/nama-repo.git
cd nama-repo
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi API Key
Salin file `.env.example` menjadi `.env`, lalu isi dengan API key Gemini kamu:
```bash
cp .env.example .env
```
Edit file `.env`:
```
GEMINI_API_KEY=isi_dengan_api_key_kamu
```

> Dapatkan Gemini API key di: https://aistudio.google.com/app/apikey

### 4. Jalankan Aplikasi
```bash
streamlit run app.py
```

Aplikasi akan terbuka otomatis di browser pada `http://localhost:8501`

---

## 📁 Struktur Project

```
Tugas Akhir/
├── app.py                  # Entry point aplikasi
├── requirements.txt        # Daftar library
├── learnai_data.json       # Database lokal (JSON)
├── .env.example            # Contoh konfigurasi environment
├── assets/
│   └── style.css           # Styling CSS
├── modules/
│   ├── qa_system.py        # Modul tanya jawab AI
│   ├── quiz_generator.py   # Modul generator kuis
│   ├── rag_system.py       # Modul RAG (analisis dokumen)
│   └── study_plan.py       # Modul rencana belajar
├── services/
│   ├── ai_client.py        # Konfigurasi klien Gemini AI
│   └── db_json.py          # Manajemen database JSON
└── ui/
    └── dashboard.py        # Komponen UI dashboard
```

---

## 📌 Catatan

- Pastikan koneksi internet aktif karena aplikasi menggunakan Gemini API
- File `.env` **tidak boleh** dibagikan atau diupload ke repository
