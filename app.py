import streamlit as st
import streamlit.components.v1 as components
import json
import re

from modules.qa_system import ask_ai
from modules.quiz_generator import generate_quiz
from modules.rag_system import extract_text_from_file, ask_from_document
from modules.study_plan import generate_study_plan
from services.db_json import (
    get_or_create_user, get_user_sessions,
    create_session, update_session, sync_session_to_db,
    load_data, save_data
)

# ── Helper: simpan & load chat messages per user ke DB ──
def db_save_chat(user_id: int, messages: list):
    data = load_data()
    if "chats" not in data:
        data["chats"] = {}
    saveable = [m for m in messages if m.get("type") not in ("generating",)]
    data["chats"][str(user_id)] = saveable
    save_data(data)

def db_load_chat(user_id: int) -> list:
    data = load_data()
    return data.get("chats", {}).get(str(user_id), [])

def db_save_chat_history(user_id: int, history: list):
    data = load_data()
    if "chat_history" not in data:
        data["chat_history"] = {}
    data["chat_history"][str(user_id)] = history
    save_data(data)

def db_load_chat_history(user_id: int) -> list:
    data = load_data()
    return data.get("chat_history", {}).get(str(user_id), [])

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="LearnAI", page_icon="🤖")

# --- GLOBAL STYLE ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Share+Tech+Mono&family=DM+Sans:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }
.main .block-container { padding: 0 !important; max-width: 100% !important; }
.stApp { background: #020617 !important; }
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
footer { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
button[data-testid="collapsedControl"] { display: none !important; }

button[kind="primary"], button[kind="secondary"] {
    clip-path: none !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
defaults = {
    "menu": "Home",
    "user_name": "",
    "user_id": None,
    "sessions": [],
    "active_session": None,
    "total_questions": 0,
    "total_quizzes": 0,
    "total_docs": 0,
    "chat_messages": [],
    "chat_conversations": [],
    "active_conversation_id": None,
    "doc_text": "",
    "doc_name": "",
    "pending_quiz_topic": "",
    "waiting_for_topic": False,
    "plan_data": [],
    "plan_topic": "",
    "plan_generated": False,
    "input_counter": 0,
    "modal_step": 0,
    "modal_sname": "",
    "modal_topics": "",
    "modal_level": "Beginner",
    "modal_deadline": "",
    "modal_topics2": "",
    "modal_level2": "Beginner",
    "active_chapter": 0,
    "active_material": 0,
    "material_view": "list",
    "delete_conv_id": None,
    "lang": "id",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

ss = st.session_state

# ── i18n translations ──
TRANSLATIONS = {
    "id": {
        "new_chat": "＋  New Chat",
        "chat_history_label": "Riwayat Percakapan",
        "no_history": "Belum ada riwayat percakapan",
        "free_plan": "Free plan",
        "delete_help": "Hapus",
        "lang_toggle": "🇬🇧 English",
        "dashboard": "DASHBOARD",
        "chat_ai_nav": "CHAT AI",
        "plan_belajar": "PLAN BELAJAR",
        "home_nav": "← HOME",
        "home_initializing": "Initializing Neural System...",
        "home_subtitle": "Platform belajar adaptif berbasis AI pintar.<br>Belajar lebih cerdas, lebih cepat, dan kapan saja secara personal.",
        "home_cta_btn": "[ Mulai Belajar ]",
        "home_bio_dev_label": "// Developer Profile",
        "home_bio_city_label": "Asal Kota",
        "home_bio_campus_label": "Kampus",
        "home_bio_major_label": "Jurusan",
        "home_ticker": ["LearnAI Platform", "AI-Powered Education", "Adaptive Learning Engine", "Neural Network Online", "STMIK Kaputama", "Sistem Informasi"],
        "home_name_hint": "Siapa namamu?",
        "home_name_placeholder": "Tulis namamu di sini...",
        "home_start": "[ MULAI BELAJAR ]",
        "home_name_warn": "⚠ Tulis namamu dulu ya!",
        "greeting_morning": "Selamat Pagi",
        "greeting_afternoon": "Selamat Siang",
        "greeting_sore": "Selamat Sore",
        "greeting_evening": "Selamat Malam",
        "dsb_title_prefix": "Dashboard Belajar",
        "dsb_no_session": "Belum ada session aktif",
        "dsb_no_session_sub": "// Buka Plan Belajar, buat session, lalu klik ▶ untuk mulai.",
        "dsb_go_plan": "→ Ke Plan Belajar",
        "dsb_target_today": "Target Hari Ini",
        "dsb_all_done": "✓ SEMUA MATERI SELESAI DIKERJAKAN!",
        "dsb_analysis": "Analisis Diagnostik Progres",
        "dsb_streak": "Keaktifan Beruntun",
        "dsb_streak_unit": "hari",
        "dsb_streak_empty": "// Mulai petualangan belajarmu!",
        "dsb_avg_score": "Rata-Rata Nilai Kuis",
        "dsb_quiz_done_unit": "kuis selesai",
        "dsb_excellent": "✓ Excellent Perform",
        "dsb_keep_practicing": "⚡ Keep Practicing",
        "dsb_status": "Status Kelulusan Belajar",
        "dsb_above_target": "SUDAH MELEBIHI TARGET",
        "dsb_below_target": "BELUM MENCAPAI TARGET",
        "dsb_status_ok": "// Performa belajar Anda sangat baik dan sesuai target.",
        "dsb_status_warn": "// Tingkatkan keaktifan membaca materi untuk mengejar target.",
        "dsb_quiz_history": "📊 Riwayat Hasil Kuis",
        "dsb_quiz_no_data": "// BELUM ADA QUIZ — MULAI BELAJAR UNTUK MELIHAT RIWAYAT",
        "dsb_col_topic": "Chapter Topic",
        "dsb_col_level": "Level",
        "dsb_col_score": "Score",
        "dsb_col_diag": "Diagnosis Analysis",
        "plan_greeting_sub": "// kelola session belajar & jadwal harianmu",
        "plan_add_session": "＋ Add Session",
        "plan_tab_sessions": "📋  Sessions",
        "plan_tab_materials": "📚  Study Materials",
        "plan_col_name": "Session Name",
        "plan_col_progress": "Progress",
        "plan_col_last": "Last Checked",
        "plan_col_topics": "Topics",
        "plan_col_action": "Aksi",
        "plan_empty": '// Belum ada session. Klik "+ Add Session" untuk mulai.',
        "plan_btn_open_help": "Buka Study Materials",
        "plan_btn_edit_help": "Edit Session",
        "plan_btn_del_help": "Hapus Session",
        "plan_no_selected": "Belum ada session yang dipilih",
        "plan_no_selected_sub": "// Klik ▶ pada session untuk membuka Study Materials",
        "plan_back_sessions": "← Kembali ke Sessions",
        "plan_session_active": "// SESSION AKTIF",
        "plan_generate_spinner": "AI sedang menyiapkan materi untuk",
        "plan_generate_spinner_plan": "Generating study plan untuk",
        "plan_chapter_locked": "🔒 Selesaikan chapter sebelumnya untuk membuka ini.",
        "plan_start_quiz": "Mulai Quiz →",
        "plan_start_lesson": "Mulai Belajar →",
        "plan_back_list": "← Kembali ke Daftar",
        "plan_prev": "← Sebelumnya",
        "plan_finish": "✅ Selesai",
        "plan_generating_material": "AI menyiapkan materi",
        "quiz_making": "Membuat soal quiz...",
        "quiz_chapter_sub": "Selesaikan quiz ini untuk membuka chapter berikutnya.",
        "quiz_question_label": "Question",
        "quiz_of": "of",
        "quiz_answered": "answered",
        "quiz_prev": "← Prev",
        "quiz_next": "Next →",
        "quiz_submit": "✅ Submit Quiz",
        "quiz_pass": "🎉 Bagus! Kamu bisa lanjut ke chapter berikutnya.",
        "quiz_fail": "📖 Pelajari lagi materinya ya!",
        "quiz_retry": "🔄 Ulangi Quiz",
        "quiz_continue": "Lanjut →",
        "quiz_review_label": "// Review Jawaban",
        "quiz_correct_label": "Jawaban benar:",
        "quiz_your_label": "Jawaban kamu:",
        "quiz_correct": "Benar",
        "quiz_wrong": "Salah",
        "quiz_not_answered": "Tidak dijawab",
        "quiz_back_read": "← Pelajari Lagi",
        "quiz_analysis_excellent": "Pemahaman sangat baik!",
        "quiz_analysis_good": "Cukup baik, perlu latihan lagi.",
        "quiz_analysis_poor": "Perlu ulang materi ini.",
        "quiz_score_correct": "benar",
        "plan_all_done": "🎉 Selamat! Semua materi session ini sudah selesai!",
        "plan_all_done_text": "Semua materi selesai!",
        "plan_complete_pct": "Selesai",
        "dlg_add_title": "Add Session",
        "dlg_add_subtitle": "A session is your isolated learning workspace",
        "dlg_step1_title": "Create New Session",
        "dlg_field_name": "SESSION NAME",
        "dlg_field_name_ph": "e.g. UTS Machine Learning",
        "dlg_field_topics": "TOPICS",
        "dlg_field_topics_ph": "e.g. Python, ML, Kalkulus",
        "dlg_field_level": "YOUR LEVEL",
        "dlg_cancel": "Batal",
        "dlg_continue": "Lanjut →",
        "dlg_step2_title": "How Do You Want To Learn?",
        "dlg_step2_sub": "Set your study goal and pace",
        "dlg_field_deadline": "DEADLINE",
        "dlg_field_topics2": "Topik spesifik yang ingin dipelajari",
        "dlg_back": "← Back",
        "dlg_create_btn": "Create Session",
        "dlg_creating": "Generating Study Plan and Learning Path...",
        "dlg_edit_title": "Edit Session",
        "dlg_edit_save": "💾 Simpan",
        "dlg_edit_name_warn": "Nama session tidak boleh kosong!",
        "dlg_delete_title": "Hapus Session",
        "dlg_delete_confirm_text": "dan semua data di dalamnya akan dihapus permanen dan tidak bisa dikembalikan.",
        "dlg_delete_will": "Session",
        "dlg_delete_confirm": "🗑️ Ya, Hapus",
        "chat_ai_title": "Chat AI",
        "chat_ai_sub": "Tanya apa saja · Upload PDF · Minta quiz interaktif",
        "chat_placeholder": "Tanya sesuatu... (ketik / untuk perintah)",
        "how_help": "How can I help you?",
        "how_help_sub": "Mulai dengan pertanyaan, minta quiz, atau upload dokumen untuk belajar lebih cepat.",
        "btn_talk": "Let's talk about..",
        "btn_help": "Help me with..",
        "btn_teach": "Teach me to..",
        "btn_analyse": "Analyse this topic..",
        "btn_story": "Write a story about..",
    },
    "en": {
        "new_chat": "＋  New Chat",
        "chat_history_label": "Chat History",
        "no_history": "No conversation history yet",
        "free_plan": "Free plan",
        "delete_help": "Delete",
        "lang_toggle": "🇮🇩 Indonesia",
        "dashboard": "DASHBOARD",
        "chat_ai_nav": "CHAT AI",
        "plan_belajar": "STUDY PLAN",
        "home_nav": "← HOME",
        "home_initializing": "Initializing Neural System...",
        "home_subtitle": "Your adaptive AI-powered learning platform.<br>Study smarter, faster, and anytime — personally tailored.",
        "home_cta_btn": "[ Start Learning ]",
        "home_bio_dev_label": "// Developer Profile",
        "home_bio_city_label": "Hometown",
        "home_bio_campus_label": "University",
        "home_bio_major_label": "Major",
        "home_ticker": ["LearnAI Platform", "AI-Powered Education", "Adaptive Learning Engine", "Neural Network Online", "STMIK Kaputama", "Information Systems"],
        "home_name_hint": "What's your name?",
        "home_name_placeholder": "Type your name here...",
        "home_start": "[ START LEARNING ]",
        "home_name_warn": "⚠ Please enter your name first!",
        "greeting_morning": "Good Morning",
        "greeting_afternoon": "Good Afternoon",
        "greeting_sore": "Good Afternoon",
        "greeting_evening": "Good Evening",
        "dsb_title_prefix": "Learning Dashboard",
        "dsb_no_session": "No active session",
        "dsb_no_session_sub": "// Go to Study Plan, create a session, then click ▶ to start.",
        "dsb_go_plan": "→ Go to Study Plan",
        "dsb_target_today": "Today's Targets",
        "dsb_all_done": "✓ ALL MATERIALS COMPLETED!",
        "dsb_analysis": "Progress Diagnostic Analysis",
        "dsb_streak": "Learning Streak",
        "dsb_streak_unit": "days",
        "dsb_streak_empty": "// Start your learning adventure!",
        "dsb_avg_score": "Average Quiz Score",
        "dsb_quiz_done_unit": "quizzes done",
        "dsb_excellent": "✓ Excellent Perform",
        "dsb_keep_practicing": "⚡ Keep Practicing",
        "dsb_status": "Learning Progress Status",
        "dsb_above_target": "ABOVE TARGET",
        "dsb_below_target": "BELOW TARGET",
        "dsb_status_ok": "// Your learning performance is excellent and on track.",
        "dsb_status_warn": "// Increase your study activity to catch up with the target.",
        "dsb_quiz_history": "📊 Quiz History",
        "dsb_quiz_no_data": "// NO QUIZZES YET — START LEARNING TO SEE HISTORY",
        "dsb_col_topic": "Chapter Topic",
        "dsb_col_level": "Level",
        "dsb_col_score": "Score",
        "dsb_col_diag": "Diagnosis Analysis",
        "plan_greeting_sub": "// manage your learning sessions & daily schedule",
        "plan_add_session": "＋ Add Session",
        "plan_tab_sessions": "📋  Sessions",
        "plan_tab_materials": "📚  Study Materials",
        "plan_col_name": "Session Name",
        "plan_col_progress": "Progress",
        "plan_col_last": "Last Checked",
        "plan_col_topics": "Topics",
        "plan_col_action": "Actions",
        "plan_empty": '// No sessions yet. Click "+ Add Session" to start.',
        "plan_btn_open_help": "Open Study Materials",
        "plan_btn_edit_help": "Edit Session",
        "plan_btn_del_help": "Delete Session",
        "plan_no_selected": "No session selected",
        "plan_no_selected_sub": "// Click ▶ on a session to open Study Materials",
        "plan_back_sessions": "← Back to Sessions",
        "plan_session_active": "// ACTIVE SESSION",
        "plan_generate_spinner": "AI is preparing materials for",
        "plan_generate_spinner_plan": "Generating study plan for",
        "plan_chapter_locked": "🔒 Complete the previous chapter to unlock this one.",
        "plan_start_quiz": "Start Quiz →",
        "plan_start_lesson": "Start Learning →",
        "plan_back_list": "← Back to List",
        "plan_prev": "← Previous",
        "plan_finish": "✅ Done",
        "plan_generating_material": "AI preparing material",
        "quiz_making": "Generating quiz questions...",
        "quiz_chapter_sub": "Complete this quiz to unlock the next chapter.",
        "quiz_question_label": "Question",
        "quiz_of": "of",
        "quiz_answered": "answered",
        "quiz_prev": "← Prev",
        "quiz_next": "Next →",
        "quiz_submit": "✅ Submit Quiz",
        "quiz_pass": "🎉 Great! You can move on to the next chapter.",
        "quiz_fail": "📖 Review the material again!",
        "quiz_retry": "🔄 Retry Quiz",
        "quiz_continue": "Continue →",
        "quiz_review_label": "// Answer Review",
        "quiz_correct_label": "Correct answer:",
        "quiz_your_label": "Your answer:",
        "quiz_correct": "Correct",
        "quiz_wrong": "Wrong",
        "quiz_not_answered": "Not answered",
        "quiz_back_read": "← Review Material",
        "quiz_analysis_excellent": "Excellent understanding!",
        "quiz_analysis_good": "Good, but needs more practice.",
        "quiz_analysis_poor": "Please review this material again.",
        "quiz_score_correct": "correct",
        "plan_all_done": "🎉 Congratulations! All materials in this session are complete!",
        "plan_all_done_text": "All done!",
        "plan_complete_pct": "Complete",
        "dlg_add_title": "Add Session",
        "dlg_add_subtitle": "A session is your isolated learning workspace",
        "dlg_step1_title": "Create New Session",
        "dlg_field_name": "SESSION NAME",
        "dlg_field_name_ph": "e.g. UTS Machine Learning",
        "dlg_field_topics": "TOPICS",
        "dlg_field_topics_ph": "e.g. Python, ML, Calculus",
        "dlg_field_level": "YOUR LEVEL",
        "dlg_cancel": "Cancel",
        "dlg_continue": "Continue →",
        "dlg_step2_title": "How Do You Want To Learn?",
        "dlg_step2_sub": "Set your study goal and pace",
        "dlg_field_deadline": "DEADLINE",
        "dlg_field_topics2": "Specific topics you want to learn",
        "dlg_back": "← Back",
        "dlg_create_btn": "Create Session",
        "dlg_creating": "Generating Study Plan and Learning Path...",
        "dlg_edit_title": "Edit Session",
        "dlg_edit_save": "💾 Save",
        "dlg_edit_name_warn": "Session name cannot be empty!",
        "dlg_delete_title": "Delete Session",
        "dlg_delete_confirm_text": "and all its data will be permanently deleted and cannot be recovered.",
        "dlg_delete_will": "Session",
        "dlg_delete_confirm": "🗑️ Yes, Delete",
        "chat_ai_title": "Chat AI",
        "chat_ai_sub": "Ask anything · Upload PDF · Request interactive quiz",
        "chat_placeholder": "Ask something... (type / for commands)",
        "how_help": "How can I help you?",
        "how_help_sub": "Start with a question, request a quiz, or upload a document to learn faster.",
        "btn_talk": "Let's talk about..",
        "btn_help": "Help me with..",
        "btn_teach": "Teach me to..",
        "btn_analyse": "Analyse this topic..",
        "btn_story": "Write a story about..",
    }
}

def t(key: str) -> str:
    lang = ss.get("lang", "id")
    return TRANSLATIONS.get(lang, TRANSLATIONS["id"]).get(key, key)

def cur_lang() -> str:
    return ss.get("lang", "id")

# ── Conversation helpers ──
def new_conversation():
    import datetime
    conv_id = str(datetime.datetime.now().timestamp()).replace(".", "")
    conv = {
        "id": conv_id,
        "title": "New Chat",
        "messages": [],
        "timestamp": datetime.datetime.now().strftime("%d %b %Y, %H:%M"),
    }
    ss.chat_conversations.insert(0, conv)
    ss.active_conversation_id = conv_id
    ss.chat_messages = []
    uid = ss.get("user_id")
    if uid:
        db_save_chat_history(uid, ss.chat_conversations)
    return conv_id

def get_active_conv():
    if not ss.active_conversation_id:
        return None
    for c in ss.chat_conversations:
        if c["id"] == ss.active_conversation_id:
            return c
    return None

def sync_messages_to_conv():
    conv = get_active_conv()
    if conv is not None:
        conv["messages"] = ss.chat_messages
        for m in ss.chat_messages:
            if m["role"] == "user" and m.get("content"):
                title = m["content"][:40] + ("…" if len(m["content"]) > 40 else "")
                conv["title"] = title
                break
        uid = ss.get("user_id")
        if uid:
            db_save_chat_history(uid, ss.chat_conversations)
            db_save_chat(uid, ss.chat_messages)

def get_home_html():
 return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&family=DM+Sans:ital,wght@0,300;0,400;1,300&display=swap');
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: 100%; height: 100%; overflow: hidden; background: #020617; }}
canvas#bg {{ position: fixed; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; }}
.scanline {{ position: fixed; inset: 0; background: repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(56,189,248,0.008) 2px,rgba(56,189,248,0.008) 4px); pointer-events: none; z-index: 5; }}
.vignette {{ position: fixed; inset: 0; background: radial-gradient(ellipse at center,transparent 35%,rgba(2,6,23,0.65) 100%); pointer-events: none; z-index: 6; }}
.screen {{ position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; z-index: 10; transition: opacity 0.9s ease; }}
.screen.hidden {{ opacity: 0; pointer-events: none; }}
.screen.visible {{ opacity: 1; }}
.corner {{ position: absolute; width: 28px; height: 28px; border-color: rgba(56,189,248,0.4); border-style: solid; z-index: 20; }}
.c-tl {{ top: 20px; left: 20px; border-width: 2px 0 0 2px; }}
.c-tr {{ top: 20px; right: 20px; border-width: 2px 2px 0 0; }}
.c-bl {{ bottom: 34px; left: 20px; border-width: 0 0 2px 2px; }}
.c-br {{ bottom: 34px; right: 20px; border-width: 0 2px 2px 0; }}
.hud-l {{ position: absolute; left: 32px; top: 50%; transform: translateY(-50%); z-index: 20; display: flex; flex-direction: column; gap: 22px; }}
.hud-block {{ display: flex; flex-direction: column; gap: 3px; }}
.hud-lbl {{ font-family: 'Share Tech Mono', monospace; font-size: 8px; color: rgba(56,189,248,0.38); letter-spacing: .22em; text-transform: uppercase; }}
.hud-val {{ font-family: 'Share Tech Mono', monospace; font-size: 13px; color: #38bdf8; letter-spacing: .05em; display: flex; align-items: center; gap: 5px; }}
.hud-dot {{ width: 6px; height: 6px; border-radius: 50%; background: #10b981; animation: pulse 1.8s ease-in-out infinite; }}
.hud-bar {{ width: 64px; height: 2px; background: rgba(56,189,248,0.1); border-radius: 2px; margin-top: 4px; overflow: hidden; }}
.hud-fill {{ height: 100%; background: linear-gradient(90deg, #6366f1, #38bdf8); border-radius: 2px; animation: barpulse 2.6s ease-in-out infinite; }}
.hud-r {{ position: absolute; right: 32px; top: 50%; transform: translateY(-50%); z-index: 20; display: flex; flex-direction: column; gap: 10px; align-items: flex-end; }}
.hud-cnt {{ font-family: 'Share Tech Mono', monospace; font-size: 9px; color: rgba(56,189,248,0.3); letter-spacing: .1em; }}
.hud-cnt span {{ color: #38bdf8; }}
.hud-line {{ width: 52px; height: 1px; background: linear-gradient(90deg, transparent, rgba(56,189,248,0.35)); }}
#screen-welcome .wc {{ text-align: center; }}
.wl1 {{ font-family: 'Share Tech Mono', monospace; font-size: 11px; color: rgba(56,189,248,0.5); letter-spacing: .42em; text-transform: uppercase; margin-bottom: 14px; animation: fadeup .8s ease both; }}
.wl2 {{ font-family: 'Orbitron', monospace; font-size: clamp(2.8rem,7vw,5.4rem); font-weight: 900; color: #f1f5f9; text-shadow: 0 0 40px rgba(56,189,248,0.25); margin-bottom: 12px; animation: fadeup .8s ease .2s both; }}
.wl2 span {{ color: #38bdf8; }}
.wl3 {{ font-family: 'Share Tech Mono', monospace; font-size: 10px; color: rgba(56,189,248,0.3); letter-spacing: .3em; animation: fadeup .8s ease .4s both; }}
.blink {{ animation: blink 1.5s infinite; }}
@keyframes blink {{ 0%,100%{{opacity:.3}} 50%{{opacity:1}} }}
.wbar {{ width: 192px; height: 2px; background: rgba(56,189,248,0.08); border-radius: 2px; margin: 20px auto 0; overflow: hidden; }}
.wbar-inner {{ height: 100%; width: 0; background: linear-gradient(90deg, transparent, #38bdf8, transparent); animation: barGrow 2.6s ease forwards .6s; }}
@keyframes barGrow {{ to {{ width: 100%; }} }}
#screen-bio .bc {{ display: flex; align-items: center; gap: 40px; background: rgba(2,8,28,0.82); border: 1px solid rgba(56,189,248,0.18); border-radius: 18px; padding: 36px 44px; backdrop-filter: blur(14px); animation: scaleUp .85s ease both; max-width: 660px; box-shadow: 0 0 48px rgba(56,189,248,0.06); }}
.bio-av {{ width: 110px; height: 110px; border-radius: 50%; border: 2px solid rgba(56,189,248,0.4); background: rgba(56,189,248,0.06); display: flex; align-items: center; justify-content: center; font-size: 2.6rem; flex-shrink: 0; overflow: hidden; }}
.bio-av img {{ width:100%; height:100%; object-fit:cover; }}
.bio-tag {{ font-family: 'Share Tech Mono', monospace; font-size: 9px; color: rgba(56,189,248,0.4); letter-spacing: .2em; text-transform: uppercase; margin-bottom: 10px; }}
.bio-name {{ font-family: 'Orbitron', monospace; font-size: clamp(1.1rem,2.2vw,1.6rem); font-weight: 900; color: #f1f5f9; text-shadow: 0 0 18px rgba(56,189,248,0.22); margin-bottom: 16px; }}
.bio-rows {{ display: flex; flex-direction: column; gap: 10px; }}
.bio-row {{ display: flex; align-items: flex-start; gap: 10px; }}
.bio-icon {{ font-size: 12px; color: #38bdf8; flex-shrink: 0; margin-top: 2px; }}
.bio-lbl {{ font-family: 'Share Tech Mono', monospace; font-size: 8px; color: rgba(56,189,248,0.35); letter-spacing: .12em; text-transform: uppercase; margin-bottom: 2px; }}
.bio-val {{ font-family: 'DM Sans', sans-serif; font-size: 13px; color: rgba(200,225,255,0.82); line-height: 1.4; }}
.bio-div {{ width: 100%; height: 1px; background: linear-gradient(90deg, rgba(56,189,248,0.22), transparent); margin: 2px 0; }}
.main-c {{ display: flex; flex-direction: column; align-items: center; text-align: center; padding: 0 24px; }}
.badge {{ display: inline-flex; align-items: center; gap: 8px; padding: 5px 18px; border: 1px solid rgba(56,189,248,0.25); background: rgba(56,189,248,0.04); color: #38bdf8; font-family: 'Share Tech Mono', monospace; font-size: 9px; letter-spacing: .2em; text-transform: uppercase; border-radius: 999px; margin-bottom: 18px; animation: fadeup .8s ease .1s both; }}
.bdot {{ width: 6px; height: 6px; background: #38bdf8; border-radius: 50%; animation: pulse 1.5s ease-in-out infinite; }}
.eyebrow {{ font-family: 'Share Tech Mono', monospace; font-size: 11px; color: rgba(56,189,248,0.45); letter-spacing: .38em; text-transform: uppercase; margin-bottom: 6px; animation: fadeup .8s ease .2s both; }}
.headline {{ font-family: 'Orbitron', monospace; font-size: clamp(3.2rem,9vw,6.4rem); font-weight: 900; line-height: 1; margin-bottom: 12px; animation: fadeup .8s ease .3s both; color: #f1f5f9; }}
.hl-ai {{ color: #38bdf8; text-shadow: 0 0 28px rgba(56,189,248,.85), 0 0 72px rgba(56,189,248,.25); animation: glitch 6s ease-in-out infinite; }}
.subtitle {{ font-family: 'DM Sans', sans-serif; color: rgba(148,163,184,0.75); font-size: 13px; font-weight: 300; max-width: 420px; line-height: 1.85; margin-bottom: 30px; animation: fadeup .8s ease .45s both; }}
.cta {{ padding: 13px 48px; border: 1px solid rgba(56,189,248,0.6); background: rgba(56,189,248,0.06); color: #38bdf8; font-family: 'Share Tech Mono', monospace; font-size: 12px; letter-spacing: .2em; text-transform: uppercase; cursor: pointer; border-radius: 12px; opacity: 0; pointer-events: none; transition: opacity .8s ease, background .2s, box-shadow .25s; display: inline-flex; align-items: center; gap: 8px; }}
.cta.show {{ opacity: 1; pointer-events: all; }}
.cta:hover {{ background: rgba(56,189,248,0.14); box-shadow: 0 0 32px rgba(56,189,248,0.2); }}
.cta-arr {{ transition: transform .25s; }}
.cta:hover .cta-arr {{ transform: translateX(4px); }}
.ticker {{ position: fixed; bottom: 0; left: 0; right: 0; height: 28px; background: rgba(2,6,23,0.95); border-top: 1px solid rgba(56,189,248,0.1); display: flex; align-items: center; overflow: hidden; z-index: 30; }}
.ticker-inner {{ display: flex; animation: ticker 26s linear infinite; white-space: nowrap; }}
.tick-item {{ font-family: 'Share Tech Mono', monospace; font-size: 9px; color: rgba(56,189,248,0.35); letter-spacing: .16em; text-transform: uppercase; padding: 0 28px; }}
.tick-sep {{ color: rgba(99,102,241,0.4); }}
@keyframes glitch {{ 0%,92%,100%{{text-shadow:0 0 28px rgba(56,189,248,.85),0 0 72px rgba(56,189,248,.25);transform:none}} 93%{{text-shadow:-3px 0 #ff0060,3px 0 #00ffff;transform:skewX(-4deg)}} 95%{{text-shadow:3px 0 #ff0060,-3px 0 #00ffff;transform:skewX(3deg)}} 97%{{text-shadow:-1px 0 #ff0060,1px 0 #00ffff;transform:none}} }}
@keyframes pulse {{ 0%,100%{{opacity:1;transform:scale(1)}} 50%{{opacity:.25;transform:scale(2)}} }}
@keyframes barpulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.3}} }}
@keyframes ticker {{ 0%{{transform:translateX(0)}} 100%{{transform:translateX(-50%)}} }}
@keyframes fadeup {{ from{{opacity:0;transform:translateY(16px)}} to{{opacity:1;transform:translateY(0)}} }}
@keyframes scaleUp {{ from{{opacity:0;transform:scale(.94)}} to{{opacity:1;transform:scale(1)}} }}
</style>
</head>
<body>
<canvas id="bg"></canvas>
<div class="scanline"></div>
<div class="vignette"></div>
<div id="screen-welcome" class="screen visible">
  <div class="wc">
    <div class="wl1">✦ &nbsp; Welcome to &nbsp; ✦</div>
    <div class="wl2">Learn<span>AI</span></div>
    <div class="wl3 blink">Initializing Neural System...</div>
    <div class="wbar"><div class="wbar-inner"></div></div>
  </div>
</div>
<div id="screen-bio" class="screen hidden">
  <div class="bc">
    <div class="bio-av" id="bioPhoto">👩‍💻</div>
    <div>
      <div class="bio-tag">{t("home_bio_dev_label")}</div>
      <div class="bio-name">Nia Duwi Lestari</div>
      <div class="bio-rows">
        <div class="bio-row"><div class="bio-icon">📍</div><div><div class="bio-lbl">{t("home_bio_city_label")}</div><div class="bio-val">Kota Binjai</div></div></div>
        <div class="bio-div"></div>
        <div class="bio-row"><div class="bio-icon">🎓</div><div><div class="bio-lbl">{t("home_bio_campus_label")}</div><div class="bio-val">STMIK Kaputama</div></div></div>
        <div class="bio-div"></div>
        <div class="bio-row"><div class="bio-icon">💻</div><div><div class="bio-lbl">{t("home_bio_major_label")}</div><div class="bio-val">Sistem Informasi</div></div></div>
      </div>
    </div>
  </div>
</div>
<div id="screen-main" class="screen hidden">
  <div class="corner c-tl"></div><div class="corner c-tr"></div>
  <div class="corner c-bl"></div><div class="corner c-br"></div>
  <div class="hud-l">
    <div class="hud-block">
      <div class="hud-lbl">System</div>
      <div class="hud-val"><span class="hud-dot"></span> ONLINE</div>
      <div class="hud-bar"><div class="hud-fill" style="width:100%"></div></div>
    </div>
    <div class="hud-block">
      <div class="hud-lbl">AI Core</div>
      <div class="hud-val" id="aicore">94.2%</div>
      <div class="hud-bar"><div class="hud-fill" style="width:94%;animation-delay:.4s"></div></div>
    </div>
    <div class="hud-block">
      <div class="hud-lbl">Neural Link</div>
      <div class="hud-val">ACTIVE</div>
      <div class="hud-bar"><div class="hud-fill" style="width:78%;animation-delay:.9s"></div></div>
    </div>
  </div>
  <div class="hud-r">
    <div class="hud-cnt"><span id="fc">00</span> / 86 LOAD</div>
    <div class="hud-line"></div>
    <div class="hud-cnt">SYS <span>V2.5</span></div>
    <div class="hud-line"></div>
    <div class="hud-cnt" style="color:#10b981;">ENC <span style="color:#10b981;">ON</span></div>
    <div class="hud-line"></div>
    <div class="hud-cnt" style="letter-spacing:.2em;">READY</div>
  </div>
  <div class="main-c">
    <div class="badge"><div class="bdot"></div>AI-Powered Learning Workspace</div>
    <div class="eyebrow">Welcome to</div>
    <div class="headline">Learn<span class="hl-ai">AI</span></div>
    <p class="subtitle">{t("home_subtitle")}</p>
    <button class="cta" id="ctaBtn" onclick="triggerStart()">{t("home_cta_btn")} <span class="cta-arr">›</span></button>
  </div>
</div>
<div class="ticker"><div class="ticker-inner">
  <span class="tick-item">LearnAI Platform</span><span class="tick-sep">///</span>
  <span class="tick-item">AI-Powered Education</span><span class="tick-sep">///</span>
  <span class="tick-item">Adaptive Learning Engine</span><span class="tick-sep">///</span>
  <span class="tick-item">Neural Network Online</span><span class="tick-sep">///</span>
  <span class="tick-item">STMIK Kaputama</span><span class="tick-sep">///</span>
  <span class="tick-item">Sistem Informasi</span><span class="tick-sep">///</span>
  <span class="tick-item">LearnAI Platform</span><span class="tick-sep">///</span>
  <span class="tick-item">AI-Powered Education</span><span class="tick-sep">///</span>
  <span class="tick-item">Adaptive Learning Engine</span><span class="tick-sep">///</span>
  <span class="tick-item">Neural Network Online</span><span class="tick-sep">///</span>
  <span class="tick-item">STMIK Kaputama</span><span class="tick-sep">///</span>
  <span class="tick-item">Sistem Informasi</span><span class="tick-sep">///</span>
</div></div>
<script>
const canvas=document.getElementById('bg'),ctx=canvas.getContext('2d');
const fcEl=document.getElementById('fc'),aicEl=document.getElementById('aicore');
function resize(){{canvas.width=window.innerWidth;canvas.height=window.innerHeight;}}
resize();window.addEventListener('resize',()=>{{resize();initScene();}});
function tkPoint(u,P=3,Q=2){{const r=0.5*Math.cos(Q*u)+1.5;return{{x:r*Math.cos(P*u),y:r*Math.sin(P*u),z:-Math.sin(Q*u)}};}}
function project(x,y,z,fov,cx,cy){{const s=fov/(fov+z);return{{px:cx+x*s*160,py:cy+y*s*160,s,z}};}}
const N=260;let particles=[];
function initScene(){{particles=[];for(let i=0;i<N;i++){{const orb=Math.random()<0.28;particles.push({{u:(i/N)*Math.PI*2,spd:0.0025+Math.random()*0.002,spread:orb?Math.random()*0.25+0.04:0,phase:Math.random()*Math.PI*2,bright:Math.random()<0.1,pulse:Math.random()*Math.PI*2,ps:0.018+Math.random()*0.02}});}}}}
initScene();
const signals=[];
function maybeSignal(){{if(signals.length<10&&Math.random()<0.035){{const i=Math.floor(Math.random()*N),j=Math.floor(Math.random()*N);if(i!==j)signals.push({{from:i,to:j,t:0,spd:0.018+Math.random()*0.018}});}}}}
let ft=0,frame=0;
function draw(){{
  ft+=0.009;frame+=1;
  const W=canvas.width,H=canvas.height,CX=W/2,CY=H/2;
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle='#020617';ctx.fillRect(0,0,W,H);
  const g1=ctx.createRadialGradient(CX,CY,0,CX,CY,Math.min(W,H)*0.65);
  g1.addColorStop(0,'rgba(56,189,248,0.1)');g1.addColorStop(.45,'rgba(30,41,59,0.04)');g1.addColorStop(1,'transparent');
  ctx.fillStyle=g1;ctx.fillRect(0,0,W,H);
  const ry=ft*0.32,rx=Math.sin(ft*0.17)*0.22,cosY=Math.cos(ry),sinY=Math.sin(ry),cosX=Math.cos(rx),sinX=Math.sin(rx);
  function rot(x,y,z){{const x1=x*cosY+z*sinY,z1=-x*sinY+z*cosY,y1=y*cosX-z1*sinX,z2=y*sinX+z1*cosX;return{{x:x1,y:y1,z:z2}};}}
  const pts=particles.map(p=>{{const base=tkPoint(p.u),bx=base.x+Math.sin(p.phase+ft)*p.spread,by=base.y+Math.cos(p.phase*1.3+ft)*p.spread,bz=base.z+Math.sin(p.phase*0.7+ft)*p.spread,r=rot(bx,by,bz);return project(r.x,r.y,r.z,5,CX,CY);}});
  for(let i=0;i<pts.length;i+=2){{for(let j=i+1;j<pts.length;j+=2){{const dx=pts[i].px-pts[j].px,dy=pts[i].py-pts[j].py,d=Math.sqrt(dx*dx+dy*dy);if(d<52){{ctx.beginPath();ctx.moveTo(pts[i].px,pts[i].py);ctx.lineTo(pts[j].px,pts[j].py);ctx.strokeStyle=`rgba(56,189,248,${{(1-d/52)*0.32*Math.min(pts[i].s,pts[j].s)}})`;ctx.lineWidth=0.55;ctx.stroke();}}}}}}
  maybeSignal();
  for(let k=signals.length-1;k>=0;k--){{const sg=signals[k];sg.t+=sg.spd;if(sg.t>=1){{signals.splice(k,1);continue;}}const a=pts[sg.from],b=pts[sg.to];if(a&&b){{const px=a.px+(b.px-a.px)*sg.t,py=a.py+(b.py-a.py)*sg.t;const sg2=ctx.createRadialGradient(px,py,0,px,py,8);sg2.addColorStop(0,'rgba(255,255,255,.92)');sg2.addColorStop(.4,'rgba(56,189,248,.6)');sg2.addColorStop(1,'rgba(0,0,0,0)');ctx.beginPath();ctx.arc(px,py,8,0,Math.PI*2);ctx.fillStyle=sg2;ctx.fill();}}}}
  const sorted=pts.map((p,i)=>({{...p,i}})).sort((a,b)=>a.z-b.z);
  sorted.forEach(({{px,py,s,i}})=>{{const p=particles[i];p.pulse+=p.ps;const pv=0.5+0.5*Math.sin(p.pulse),r=Math.max(0.8,(1.4+pv*1.1)*s);if(p.bright){{const bg=ctx.createRadialGradient(px,py,0,px,py,r*10);bg.addColorStop(0,`rgba(186,230,253,${{0.5+pv*.3}})`);bg.addColorStop(.3,`rgba(56,189,248,${{0.2+pv*.1}})`);bg.addColorStop(1,'rgba(0,0,0,0)');ctx.beginPath();ctx.arc(px,py,r*10,0,Math.PI*2);ctx.fillStyle=bg;ctx.fill();ctx.beginPath();ctx.arc(px,py,r+0.4,0,Math.PI*2);ctx.fillStyle=`rgba(224,242,254,${{0.8+pv*.2}})`;ctx.fill();}}else{{ctx.beginPath();ctx.arc(px,py,r,0,Math.PI*2);ctx.fillStyle=`rgba(56,189,248,${{(0.24+pv*.3)*s}})`;ctx.fill();}}}});
  particles.forEach(p=>{{p.u+=p.spd;}});
  if(frame%10===0){{fcEl.textContent=String(Math.floor((Math.sin(ft)*.5+.5)*86)).padStart(2,'0');aicEl.textContent=(93.5+Math.sin(ft*.7)*2.1).toFixed(1)+'%';}}
  requestAnimationFrame(draw);
}}
draw();
function showScreen(id){{document.querySelectorAll('.screen').forEach(s=>{{s.classList.remove('visible');s.classList.add('hidden');}});document.getElementById(id).classList.remove('hidden');document.getElementById(id).classList.add('visible');}}
setTimeout(()=>showScreen('screen-bio'),3200);
setTimeout(()=>{{showScreen('screen-main');document.getElementById('ctaBtn').classList.add('show');}},6800);
function triggerStart(){{const btns=window.parent.document.querySelectorAll('div[data-testid="stButton"] > button');btns.forEach(b=>{{if(b.innerText.includes('MULAI BELAJAR')||b.innerText.includes('START LEARNING'))b.click();}});}}
(function(){{const img=new Image();img.onload=function(){{const ph=document.getElementById('bioPhoto');ph.textContent='';const i=document.createElement('img');i.src='assets/foto.jpg';i.alt='Dev';ph.appendChild(i);}};img.src='assets/foto.jpg';}})();
</script>
</body>
</html>
"""

NAVBAR_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Share+Tech+Mono&display=swap');
.block-container{padding-top:0.4rem !important;padding-bottom:0 !important;}
div[data-testid="stHorizontalBlock"]{
  background:rgba(2,6,23,0.97) !important;
  backdrop-filter:blur(20px);
  padding:8px 28px !important;
  gap:6px;
  border-bottom:1px solid rgba(56,189,248,0.12) !important;
}
div[data-testid="stHorizontalBlock"] button{
  background:transparent !important;
  border:1px solid rgba(56,189,248,0.15) !important;
  color:rgba(100,116,139,0.8) !important;
  font-family:'Share Tech Mono',monospace !important;
  font-size:0.76rem !important;
  border-radius:8px !important;
  padding:7px 14px !important;
  letter-spacing:0.08em !important;
  text-transform:uppercase !important;
}
div[data-testid="stHorizontalBlock"] button:hover{
  border-color:rgba(56,189,248,0.5) !important;
  color:#38bdf8 !important;
  box-shadow:0 0 12px rgba(56,189,248,0.1) !important;
}
div[data-testid="stHorizontalBlock"] button[kind="primary"]{
  background:rgba(56,189,248,0.06) !important;
  border:1px solid rgba(56,189,248,0.45) !important;
  color:#38bdf8 !important;
  box-shadow:none !important;
}
div[data-testid="stHorizontalBlock"] button p,
div[data-testid="stHorizontalBlock"] button span{
  color:inherit !important;
  font-family:'Share Tech Mono',monospace !important;
  font-size:0.76rem !important;
  letter-spacing:0.08em !important;
}
</style>"""

def md_to_html(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    text = text.replace('\n', '<br>')
    return text

def detect_quiz_request(text):
    keywords = ["quiz", "soal", "latihan soal", "buat soal", "buatkan soal", "generate quiz", "buatkan quiz", "buat quiz"]
    return any(k in text.lower() for k in keywords)

def detect_level(text):
    t = text.lower()
    if any(k in t for k in ["mudah", "easy", "gampang"]): return "Mudah"
    if any(k in t for k in ["sedang", "medium", "menengah"]): return "Sedang"
    if any(k in t for k in ["sulit", "susah", "hard", "difficult"]): return "Sulit"
    return None

def extract_topic(text):
    tl = text.lower()
    patterns = [
        r"quiz\s+(?:tentang|about|mengenai)?\s*(.+?)(?:\s+level|\s+tingkat|\s+mudah|\s+sedang|\s+sulit|$)",
        r"soal\s+(?:tentang|about|mengenai)?\s*(.+?)(?:\s+level|\s+tingkat|\s+mudah|\s+sedang|\s+sulit|$)",
        r"(?:tentang|about|mengenai)\s+(.+?)(?:\s+level|\s+tingkat|\s+mudah|\s+sedang|\s+sulit|$)",
    ]
    for p in patterns:
        m = re.search(p, tl)
        if m:
            topic = m.group(1).strip()
            topic = re.sub(r'\b(level|tingkat|buat|buatkan|generate|aku|saya|mau|minta|dong|ya|yuk)\b', '', topic).strip()
            if topic and len(topic) > 1:
                return topic.title()
    return None

# =============================================
# NAVBAR
# =============================================
if ss.menu not in ["Home", "InputNama"]:
    st.markdown(NAVBAR_CSS, unsafe_allow_html=True)
    menus = ["Dashboard", "Chat AI", "Plan Belajar"]
    menu_icons = {"Dashboard": "🏠", "Chat AI": "💬", "Plan Belajar": "📅"}
    menu_labels = {
        "Dashboard": t("dashboard"),
        "Chat AI": t("chat_ai_nav"),
        "Plan Belajar": t("plan_belajar"),
    }
    brand_col, *menu_cols, lang_col, back_col = st.columns([2, 1, 1, 1, 0.7, 0.8])
    with brand_col:
        st.markdown('<div style="padding:8px 0;font-size:1.2rem;font-weight:700;font-family:Orbitron,monospace;color:#f1f5f9;">Learn<span style="color:#38bdf8;">AI</span></div>', unsafe_allow_html=True)
    for i, m in enumerate(menus):
        with menu_cols[i]:
            if st.button(f"{menu_icons[m]} {menu_labels[m]}", key=f"nav_{m}", use_container_width=True,
                         type="primary" if ss.menu == m else "secondary"):
                ss.menu = m; ss.modal_step = 0; st.rerun()
    with lang_col:
        lang_display = "🇬🇧 EN" if ss.get("lang","id") == "en" else "🇮🇩 ID"
        if st.button(lang_display, key="navbar_lang_toggle", use_container_width=True):
            ss.lang = "en" if ss.get("lang","id") == "id" else "id"
            st.rerun()
    with back_col:
        if st.button(t("home_nav"), key="back_home"):
            ss.menu = "Home"; st.rerun()

menu = ss.menu

# =============================================
# HOME
# =============================================
if menu == "Home":
    st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] { display: none !important; }
    .block-container { padding: 0 !important; margin: 0 !important; }
    .stApp { overflow: hidden !important; }
    section[data-testid="stAppViewContainer"] { padding: 0 !important; }
    div[data-testid="stVerticalBlock"] { gap: 0 !important; padding: 0 !important; }
    iframe { width: 100vw !important; height: 100vh !important; position: fixed !important; top: 0 !important; left: 0 !important; border: none !important; z-index: 1 !important; }
    div[data-testid="stButton"] { position: fixed !important; bottom: 60px !important; left: 50% !important; transform: translateX(-50%) !important; z-index: 9999 !important; width: auto !important; display: none !important; }
    </style>
    """, unsafe_allow_html=True)
    col_lang_filler, col_lang_btn = st.columns([8, 1])
    with col_lang_btn:
        lang_display_home = "🇬🇧 EN" if ss.get("lang","id") == "en" else "🇮🇩 ID"
        if st.button(lang_display_home, key="home_lang_toggle"):
            ss.lang = "en" if ss.get("lang", "id") == "id" else "id"
            st.rerun()
    components.html(get_home_html(), height=800, scrolling=False)
    if st.button(t("home_start"), key="home_cta"):
        ss.menu = "InputNama"; st.rerun()

# =============================================
# INPUT NAMA
# =============================================
elif menu == "InputNama":
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
    .block-container { padding: 0 !important; max-width: 100% !important; margin: 0 !important; }
    section[data-testid="stAppViewContainer"] { padding: 0 !important; }
    header[data-testid="stHeader"] { display: none !important; }
    div[data-testid="stVerticalBlock"] > div { gap: 0 !important; }
    .stApp {
        background: #020617 !important;
        background-image:
            radial-gradient(1px 1px at 18% 28%, rgba(255,255,255,0.5) 0%, transparent 100%),
            radial-gradient(1px 1px at 58% 14%, rgba(255,255,255,0.38) 0%, transparent 100%),
            radial-gradient(1.5px 1.5px at 78% 58%, rgba(255,255,255,0.45) 0%, transparent 100%),
            radial-gradient(1px 1px at 8% 68%, rgba(255,255,255,0.32) 0%, transparent 100%),
            radial-gradient(1px 1px at 42% 78%, rgba(255,255,255,0.38) 0%, transparent 100%),
            radial-gradient(1.5px 1.5px at 88% 38%, rgba(56,189,248,0.28) 0%, transparent 100%),
            radial-gradient(1px 1px at 32% 48%, rgba(255,255,255,0.28) 0%, transparent 100%),
            radial-gradient(2px 2px at 68% 82%, rgba(56,189,248,0.22) 0%, transparent 100%),
            radial-gradient(1px 1px at 52% 42%, rgba(255,255,255,0.42) 0%, transparent 100%) !important;
    }
    div[data-testid="stTextInputRootElement"] {
        background: rgba(2,8,30,0.75) !important;
        border: 1px solid rgba(56,189,248,0.28) !important;
        border-radius: 10px !important;
        margin-bottom: 16px !important;
    }
    div[data-testid="stTextInputRootElement"]:focus-within {
        border-color: rgba(56,189,248,0.65) !important;
        box-shadow: 0 0 16px rgba(56,189,248,0.12) !important;
    }
    div[data-testid="stTextInputRootElement"] > div { background: transparent !important; border: none !important; box-shadow: none !important; }
    div[data-testid="stTextInputRootElement"] input {
        background: transparent !important; color: #f1f5f9 !important;
        font-family: 'Share Tech Mono', monospace !important; font-size: 14px !important;
        text-align: center !important; letter-spacing: 0.08em !important;
        border: none !important; box-shadow: none !important; padding: 14px 18px !important;
    }
    div[data-testid="stTextInputRootElement"] input::placeholder {
        color: rgba(56,189,248,0.28) !important;
        font-family: 'Share Tech Mono', monospace !important;
    }
    div[data-testid="stButton"] button {
        width: 100% !important; padding: 13px 20px !important;
        background: rgba(56,189,248,0.06) !important;
        border: 1px solid rgba(56,189,248,0.55) !important;
        color: #38bdf8 !important; font-family: 'Share Tech Mono', monospace !important;
        font-size: 11px !important; letter-spacing: 0.22em !important;
        cursor: pointer !important; border-radius: 12px !important;
        text-transform: uppercase !important;
        transition: all .2s !important;
    }
    div[data-testid="stButton"] button:hover {
        background: rgba(56,189,248,0.12) !important;
        box-shadow: 0 0 22px rgba(56,189,248,0.18) !important;
        color: #e0f2fe !important;
    }
    div[data-testid="stButton"] button p, div[data-testid="stButton"] button span {
        color: inherit !important; font-family: 'Share Tech Mono', monospace !important;
        font-size: 11px !important; letter-spacing: 0.22em !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_lang_f2, col_lang_b2 = st.columns([8, 1])
    with col_lang_b2:
        lang_display_input = "🇬🇧 EN" if ss.get("lang","id") == "en" else "🇮🇩 ID"
        if st.button(lang_display_input, key="inputnama_lang_toggle"):
            ss.lang = "en" if ss.get("lang", "id") == "id" else "id"
            st.rerun()

    _, col_mid, _ = st.columns([1, 1.1, 1])
    with col_mid:
        st.markdown(f'''
        <div style="padding-top:26vh;">
            <div style="font-family:'Share Tech Mono',monospace;font-size:9px;color:rgba(56,189,248,0.45);letter-spacing:0.42em;text-transform:uppercase;text-align:center;margin-bottom:18px;">// initialize user</div>
            <div style="font-family:'Orbitron',monospace;font-size:2.6rem;font-weight:900;color:#f1f5f9;text-align:center;margin-bottom:4px;text-shadow:0 0 28px rgba(56,189,248,0.22);">Learn<span style="color:#38bdf8;">AI</span></div>
            <div style="width:44px;height:1px;background:linear-gradient(90deg,transparent,rgba(56,189,248,0.55),transparent);margin:14px auto 20px;"></div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:12px;color:rgba(148,163,184,0.5);letter-spacing:0.14em;text-align:center;margin-bottom:22px;">{t("home_name_hint")}</div>
        </div>
        ''', unsafe_allow_html=True)

        nama_input = st.text_input("Nama", placeholder=t("home_name_placeholder"), key="input_nama_field", label_visibility="collapsed")

        if st.button(t("home_start"), key="confirm_nama", use_container_width=True):
            raw = ss.get("input_nama_field", "").strip()
            if not raw:
                st.warning(t("home_name_warn"))
            else:
                ss.sessions = []; ss.chat_messages = []; ss.chat_conversations = []
                ss.active_conversation_id = None; ss.active_session = None
                ss.doc_text = ""; ss.doc_name = ""; ss.plan_data = []
                ss.plan_generated = False; ss.waiting_for_topic = False
                ss.pending_quiz_topic = ""; ss.total_questions = 0
                ss.total_quizzes = 0; ss.total_docs = 0
                ss.material_view = "list"; ss.active_chapter = 0
                ss.active_material = 0; ss.user_id = None
                ss.user_name = raw
                uid = get_or_create_user(raw)
                ss.user_id = uid
                ss.sessions = get_user_sessions(uid)
                ss.chat_conversations = db_load_chat_history(uid)
                if ss.chat_conversations:
                    ss.active_conversation_id = ss.chat_conversations[0]["id"]
                    ss.chat_messages = list(ss.chat_conversations[0].get("messages", []))
                else:
                    new_conversation()
                ss.menu = "Plan Belajar"
                st.rerun()

# =============================================
# DASHBOARD
# =============================================
elif menu == "Dashboard":
    import datetime, random
    active_idx  = ss.get("active_session", None)
    active_sess = ss.sessions[active_idx] if (active_idx is not None and active_idx < len(ss.sessions)) else None

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Share+Tech+Mono&family=DM+Sans:wght@300;400;500&display=swap');
    .block-container { padding: 28px 40px !important; }
    .stApp { background: #020617 !important; }
    .la-card { background: #0f172a; border: 1px solid rgba(56,189,248,0.12); border-radius: 12px; padding: 20px 22px; margin-bottom: 16px; }
    .la-card-label { font-family: 'Share Tech Mono', monospace; font-size: 9px; font-weight: 600; letter-spacing: 0.15em; text-transform: uppercase; color: #38bdf8 !important; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; }
    .la-card-label::after { content: ''; flex: 1; height: 1px; background: rgba(56,189,248,0.12); }
    .target-item { display:flex; align-items:flex-start; gap:10px; padding:6px 0; font-size:13px; color:#e2e8f0 !important; }
    .target-dot { width:6px; height:6px; border-radius:50%; background:#6366f1; flex-shrink:0; margin-top:5px; }
    .pa-text { font-size:13px; color:#cbd5e1 !important; line-height:1.75; }
    .status-badge { display:inline-flex; align-items:center; gap:6px; padding:5px 14px; border-radius:8px; font-size:11px; font-weight:600; background:rgba(16,185,129,0.1); color:#10b981; border:1px solid rgba(16,185,129,0.25); font-family:'Share Tech Mono',monospace; letter-spacing:0.08em; margin-top:8px; }
    .status-badge.behind { background:rgba(245,158,11,0.1); color:#f59e0b; border:1px solid rgba(245,158,11,0.25); }
    .status-msg { font-size:10px; color:rgba(100,116,139,0.8) !important; margin-top:8px; line-height:1.5; font-family:'Share Tech Mono',monospace; }
    .qh-wrap { background:#0f172a; border:1px solid rgba(56,189,248,0.12); border-radius:12px; padding:20px 22px; }
    .qh-title { font-size:13px; font-weight:700; color:#f1f5f9 !important; font-family:'Orbitron',monospace; letter-spacing:0.04em; }
    .qh-count { font-size:10px; color:rgba(56,189,248,0.4) !important; font-family:'Share Tech Mono',monospace; letter-spacing:0.1em; }
    .qh-table { width:100%; border-collapse:collapse; font-size:12px; }
    .qh-table th { font-size:9px; font-weight:500; color:#38bdf8 !important; text-align:left; padding:8px 12px; border-bottom:1px solid rgba(56,189,248,0.1); text-transform:uppercase; letter-spacing:0.12em; font-family:'Share Tech Mono',monospace; }
    .qh-table td { padding:12px 12px; border-bottom:1px solid rgba(56,189,248,0.05); color:#cbd5e1 !important; font-size:12px; vertical-align:middle; }
    .qh-table tr:hover td { background: rgba(56,189,248,0.03); }
    .score-chip { display:inline-block; padding:3px 10px; border-radius:6px; font-size:11px; font-weight:700; font-family:'Share Tech Mono',monospace; }
    .level-chip { display:inline-block; padding:3px 10px; border-radius:6px; font-size:11px; font-weight:500; font-family:'Share Tech Mono',monospace; }
    .dsb-title { font-family:'Orbitron',monospace; font-size:1.25rem; font-weight:700; color:#f1f5f9 !important; margin-bottom:3px; letter-spacing:0.03em; }
    .dsb-sub { font-size:11px; color:rgba(56,189,248,0.45) !important; margin-bottom:22px; font-family:'Share Tech Mono',monospace; letter-spacing:0.1em; }
    .dsb-divider { border:none; border-top:1px solid rgba(56,189,248,0.1); margin:4px 0 18px; }
    .streak-fire { font-size:1.2rem; letter-spacing:2px; margin-top:6px; }
    div[data-testid="stButton"] button { background: rgba(56,189,248,0.05) !important; border: 1px solid rgba(56,189,248,0.3) !important; color: #38bdf8 !important; font-family: 'Share Tech Mono', monospace !important; font-size: 11px !important; letter-spacing: 0.1em !important; border-radius: 8px !important; text-transform: uppercase !important; }
    div[data-testid="stButton"] button:hover { background: rgba(56,189,248,0.12) !important; border-color: rgba(56,189,248,0.6) !important; color: #e0f2fe !important; }
    div[data-testid="stButton"] button[kind="primary"] { background: #4f46e5 !important; border-color: #6366f1 !important; color: #fff !important; }
    div[data-testid="stButton"] button[kind="primary"]:hover { background: #4338ca !important; }
    div[data-testid="stButton"] button p, div[data-testid="stButton"] button span { color: inherit !important; font-family: 'Share Tech Mono', monospace !important; font-size: 11px !important; letter-spacing: 0.1em !important; }
    </style>
    """, unsafe_allow_html=True)

    if not active_sess:
        st.markdown("""<div style="text-align:center;padding:80px 20px;">
            <div style="font-family:'Orbitron',monospace;font-size:3rem;color:rgba(56,189,248,0.15);margin-bottom:16px;">[ 📚 ]</div>
            <div style="font-family:'Orbitron',monospace;font-size:1rem;font-weight:700;color:#f1f5f9;margin-bottom:8px;">Belum ada session aktif</div>
            <div style="font-size:12px;color:rgba(56,189,248,0.35);font-family:'Share Tech Mono',monospace;letter-spacing:0.08em;">// Buka Plan Belajar, buat session, lalu klik ▶ untuk mulai.</div>
        </div>""", unsafe_allow_html=True)
        if st.button("→ Ke Plan Belajar", type="primary"):
            ss.menu = "Plan Belajar"; st.rerun()
        st.stop()

    sess_name=active_sess["name"]; sess_topics=active_sess["topics"]; sess_level=active_sess["level"]
    sess_deadline=active_sess.get("deadline",""); chapters=active_sess.get("chapters",[])
    quiz_history=active_sess.get("quiz_history",[]); progress=active_sess.get("progress",0)
    undone_mats=[(c,m) for c in chapters for m in c.get("materials",[]) if not m.get("done")]
    today_targets=undone_mats[:2]; streak=active_sess.get("streak",3)
    avg_score=int(sum(q["score"] for q in quiz_history)/len(quiz_history)) if quiz_history else 0
    ahead=progress>=50 or avg_score>=70

    deadline_html=f'<span style="font-size:11px;color:#f59e0b;margin-left:12px;font-family:\'Share Tech Mono\',monospace;border:1px solid rgba(245,158,11,0.3);background:rgba(245,158,11,0.08);padding:2px 8px;border-radius:6px;">⏱ DEADLINE: {sess_deadline}</span>' if sess_deadline else ''
    st.markdown(f'<div class="dsb-title">{t("dsb_title_prefix")} {deadline_html}</div><div class="dsb-sub">// WS: {sess_name} &nbsp;·&nbsp; {sess_topics} &nbsp;·&nbsp; Level {sess_level}</div><hr class="dsb-divider">', unsafe_allow_html=True)

    r1a, r1b = st.columns([1,1])
    with r1a:
        today_str = datetime.date.today().strftime("%d %b %Y")
        targets_html = ""
        if today_targets:
            for c_obj, m_obj in today_targets:
                try:
                    c_title = c_obj.get('title','') if isinstance(c_obj,dict) else ''
                    m_title = m_obj.get('title','') if isinstance(m_obj,dict) else ''
                    m_type  = m_obj.get('type','')  if isinstance(m_obj,dict) else ''
                    icon = '<span style="color:rgba(99,102,241,0.7);font-family:\'Share Tech Mono\',monospace;font-size:9px;background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.2);padding:1px 6px;border-radius:4px;">QUIZ</span>' if m_type=="quiz" else '<span style="color:rgba(56,189,248,0.7);font-family:\'Share Tech Mono\',monospace;font-size:9px;background:rgba(56,189,248,0.08);border:1px solid rgba(56,189,248,0.18);padding:1px 6px;border-radius:4px;">READ</span>'
                    targets_html += f'<div class="target-item"><div class="target-dot"></div><div>{icon} &nbsp;<strong style="color:#e2e8f0;">{c_title}</strong><div style="color:rgba(100,116,139,0.7);font-size:11px;margin-top:2px;margin-left:2px;">{m_title}</div></div></div>'
                except: pass
        else:
            targets_html = '<div class="target-item" style="color:#10b981;font-family:\'Share Tech Mono\',monospace;font-size:11px;">✓ SEMUA MATERI SELESAI DIKERJAKAN!</div>'
        st.markdown(f'<div class="la-card"><div class="la-card-label">Target Hari Ini &nbsp;·&nbsp; {today_str}</div>{targets_html}</div>', unsafe_allow_html=True)

    with r1b:
        pa_key = f"pa_{active_idx}_{cur_lang()}"
        if pa_key not in ss:
            if quiz_history:
                scores_info = ", ".join([f"{q['topic']} ({q['score']}%)" for q in quiz_history[-3:]])
                if cur_lang() == "en":
                    pa_prompt = f'As a learning counselor, give a brief 2-3 sentence analysis in English. Quiz data: {scores_info}. Mention strengths and improvement tips for "{sess_topics}" at "{sess_level}" level.'
                    pa_fallback = f"Great dedication! Keep studying {sess_topics}."
                else:
                    pa_prompt = f'Sebagai konsilor belajar, berikan analisis singkat (2-3 kalimat). Data kuis: {scores_info}. Kekuatan dan saran untuk topik "{sess_topics}" level "{sess_level}".'
                    pa_fallback = f"Semangat belajarmu luar biasa! Terus tingkatkan pada topik {sess_topics}."
                try: pa_text = ask_ai(pa_prompt, lang=cur_lang())
                except: pa_text = pa_fallback
            else:
                pa_text = "Complete quizzes to get AI analysis!" if cur_lang()=="en" else "Selesaikan kuis untuk mendapatkan analisis AI!"
            ss[pa_key] = pa_text
        st.markdown(f'<div class="la-card"><div class="la-card-label">Analisis Diagnostik Progres</div><div class="pa-text">{ss[pa_key]}</div></div>', unsafe_allow_html=True)

    r2a, r2b, r2c = st.columns([1,1,1])
    with r2a:
        fire = "🔥" * min(streak, 5)
        st.markdown(f'''<div class="la-card">
            <div class="la-card-label">Keaktifan Beruntun</div>
            <div style="display:flex;align-items:baseline;gap:6px;">
                <div style="font-family:'Orbitron',monospace;font-size:2.4rem;font-weight:700;color:#f1f5f9;line-height:1;">{streak}</div>
                <div style="font-size:12px;color:rgba(100,116,139,0.6);font-family:'Share Tech Mono',monospace;">hari</div>
            </div>
            <div class="streak-fire">{fire if streak>0 else '<span style="font-size:11px;font-family:Share Tech Mono,monospace;color:rgba(100,116,139,0.5);">// Mulai petualangan belajarmu!</span>'}</div>
        </div>''', unsafe_allow_html=True)

    with r2b:
        sc = "#10b981" if avg_score>=80 else "#f59e0b" if avg_score>=60 else "#ef4444"
        sc_bg = "rgba(16,185,129,0.1)" if avg_score>=80 else "rgba(245,158,11,0.1)" if avg_score>=60 else "rgba(239,68,68,0.1)"
        sc_brd = "rgba(16,185,129,0.3)" if avg_score>=80 else "rgba(245,158,11,0.3)" if avg_score>=60 else "rgba(239,68,68,0.3)"
        perf_label = "✓ Excellent Perform" if avg_score>=80 else "⚡ Keep Practicing"
        C = 2*3.14159*30; parc = (avg_score/100)*C if avg_score else 0
        st.markdown(f'''<div class="la-card">
            <div class="la-card-label">Rata-Rata Nilai Kuis</div>
            <div style="display:flex;align-items:center;gap:18px;">
                <svg width="72" height="72" viewBox="0 0 72 72">
                    <circle cx="36" cy="36" r="30" fill="none" stroke="rgba(56,189,248,0.1)" stroke-width="6"/>
                    <circle cx="36" cy="36" r="30" fill="none" stroke="{sc}" stroke-width="6"
                        stroke-dasharray="{parc:.1f} {C:.1f}" stroke-linecap="round" transform="rotate(-90 36 36)"/>
                    <text x="36" y="41" text-anchor="middle" font-size="13" font-weight="700" fill="{sc}" font-family="monospace">{avg_score if avg_score else "—"}</text>
                </svg>
                <div>
                    <div style="display:flex;align-items:baseline;gap:4px;">
                        <span style="font-family:'Orbitron',monospace;font-size:2rem;font-weight:700;color:{sc};line-height:1;">{avg_score if avg_score else "—"}</span>
                        <span style="font-size:12px;color:rgba(100,116,139,0.5);font-family:'Share Tech Mono',monospace;">/100</span>
                    </div>
                    <div style="font-size:10px;color:rgba(100,116,139,0.6);font-family:'Share Tech Mono',monospace;margin-top:2px;">{len(quiz_history)} kuis selesai</div>
                    {"" if not quiz_history else f'<div style="display:inline-flex;align-items:center;gap:5px;margin-top:8px;background:{sc_bg};border:1px solid {sc_brd};color:{sc};font-size:10px;padding:4px 10px;border-radius:6px;font-family:\'Share Tech Mono\',monospace;">{perf_label}</div>'}
                ''', unsafe_allow_html=True)

    with r2c:
        bc = "status-badge" if ahead else "status-badge behind"
        bl2 = "SUDAH MELEBIHI TARGET" if ahead else "BELUM MENCAPAI TARGET"
        bi2 = "✓" if ahead else "⚠"
        sm = "// Performa belajar Anda sangat baik dan sesuai target." if ahead else "// Tingkatkan keaktifan membaca materi untuk mengejar target."
        st.markdown(f'''<div class="la-card">
            <div class="la-card-label">Status Kelulusan Belajar</div>
            <div class="{bc}">{bi2} &nbsp;{bl2}</div>
            <div class="status-msg">{sm}</div>
        </div>''', unsafe_allow_html=True)

    st.markdown(f'<div class="qh-wrap"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;border-bottom:1px solid rgba(56,189,248,0.08);padding-bottom:10px;"><div class="qh-title">📊 Riwayat Hasil Kuis</div><div class="qh-count">// {len(quiz_history)} EVALUATIONS RECORDED</div></div>', unsafe_allow_html=True)
    if quiz_history:
        rows_html = ""
        for qh in quiz_history:
            sc=qh["score"]; sc_color="#10b981" if sc>=80 else "#f59e0b" if sc>=60 else "#ef4444"
            sc_bg="rgba(16,185,129,0.1)" if sc>=80 else "rgba(245,158,11,0.1)" if sc>=60 else "rgba(239,68,68,0.1)"
            sc_brd="rgba(16,185,129,0.25)" if sc>=80 else "rgba(245,158,11,0.25)" if sc>=60 else "rgba(239,68,68,0.25)"
            lv=qh.get("level","—")
            lv_color="#10b981" if lv=="Mudah" else "#38bdf8" if lv in ["Sedang","Intermediate","Beginner"] else "#ef4444"
            lv_bg="rgba(16,185,129,0.08)" if lv=="Mudah" else "rgba(56,189,248,0.08)" if lv in ["Sedang","Intermediate","Beginner"] else "rgba(239,68,68,0.08)"
            lv_brd="rgba(16,185,129,0.2)" if lv=="Mudah" else "rgba(56,189,248,0.2)" if lv in ["Sedang","Intermediate","Beginner"] else "rgba(239,68,68,0.2)"
            rh = f'<br><span style="font-size:9px;color:rgba(56,189,248,0.35);">(retry)</span>' if qh.get("retry") else ""
            rows_html += f'<tr><td style="color:#e2e8f0;font-weight:500;">{qh["topic"]}</td><td><span class="level-chip" style="background:{lv_bg};color:{lv_color};border:1px solid {lv_brd};">{lv}</span></td><td><span class="score-chip" style="background:{sc_bg};color:{sc_color};border:1px solid {sc_brd};">{sc}%{rh}</span></td><td style="color:rgba(100,116,139,0.7);font-size:11px;line-height:1.65;">{qh.get("analysis","—")}</td></tr>'
        st.markdown(f'<table class="qh-table"><thead><tr><th>{t("dsb_col_topic")}</th><th>{t("dsb_col_level")}</th><th>{t("dsb_col_score")}</th><th>{t("dsb_col_diag")}</th></tr></thead><tbody>{rows_html}</tbody></table>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:center;padding:32px 0;color:rgba(56,189,248,0.2);font-size:11px;font-family:\'Share Tech Mono\',monospace;letter-spacing:0.1em;">// BELUM ADA QUIZ — MULAI BELAJAR UNTUK MELIHAT RIWAYAT</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =============================================
# CHAT AI
# =============================================
elif menu == "Chat AI":
    if not ss.chat_conversations:
        new_conversation()
    elif not ss.active_conversation_id:
        ss.active_conversation_id = ss.chat_conversations[0]["id"]
        ss.chat_messages = ss.chat_conversations[0].get("messages", [])

    with st.sidebar:
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
        [data-testid="stSidebar"] { background: #0f0f23 !important; border-right: 1px solid rgba(99,102,241,0.15) !important; min-width: 260px !important; max-width: 280px !important; }
        [data-testid="stSidebar"] > div { padding: 0 !important; }
        [data-testid="stSidebar"] div[data-testid="stButton"] button { background: linear-gradient(135deg, #4f46e5, #7c3aed) !important; border: none !important; color: #fff !important; font-family: 'Inter', sans-serif !important; font-size: 13px !important; font-weight: 500 !important; letter-spacing: 0 !important; border-radius: 10px !important; padding: 10px 14px !important; width: 100% !important; text-transform: none !important; }
        [data-testid="stSidebar"] div[data-testid="stButton"] button:hover { background: linear-gradient(135deg, #4338ca, #6d28d9) !important; box-shadow: 0 4px 15px rgba(99,102,241,0.35) !important; }
        [data-testid="stSidebar"] div[data-testid="stButton"] button p, [data-testid="stSidebar"] div[data-testid="stButton"] button span { color: #fff !important; font-family: 'Inter', sans-serif !important; font-size: 13px !important; letter-spacing: 0 !important; text-transform: none !important; }
        [data-testid="stSidebar"] hr { border-color: rgba(99,102,241,0.12) !important; margin: 10px 0 !important; }
        [data-testid="stSidebarCollapseButton"] { display: none !important; }
        button[data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"][aria-expanded="false"] { display: flex !important; transform: none !important; min-width: 260px !important; }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('''
        <div style="padding:20px 16px 14px;display:flex;align-items:center;gap:10px;">
            <div style="width:28px;height:28px;background:linear-gradient(135deg,#4f46e5,#7c3aed);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;color:white;flex-shrink:0;">✦</div>
            <div style="font-family:'Orbitron',monospace;font-size:14px;font-weight:700;color:#e0d9f5;letter-spacing:0.04em;">Learn<span style="color:#818cf8;">AI</span></div>
        </div>
        ''', unsafe_allow_html=True)

        if st.button(t("new_chat"), key="sidebar_new_chat", use_container_width=True):
            sync_messages_to_conv()
            new_conversation(); st.rerun()

        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-family:\'Inter\',sans-serif;font-size:11px;color:rgba(165,148,210,0.45);letter-spacing:0.05em;text-transform:uppercase;padding:4px 16px 8px;font-weight:500;">{t("chat_history_label")}</div>', unsafe_allow_html=True)

        st.markdown("""
        <style>
        [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] { background: transparent !important; border: none !important; padding: 0 8px !important; gap: 4px !important; margin-bottom: 2px !important; align-items: center !important; }
        [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button { border-radius: 10px !important; font-size: 13px !important; letter-spacing: 0 !important; text-transform: none !important; }
        [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button[kind="secondary"] { background: transparent !important; border: 1px solid transparent !important; color: rgba(200,188,240,0.7) !important; font-family: 'Inter', sans-serif !important; padding: 8px 10px !important; }
        [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button[kind="secondary"]:hover { background: rgba(99,102,241,0.1) !important; border-color: rgba(99,102,241,0.25) !important; color: #e0d9f5 !important; }
        [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button[kind="primary"] { background: rgba(79,70,229,0.18) !important; color: #e0d9f5 !important; border: 1px solid rgba(99,102,241,0.35) !important; font-family: 'Inter', sans-serif !important; padding: 8px 10px !important; }
        [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button p, [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button span { color: inherit !important; font-family: 'Inter', sans-serif !important; font-size: 13px !important; letter-spacing: 0 !important; text-transform: none !important; }
        [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"]:last-child button { background: rgba(239,68,68,0.08) !important; border: 1px solid rgba(239,68,68,0.2) !important; color: rgba(248,113,113,0.8) !important; font-size: 11px !important; font-family: monospace !important; padding: 4px 0 !important; min-height: 28px !important; height: 28px !important; }
        [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"]:last-child button:hover { background: rgba(239,68,68,0.18) !important; }
        </style>
        """, unsafe_allow_html=True)

        if not ss.chat_conversations:
            st.markdown(f'<div style="font-size:12px;color:rgba(165,148,210,0.3);padding:10px 16px;font-family:Inter,sans-serif;">{t("no_history")}</div>', unsafe_allow_html=True)
        else:
            if "delete_conv_id" in ss and ss.delete_conv_id:
                did = ss.delete_conv_id
                ss.chat_conversations = [c for c in ss.chat_conversations if c["id"] != did]
                if ss.active_conversation_id == did:
                    if ss.chat_conversations:
                        ss.active_conversation_id = ss.chat_conversations[0]["id"]
                        ss.chat_messages = ss.chat_conversations[0].get("messages", [])
                    else:
                        new_conversation()
                uid = ss.get("user_id")
                if uid:
                    db_save_chat_history(uid, ss.chat_conversations)
                ss.delete_conv_id = None
                st.rerun()

            for conv in ss.chat_conversations:
                is_active = conv["id"] == ss.active_conversation_id
                title_short = conv["title"][:16] + ("…" if len(conv["title"]) > 16 else "")
                c1, c2 = st.columns([11, 1])
                with c1:
                    if st.button(f"💬 {title_short}", key=f"conv_btn_{conv['id']}", use_container_width=True,
                                 type="primary" if is_active else "secondary"):
                        sync_messages_to_conv()
                        target_id = conv["id"]
                        ss.active_conversation_id = target_id
                        target = next((c for c in ss.chat_conversations if c["id"] == target_id), None)
                        ss.chat_messages = list(target.get("messages", [])) if target else []
                        st.rerun()
                with c2:
                    if st.button("✕", key=f"del_conv_{conv['id']}", help=t("delete_help")):
                        sync_messages_to_conv()
                        ss.delete_conv_id = conv["id"]
                        st.rerun()

        st.markdown('<hr>', unsafe_allow_html=True)
        user_initial = ss.get("user_name", "U")[0].upper()
        user_name_display = ss.get("user_name", "User")
        st.markdown(f'''
        <div style="position:fixed;bottom:0;left:0;width:260px;padding:12px 16px 14px;background:#0f0f23;border-top:1px solid rgba(99,102,241,0.12);border-right:1px solid rgba(99,102,241,0.12);z-index:9999;">
            <div style="display:flex;align-items:center;gap:10px;">
                <div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,rgba(79,70,229,0.4),rgba(124,58,237,0.4));border:1.5px solid rgba(99,102,241,0.5);display:flex;align-items:center;justify-content:center;font-family:Inter,sans-serif;font-size:14px;font-weight:600;color:#c4b5fd;flex-shrink:0;">{user_initial}</div>
                <div style="overflow:hidden;">
                    <div style="font-family:Inter,sans-serif;font-size:12px;font-weight:500;color:#e0d9f5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px;">{user_name_display}</div>
                    <div style="font-family:Inter,sans-serif;font-size:10px;color:rgba(165,148,210,0.45);margin-top:1px;">{t("free_plan")}</div>
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    .stApp { background: #0d0d1f !important; }
    .block-container { padding: 0 !important; }
    .chat-header { padding:18px 32px 14px; border-bottom:1px solid rgba(99,102,241,0.1); background:#0d0d1f; }
    .chat-header-title { font-family:'Orbitron',monospace; font-size:1.05rem; font-weight:700; color:#e0d9f5; }
    .chat-header-title span { color:#818cf8; }
    .chat-header-sub { font-family:'Inter',sans-serif; font-size:11px; color:rgba(148,130,200,0.45); margin-top:3px; }
    .msg-user { display:flex; justify-content:flex-end; margin:10px 32px; }
    .msg-user-bubble { background:rgba(79,70,229,0.15); border:1px solid rgba(99,102,241,0.3); border-radius:18px 18px 4px 18px; padding:12px 18px; max-width:65%; color:#e0d9f5; font-family:'Inter',sans-serif; font-size:0.88rem; line-height:1.6; }
    .msg-ai-wrap { display:flex; gap:10px; margin:10px 32px; align-items:flex-start; }
    .ai-avatar { width:32px; height:32px; border-radius:50%; background:linear-gradient(135deg,rgba(79,70,229,0.3),rgba(124,58,237,0.3)); border:1px solid rgba(99,102,241,0.4); display:flex; align-items:center; justify-content:center; font-size:14px; flex-shrink:0; margin-top:2px; }
    .msg-ai-bubble { background:rgba(15,12,40,0.9); border:1px solid rgba(99,102,241,0.12); border-radius:4px 18px 18px 18px; padding:12px 18px; max-width:78%; color:rgba(210,200,250,0.9); font-family:'Inter',sans-serif; font-size:0.88rem; line-height:1.65; }
    .doc-active { display:flex; align-items:center; gap:8px; padding:6px 14px; background:rgba(79,70,229,0.07); border:1px solid rgba(99,102,241,0.2); border-radius:8px; margin:0 32px 8px; font-family:'Inter',sans-serif; font-size:11px; color:#818cf8; width:fit-content; }
    .welcome-wrap { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:52vh; text-align:center; padding:0 24px; }
    .welcome-star { font-size:2.2rem; margin-bottom:18px; color:#818cf8; filter:drop-shadow(0 0 16px rgba(129,140,248,0.5)); }
    .welcome-greeting { font-family:'Inter',sans-serif; font-size:1.35rem; font-weight:400; color:#e0d9f5; margin-bottom:6px; }
    .welcome-greeting span { color:#818cf8; font-weight:600; }
    .welcome-title { font-family:'Inter',sans-serif; font-size:2.2rem; font-weight:700; color:#f0ebff; margin-bottom:12px; }
    .welcome-sub { font-family:'Inter',sans-serif; font-size:13px; color:rgba(165,148,210,0.5); max-width:400px; line-height:1.65; margin-bottom:28px; }
    .welcome-chips { display:flex; gap:10px; flex-wrap:wrap; justify-content:center; }
    .welcome-chip { padding:9px 20px; background:rgba(15,15,35,0.8); border:1px solid rgba(99,102,241,0.2); border-radius:999px; font-family:'Inter',sans-serif; font-size:12px; font-weight:500; color:rgba(180,165,235,0.8); }
    section[data-testid="stMain"] > div { padding-bottom: 110px !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="chat-header"><div class="chat-header-title">Chat <span>AI</span></div><div class="chat-header-sub">{t("chat_ai_sub")}</div></div>', unsafe_allow_html=True)
    if ss.doc_name:
        doc_active_label = "· active document" if cur_lang() == "en" else "· dokumen aktif"
        st.markdown(f'<div class="doc-active">📄 {ss.doc_name} <span style="color:rgba(99,102,241,0.4);margin-left:6px;">{doc_active_label}</span></div>', unsafe_allow_html=True)

    if not ss.chat_messages:
        user_name = ss.get("user_name", "")
        greeting_name = f", <span>{user_name}</span>" if user_name else ""
        import datetime as _dt
        hr = _dt.datetime.now().hour
        if hr < 11: greeting_word = t("greeting_morning") + " ☀️"
        elif hr < 15: greeting_word = t("greeting_afternoon") + " 🌤️"
        elif hr < 18: greeting_word = (t("greeting_evening") if ss.get("lang","id")=="en" else "Selamat Sore") + " 🌅"
        else: greeting_word = t("greeting_evening") + " 🌙"
        st.markdown(f"""
        <div class="welcome-wrap">
            <div class="welcome-star">✦</div>
            <div class="welcome-greeting">{greeting_word}{greeting_name}</div>
            <div class="welcome-title">{t("how_help")}</div>
            <div class="welcome-sub">{t("how_help_sub")}</div>
            <div class="welcome-chips">
                <div class="welcome-chip">💬 &nbsp;{t("btn_talk")}</div>
                <div class="welcome-chip">🙋 &nbsp;{t("btn_help")}</div>
                <div class="welcome-chip">📚 &nbsp;{t("btn_teach")}</div>
                <div class="welcome-chip">📊 &nbsp;{t("btn_analyse")}</div>
                <div class="welcome-chip">✍️ &nbsp;{t("btn_story")}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    for i, msg in enumerate(ss.chat_messages):
        role=msg["role"]; mtype=msg.get("type","text"); content=msg.get("content","")
        if role=="user":
            doc_html=f'<div style="font-size:10px;color:rgba(129,140,248,0.6);margin-bottom:4px;">📄 {msg["doc_name"]}</div>' if msg.get("doc_name") else ""
            st.markdown(f'<div class="msg-user"><div class="msg-user-bubble">{doc_html}{content}</div></div>',unsafe_allow_html=True)
        elif role=="assistant":
            if mtype=="text":
                if content.startswith("⏳"):
                    st.markdown(f'<div class="msg-ai-wrap"><div class="ai-avatar">🤖</div><div class="msg-ai-bubble" style="color:rgba(129,140,248,0.6);">{content}</div></div>',unsafe_allow_html=True)
                    with st.spinner(""):
                        try:
                            user_q=""
                            for m in reversed(ss.chat_messages[:i]):
                                if m["role"]=="user": user_q=m["content"]; break
                            is_doc_msg = "dokumen" in content or "document" in content or "Searching document" in content
                            if is_doc_msg and ss.doc_text: ans=ask_from_document(ss.doc_text, user_q, lang=cur_lang())
                            elif is_doc_msg and not ss.doc_text: ans="❌ Document not found." if cur_lang()=="en" else "❌ Dokumen tidak ditemukan."
                            else: ans=ask_ai(user_q, lang=cur_lang())
                            ss.chat_messages[i]["content"]=ans; sync_messages_to_conv(); st.rerun()
                        except Exception as e:
                            ss.chat_messages[i]["content"]=f"❌ {e}"; st.rerun()
                else:
                    st.markdown(f'<div class="msg-ai-wrap"><div class="ai-avatar">🤖</div><div class="msg-ai-bubble">{md_to_html(content)}</div></div>',unsafe_allow_html=True)
            elif mtype=="level_select":
                topic=msg.get("topic","")
                st.markdown(f'<div class="msg-ai-wrap"><div class="ai-avatar">🤖</div><div class="msg-ai-bubble">{content}<br><br>',unsafe_allow_html=True)
                lc1,lc2,lc3,lc4=st.columns([3,1,1,1])
                with lc2:
                    if st.button("🟢 Mudah",key=f"lv_e_{i}"):
                        ss.chat_messages.append({"role":"user","content":"Level: Mudah"})
                        ss.chat_messages.append({"role":"assistant","type":"generating","content":f"Membuat quiz <b>{topic}</b> level Mudah...","topic":topic,"level":"Mudah"}); st.rerun()
                with lc3:
                    if st.button("🟡 Sedang",key=f"lv_m_{i}"):
                        ss.chat_messages.append({"role":"user","content":"Level: Sedang"})
                        ss.chat_messages.append({"role":"assistant","type":"generating","content":f"Membuat quiz <b>{topic}</b> level Sedang...","topic":topic,"level":"Sedang"}); st.rerun()
                with lc4:
                    if st.button("🔴 Sulit",key=f"lv_h_{i}"):
                        ss.chat_messages.append({"role":"user","content":"Level: Sulit"})
                        ss.chat_messages.append({"role":"assistant","type":"generating","content":f"Membuat quiz <b>{topic}</b> level Sulit...","topic":topic,"level":"Sulit"}); st.rerun()
                st.markdown('</div></div>',unsafe_allow_html=True)
            elif mtype=="generating":
                topic=msg.get("topic",ss.pending_quiz_topic); level=msg.get("level","Sedang")
                st.markdown(f'<div class="msg-ai-wrap"><div class="ai-avatar">🤖</div><div class="msg-ai-bubble" style="color:rgba(129,140,248,0.6);">⏳ {content}</div></div>',unsafe_allow_html=True)
                with st.spinner(""):
                    try:
                        raw=generate_quiz(topic,level,lang=cur_lang()) or ""
                        raw=raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                        if not raw: raise Exception("AI mengembalikan respons kosong. Coba lagi.")
                        questions=json.loads(raw); ss.chat_messages.pop()
                        ss.chat_messages.append({"role":"assistant","type":"quiz","content":"","data":{"questions":questions,"topic":topic,"level":level}})
                        ss.total_quizzes+=1; ss.pending_quiz_topic=""; sync_messages_to_conv(); st.rerun()
                    except Exception as e:
                        ss.chat_messages.pop(); ss.chat_messages.append({"role":"assistant","type":"text","content":f"❌ Gagal membuat quiz: {e}"}); st.rerun()
            elif mtype=="quiz":
                quiz_data=msg.get("data",{}); questions=quiz_data.get("questions",[]); topic=quiz_data.get("topic","Quiz"); level=quiz_data.get("level","Sedang"); total=len(questions); qkey=f"qs_{i}"
                if qkey not in ss: ss[qkey]={"idx":0,"answers":{},"submitted":False,"time":60*total}
                qs=ss[qkey]; idx=min(qs["idx"],total-1); q=questions[idx]; opts=q["options"]; correct=q.get("answer",0)
                answered=len(qs["answers"]); labels=["A","B","C","D"]; pct=int(answered/total*100) if total else 0
                level_color={"Mudah":"#10b981","Sedang":"#f59e0b","Sulit":"#ef4444"}.get(level,"#818cf8")
                st.markdown(f'''<div style="background:#fff;border-radius:14px;overflow:hidden;margin:8px 32px;box-shadow:0 2px 12px rgba(0,0,0,0.1);">
                    <div style="padding:16px 24px;border-bottom:1px solid #f0f0f0;display:flex;align-items:center;justify-content:space-between;">
                        <div style="display:flex;align-items:center;gap:10px;">
                            <span style="font-weight:700;font-size:1rem;color:#1e1b4b;">{topic}</span>
                            <span style="font-size:0.72rem;background:{"#d1fae5" if level=="Mudah" else "#fef3c7" if level=="Sedang" else "#fee2e2"};color:{level_color};border-radius:20px;padding:3px 12px;font-weight:600;">{level}</span>
                        </div>
                        <div style="display:flex;align-items:center;gap:12px;">
                            <span style="font-size:0.82rem;color:#6b7280;">{answered} answered</span>
                        </div>
                    </div>
                    <div style="padding:0 24px;">
                        <div style="display:flex;justify-content:space-between;padding:10px 0 4px;font-size:0.8rem;color:#6b7280;">
                            <span>Question {idx+1} of {total}</span><span>{pct}% complete</span>
                        </div>
                        <div style="height:5px;background:#e5e7eb;border-radius:4px;margin-bottom:2px;">
                            <div style="height:100%;width:{int((idx+1)/total*100)}%;background:linear-gradient(90deg,#6366f1,#8b5cf6);border-radius:4px;"></div>
                        </div>
                    </div>
                    <div style="padding:22px 24px 8px;">
                        <div style="font-size:0.72rem;font-weight:600;color:#6366f1;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;">Question {idx+1}</div>
                        <div style="font-size:1.05rem;font-weight:600;color:#1e1b4b;line-height:1.65;">{q["question"]}</div>
                    </div>
                </div>''', unsafe_allow_html=True)
                if not qs["submitted"]:
                    st.markdown("""<style>div[data-testid="stRadio"]{width:100% !important;padding:0 32px !important;}div[data-testid="stRadio"]>label{display:none !important;}div[data-testid="stRadio"]>div{display:flex !important;flex-direction:column !important;gap:10px !important;width:100% !important;}div[data-testid="stRadio"] label[data-baseweb="radio"]{background:#fff !important;border:1.5px solid #e5e7eb !important;border-radius:10px !important;padding:14px 18px !important;width:100% !important;cursor:pointer !important;}div[data-testid="stRadio"] label[data-baseweb="radio"]:hover{border-color:#6366f1 !important;background:#eef2ff !important;}div[data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"]{border-color:#6366f1 !important;background:#eef2ff !important;}</style>""",unsafe_allow_html=True)
                    opt_labels=[re.sub(r'^[A-D]\.\s*','',o) for o in opts]; radio_key=f"{qkey}_radio_{idx}"; current=qs["answers"].get(idx)
                    chosen=st.radio("Pilih jawaban:",options=range(len(opt_labels)),format_func=lambda x:f"{labels[x]}. {opt_labels[x]}",index=current,key=radio_key,label_visibility="collapsed")
                    if chosen is not None and chosen!=qs["answers"].get(idx): qs["answers"][idx]=chosen; st.rerun()
                else:
                    st.markdown('<div style="padding:0 24px 20px;">',unsafe_allow_html=True)
                    for oi,opt in enumerate(opts):
                        opt_text=re.sub(r'^[A-D]\.\s*','',opt)
                        if oi==correct: bg,border,tc="#f0fdf4","#10b981","#065f46"; dot='<div style="width:10px;height:10px;border-radius:50%;background:#10b981;"></div>'; rc="#10b981"
                        elif qs["answers"].get(idx)==oi: bg,border,tc="#fef2f2","#ef4444","#991b1b"; dot='<div style="width:10px;height:10px;border-radius:50%;background:#ef4444;"></div>'; rc="#ef4444"
                        else: bg,border,tc="#f9fafb","#e5e7eb","#9ca3af"; dot=""; rc="#e5e7eb"
                        st.markdown(f'<div style="display:flex;align-items:center;gap:14px;padding:14px 18px;background:{bg};border:1.5px solid {border};border-radius:10px;margin-bottom:10px;"><div style="width:20px;height:20px;border-radius:50%;border:2px solid {rc};display:flex;align-items:center;justify-content:center;flex-shrink:0;">{dot}</div><span style="color:{tc};font-size:0.95rem;">{opt_text}</span></div>',unsafe_allow_html=True)
                    st.markdown('</div>',unsafe_allow_html=True)
                nav1,nav2,nav3=st.columns([1,1,3])
                with nav1:
                    if st.button("← Previous",key=f"{qkey}_pv",disabled=(idx==0),use_container_width=True): qs["idx"]-=1; st.rerun()
                with nav2:
                    if not qs["submitted"] and idx<total-1:
                        if st.button("Next →",key=f"{qkey}_nx",type="primary",use_container_width=True): qs["idx"]+=1; st.rerun()
                    elif not qs["submitted"] and idx==total-1:
                        if st.button("✓ Submit",key=f"{qkey}_fn",type="primary",use_container_width=True): qs["submitted"]=True; st.rerun()
                with nav3:
                    if qs["submitted"]:
                        cc=sum(1 for qi,qq in enumerate(questions) if qs["answers"].get(qi)==qq.get("answer",0)); sc=int(cc/total*100)
                        st.markdown(f'<div style="display:inline-flex;align-items:center;gap:8px;padding:8px 20px;background:#eef2ff;border:1.5px solid #6366f1;border-radius:8px;font-size:0.9rem;color:#4338ca;font-weight:600;margin-top:4px;">🏆 Score: {sc}% &nbsp;·&nbsp; {cc}/{total} benar</div>',unsafe_allow_html=True)
        st.markdown('<div style="height:16px;"></div>',unsafe_allow_html=True)

    # Input area
    st.markdown("""
    <style>
    .input-sticky-wrap { position:fixed !important; bottom:0 !important; left:260px !important; right:0 !important; z-index:999 !important; background:#070714 !important; padding:12px 32px 16px !important; border-top:1px solid rgba(99,102,241,0.1) !important; }
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stTextInputRootElement"]){ background:#fff!important;border-radius:16px!important;border:1px solid rgba(0,0,0,0.1)!important;padding:10px 14px 6px 14px!important;align-items:center!important;gap:10px!important; }
    div[data-testid="stTextInputRootElement"] input{ background:transparent!important;border:none!important;box-shadow:none!important;color:#1a1a1a!important;font-size:15px!important; }
    div[data-testid="stTextInputRootElement"] input::placeholder{color:#9ca3af!important;}
    div[data-testid="stTextInputRootElement"] > div{border:none!important;box-shadow:none!important;}
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stTextInputRootElement"]) button[kind="primary"]{ width:34px!important;height:34px!important;min-height:34px!important;border-radius:50%!important;background:#4f46e5!important;border:none!important;padding:0!important;font-size:16px!important; }
    div[data-testid="stFileUploader"]{ position:fixed!important;top:-9999px!important;left:-9999px!important;width:1px!important;height:1px!important;opacity:0!important;pointer-events:none!important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="input-sticky-wrap">', unsafe_allow_html=True)
    uploaded_from_plus=st.file_uploader(label="upload",type=["pdf","txt"],key=f"plus_upload_{ss.input_counter}",label_visibility="collapsed")
    if uploaded_from_plus and uploaded_from_plus.name!=ss.doc_name and not ss.get("_doc_processing"):
        ss._doc_processing=True
        with st.spinner("Reading document..." if cur_lang()=="en" else "Membaca dokumen..."):
            try:
                text=extract_text_from_file(uploaded_from_plus); ss.doc_text=text; ss.doc_name=uploaded_from_plus.name; ss.total_docs+=1; ss._doc_processing=False
                if cur_lang() == "en":
                    _doc_msg = f'📄 Document <b>{uploaded_from_plus.name}</b> loaded ({len(text):,} characters).<br>You can ask questions about the document or generate a quiz from it.'
                else:
                    _doc_msg = f'📄 Dokumen <b>{uploaded_from_plus.name}</b> berhasil dibaca ({len(text):,} karakter).<br>Kamu bisa bertanya isi dokumen atau membuat quiz dari dokumen.'
                ss.chat_messages.append({"role":"assistant","type":"text","content":_doc_msg})
                sync_messages_to_conv(); st.rerun()
            except Exception as e: ss._doc_processing=False; st.error(f"Error: {e}")
    col_plus,col_input,col_send=st.columns([1,10,1])
    with col_plus:
        components.html("""<style>*{box-sizing:border-box;margin:0;padding:0;}body{background:transparent;}.btn-plus{width:34px;height:34px;border-radius:50%;border:1px solid rgba(0,0,0,0.12);background:#fff;color:#6b7280;font-size:22px;cursor:pointer;display:flex;align-items:center;justify-content:center;margin-top:4px;}.btn-plus:hover{background:#f3f4f6;}input[type=file]{display:none;}</style><input type="file" id="fi" accept=".pdf,.txt" onchange="handleFile(this)"/><button class="btn-plus" onclick="document.getElementById('fi').click()">+</button><script>function handleFile(input){if(input.files.length>0){var dt=new DataTransfer();dt.items.add(input.files[0]);var ri=window.parent.document.querySelectorAll('input[type=file]');if(ri.length>0){var r=ri[ri.length-1];r.files=dt.files;r.dispatchEvent(new Event('change',{bubbles:true}));}}}</script>""",height=46)
    with col_input:
        def on_enter():
            val=ss.get(f"chat_input_{ss.input_counter}","").strip()
            if val: ss._pending_msg=val
        user_input=st.text_input("",placeholder=t("chat_placeholder"),label_visibility="collapsed",key=f"chat_input_{ss.input_counter}",on_change=on_enter)
    with col_send:
        send=st.button("↑",type="primary",use_container_width=True,key="send_btn")
    if ss.get("_pending_msg"):
        user_input=ss._pending_msg; send=True; ss._pending_msg=""
    col_a,col_b,_=st.columns([1,1,4])
    with col_a:
        if ss.doc_name and st.button("🗑️ Delete Document" if cur_lang()=="en" else "🗑️ Hapus Dokumen"):
            ss.doc_text=""; ss.doc_name=""; ss._doc_processing=False; ss.input_counter+=1
            ss.chat_messages=[m for m in ss.chat_messages if not (m.get("role")=="assistant" and ("berhasil dibaca" in m.get("content","") or "loaded (" in m.get("content","")))]
            sync_messages_to_conv(); st.rerun()
    with col_b:
        if ss.chat_messages and st.button("🗑️ Clear Chat" if cur_lang()=="en" else "🗑️ Hapus Chat"):
            ss.chat_messages=[]; ss.waiting_for_topic=False; ss.pending_quiz_topic=""
            uid=ss.get("user_id") or get_or_create_user(ss.get("user_name","User"))
            db_save_chat(uid,[]); sync_messages_to_conv(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    if send and user_input.strip():
        if not ss.active_conversation_id or not get_active_conv(): new_conversation()
        text=user_input.strip(); ss.chat_messages.append({"role":"user","content":text,"doc_name":""}); ss.total_questions+=1
        if detect_quiz_request(text):
            topic=extract_topic(text); level=detect_level(text)
            from_doc=any(k in text.lower() for k in ["dokumen","pdf","file","dari dokumen"])
            if from_doc and ss.doc_text and not topic: topic=ss.doc_name.replace(".pdf","").replace(".txt","").title()
            if not topic: ss.waiting_for_topic=True; ss.chat_messages.append({"role":"assistant","type":"text","content":("What topic do you want a quiz about? 📚" if cur_lang()=="en" else "Mau quiz tentang topik apa? 📚")})
            elif not level: ss.pending_quiz_topic=topic; ss.chat_messages.append({"role":"assistant","type":"level_select","content":f"{"Alright! Quiz about" if cur_lang()=='en' else 'Oke! Quiz tentang'} <b>{topic}</b>. {"Choose level:" if cur_lang()=='en' else 'Pilih level:'}","topic":topic})
            else: ss.pending_quiz_topic=topic; ss.chat_messages.append({"role":"assistant","type":"generating","content":f"{"Generating quiz" if cur_lang()=='en' else 'Membuat quiz'} <b>{topic}</b> {"level" if cur_lang()=='en' else 'level'} {level}...","topic":topic,"level":level})
        elif ss.waiting_for_topic:
            topic=text.strip().title(); ss.waiting_for_topic=False; ss.pending_quiz_topic=topic
            ss.chat_messages.append({"role":"assistant","type":"level_select","content":f"{"Alright! Quiz about" if cur_lang()=='en' else 'Oke! Quiz tentang'} <b>{topic}</b>. {"Choose level:" if cur_lang()=='en' else 'Pilih level:'}","topic":topic})
        elif ss.doc_text: ss.chat_messages.append({"role":"assistant","type":"text","content":"⏳ Searching document..." if cur_lang()=="en" else "⏳ Mencari di dokumen..."})
        else: ss.chat_messages.append({"role":"assistant","type":"text","content":"⏳ AI is processing..." if cur_lang()=="en" else "⏳ AI sedang memproses..."})
        sync_messages_to_conv()
        uid=ss.get("user_id") or get_or_create_user(ss.get("user_name","User"))
        db_save_chat(uid,ss.chat_messages); ss.input_counter+=1; st.rerun()

# =============================================
# PLAN BELAJAR
# =============================================
elif menu == "Plan Belajar":
    import datetime

    if "plan_tab" not in ss:
        ss.plan_tab = "sessions"
    if "just_created" in ss and ss.just_created:
        ss.plan_tab = "sessions"
        del ss.just_created

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Share+Tech+Mono&family=DM+Sans:wght@300;400;500&display=swap');
    .block-container { padding: 28px 40px !important; }
    .stApp { background: #020617 !important; }
    div[data-testid="stHorizontalBlock"] button[kind="primary"] { background: rgba(56,189,248,0.07) !important; border: 1px solid rgba(56,189,248,0.45) !important; color: #38bdf8 !important; font-family: 'Share Tech Mono', monospace !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; font-size: 0.76rem !important; box-shadow: none !important; border-radius: 8px !important; }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] { background: transparent !important; border: 1px solid rgba(56,189,248,0.15) !important; color: rgba(100,116,139,0.7) !important; font-family: 'Share Tech Mono', monospace !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; font-size: 0.76rem !important; border-radius: 8px !important; }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover { border-color: rgba(56,189,248,0.45) !important; color: #38bdf8 !important; }
    .session-header { font-size:11px; font-weight:700; color:#38bdf8; letter-spacing:0.15em; text-transform:uppercase; padding:10px 0; font-family:'Share Tech Mono',monospace; }
    .session-name { color:#f1f5f9; font-size:14px; font-weight:600; padding:8px 0; font-family:'DM Sans',sans-serif; }
    .session-date { color:rgba(100,116,139,0.7); font-size:12px; padding:8px 0; font-family:'Share Tech Mono',monospace; }
    .prog-bar-bg { background:rgba(56,189,248,0.08); height:5px; width:100%; border-radius:3px; }
    .prog-bar-fill { background:linear-gradient(90deg,#6366f1,#38bdf8); height:100%; border-radius:3px; }
    .prog-pct { font-size:11px; color:#38bdf8; font-weight:700; font-family:'Share Tech Mono',monospace; margin-left:8px; }
    .topic-chip { display:inline-block; padding:4px 12px; background:rgba(56,189,248,0.08); border:1px solid rgba(56,189,248,0.3); color:#e2e8f0; font-size:11px; font-weight:600; font-family:'Share Tech Mono',monospace; border-radius:6px; letter-spacing:0.04em; }
    .empty-state { text-align:center; padding:48px 20px; font-family:'Share Tech Mono',monospace; font-size:11px; color:rgba(100,116,139,0.45); letter-spacing:0.08em; }
    div[data-testid="stExpander"] { background:#0f172a !important; border:1px solid rgba(56,189,248,0.12) !important; border-radius:10px !important; }
    div[data-testid="stExpander"]>details { background:#0f172a !important; border:none !important; }
    div[data-testid="stExpander"]>details>summary { background:#0d1526 !important; color:#f1f5f9 !important; font-family:'Share Tech Mono',monospace !important; font-size:13px !important; padding:14px 20px !important; border-radius:8px !important; }
    div[data-testid="stExpander"]>details>summary:hover { background:rgba(56,189,248,0.06) !important; color:#38bdf8 !important; }
    div[data-testid="stExpander"]>details>summary p { color:#f1f5f9 !important; font-family:'Share Tech Mono',monospace !important; font-size:13px !important; }
    div[data-testid="stExpander"]>details[open]>summary { border-bottom:1px solid rgba(56,189,248,0.1) !important; color:#38bdf8 !important; }
    div[data-testid="stExpander"]>details[open]>summary p { color:#38bdf8 !important; }
    div[data-testid="stExpander"]>details>div[data-testid="stExpanderDetails"] { background:rgba(2,8,28,0.7) !important; padding:0 !important; }
    .material-item { display:flex; align-items:center; gap:12px; padding:10px 14px; border-bottom:1px solid rgba(56,189,248,0.05); }
    .material-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
    .material-dot.active { background:#38bdf8; box-shadow:0 0 6px #38bdf8; }
    .material-dot.done { background:#10b981; }
    .material-dot.locked { background:rgba(56,189,248,0.15); }
    .material-name { flex:1; font-size:13px; color:#f1f5f9; font-family:'DM Sans',sans-serif; }
    .material-time { font-size:10px; color:rgba(100,116,139,0.5); font-family:'Share Tech Mono',monospace; }
    .read-area { background:#0f172a; border:1px solid rgba(56,189,248,0.12); padding:24px 28px; margin-bottom:20px; border-radius:12px; }
    .read-breadcrumb { font-family:'Share Tech Mono',monospace; font-size:9px; color:rgba(56,189,248,0.4); letter-spacing:0.12em; margin-bottom:10px; }
    .read-title { font-family:'Orbitron',monospace; font-size:1.2rem; font-weight:700; color:#f1f5f9; margin-bottom:20px; border-left:3px solid #38bdf8; padding-left:16px; }
    .read-body { font-family:'DM Sans',sans-serif; font-size:14px; line-height:1.75; color:rgba(203,213,225,0.9); }
    .sp-header { margin-top:22px; margin-bottom:12px; border-left:3px solid #818cf8; padding-left:16px; }
    .sp-title { font-family:'Orbitron',monospace; font-size:0.95rem; font-weight:600; color:#f1f5f9; letter-spacing:0.02em; }
    div[data-testid="stButton"] button { background: rgba(56,189,248,0.05) !important; border: 1px solid rgba(56,189,248,0.25) !important; color: #38bdf8 !important; font-family: 'Share Tech Mono', monospace !important; font-size: 11px !important; letter-spacing: 0.08em !important; border-radius: 8px !important; text-transform: uppercase !important; }
    div[data-testid="stButton"] button:hover { background: rgba(56,189,248,0.1) !important; border-color: rgba(56,189,248,0.55) !important; }
    div[data-testid="stButton"] button[kind="primary"] { background: rgba(56,189,248,0.08) !important; border: 1px solid #38bdf8 !important; color: #38bdf8 !important; box-shadow: 0 0 14px rgba(56,189,248,0.12) !important; }
    div[data-testid="stButton"] button p, div[data-testid="stButton"] button span { color: inherit !important; font-family: 'Share Tech Mono', monospace !important; font-size: 11px !important; letter-spacing: 0.08em !important; }
    div[data-testid="stCheckbox"] label span { color: rgba(100,116,139,0.8) !important; }
    </style>
    """, unsafe_allow_html=True)

    user_name = ss.get("user_name", "User")
    hour = datetime.datetime.now().hour
    greet = t("greeting_morning") if hour<12 else (t("greeting_afternoon") if hour<17 else t("greeting_evening"))
    col_hdr, col_btn = st.columns([4,1])
    with col_hdr:
        st.markdown(f'''<div style="margin-bottom:20px;">
            <div style="font-family:'Orbitron',monospace;font-size:1.15rem;font-weight:700;color:#f1f5f9;letter-spacing:0.03em;">{greet}, <span style="color:#38bdf8;">{user_name}</span></div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:10px;color:rgba(56,189,248,0.38);margin-top:6px;letter-spacing:0.12em;">{t("plan_greeting_sub")}</div>
        </div>''', unsafe_allow_html=True)
    with col_btn:
        if st.button("＋ Add Session", key="open_modal", use_container_width=True, type="primary"):
            ss.modal_step=1; ss.modal_sname=""; ss.modal_topics=""; ss.modal_level="Beginner"; ss.modal_deadline=""; ss.modal_topics2=""; ss.modal_level2="Beginner"; st.rerun()

    has_active = ss.get("active_session") is not None and len(ss.sessions) > 0
    if has_active: tab_col1, tab_col2, _ = st.columns([1,1,4])
    else: tab_col1, _ = st.columns([1,5])
    with tab_col1:
        t1_type = "primary" if ss.plan_tab=="sessions" else "secondary"
        if st.button("📋  Sessions", key="tab_sessions", use_container_width=True, type=t1_type):
            ss.plan_tab="sessions"; ss.modal_step=0; st.rerun()
    if has_active:
        with tab_col2:
            t2_type = "primary" if ss.plan_tab=="study_materials" else "secondary"
            if st.button("📚  Study Materials", key="tab_sm", use_container_width=True, type=t2_type):
                ss.plan_tab="study_materials"; ss.modal_step=0; st.rerun()
    else:
        ss.plan_tab = "sessions"

    @st.dialog("Edit Session", width="small")
    def dialog_edit_session(idx):
        sess = ss.sessions[idx]
        st.markdown(f'<div style="margin-bottom:12px;"><div style="font-size:11px;color:#9ca3af;font-family:\'Share Tech Mono\',monospace;letter-spacing:0.08em;">// EDIT SESSION</div><div style="font-size:16px;font-weight:700;color:#1e1b4b;margin-top:4px;">{sess["name"]}</div><hr style="border:none;border-top:1px solid #e5e7eb;margin:10px 0 0;"></div>', unsafe_allow_html=True)
        new_name = st.text_input("NAMA SESSION", value=sess["name"], key=f"dlg_edit_name_{idx}")
        new_topics = st.text_input("TOPICS", value=sess.get("topics",""), key=f"dlg_edit_topics_{idx}")
        st.markdown("**LEVEL**")
        level_opts = ["Beginner","Intermediate","Advance"]
        new_level = st.radio("", level_opts, horizontal=True,
            index=level_opts.index(sess.get("level","Beginner")),
            key=f"dlg_edit_level_{idx}", label_visibility="collapsed")
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Batal", use_container_width=True, key=f"dlg_edit_cancel_{idx}"):
                st.rerun()
        with c2:
            if st.button("💾 Simpan", use_container_width=True, type="primary", key=f"dlg_edit_save_{idx}"):
                if not new_name.strip():
                    st.warning("Nama session tidak boleh kosong!")
                else:
                    ss.sessions[idx]["name"] = new_name.strip()
                    ss.sessions[idx]["topics"] = new_topics.strip()
                    ss.sessions[idx]["level"] = new_level
                    uid = ss.get("user_id") or get_or_create_user(ss.get("user_name","User"))
                    sync_session_to_db(uid, ss.sessions)
                    st.rerun()

    @st.dialog("Hapus Session", width="small")
    def dialog_delete_session(idx):
        sess = ss.sessions[idx]
        st.markdown(f'''
        <div style="text-align:center;padding:8px 0 16px;">
            <div style="font-size:2.5rem;margin-bottom:12px;">🗑️</div>
            <div style="font-size:15px;font-weight:700;color:#1e1b4b;margin-bottom:8px;">Hapus Session ini?</div>
            <div style="font-size:13px;color:#6b7280;line-height:1.6;">Session <b style="color:#ef4444;">{sess["name"]}</b> dan semua data di dalamnya akan dihapus permanen dan tidak bisa dikembalikan.</div>
        </div>
        <hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 12px;">
        ''', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Batal", use_container_width=True, key=f"dlg_del_cancel_{idx}"):
                st.rerun()
        with c2:
            if st.button("🗑️ Ya, Hapus", use_container_width=True, type="primary", key=f"dlg_del_confirm_{idx}"):
                if ss.get("active_session") == idx: ss.active_session = None; ss.plan_tab = "sessions"
                elif ss.get("active_session") is not None and ss.active_session > idx: ss.active_session -= 1
                ss.sessions.pop(idx)
                uid = ss.get("user_id") or get_or_create_user(ss.get("user_name","User"))
                sync_session_to_db(uid, ss.sessions)
                st.rerun()

    if ss.get("dialog_edit_idx") is not None:
        eidx = ss.pop("dialog_edit_idx")
        if eidx < len(ss.sessions):
            dialog_edit_session(eidx)
    if ss.get("dialog_del_idx") is not None:
        didx = ss.pop("dialog_del_idx")
        if didx < len(ss.sessions):
            dialog_delete_session(didx)

    if ss.plan_tab == "sessions":
        h1,h2,h3,h4,h5 = st.columns([3,3,2,2,3])
        with h1: st.markdown(f'<div class="session-header">{t("plan_col_name")}</div>', unsafe_allow_html=True)
        with h2: st.markdown(f'<div class="session-header">{t("plan_col_progress")}</div>', unsafe_allow_html=True)
        with h3: st.markdown(f'<div class="session-header">{t("plan_col_last")}</div>', unsafe_allow_html=True)
        with h4: st.markdown(f'<div class="session-header">{t("plan_col_topics")}</div>', unsafe_allow_html=True)
        with h5: st.markdown(f'<div class="session-header">{t("plan_col_action")}</div>', unsafe_allow_html=True)
        st.markdown('<hr style="border:none;border-top:1px solid rgba(56,189,248,0.1);margin:0 0 4px;">', unsafe_allow_html=True)

        if not ss.sessions:
            st.markdown('<div class="empty-state">// Belum ada session. Klik "+ Add Session" untuk mulai.</div>', unsafe_allow_html=True)
        else:
            for idx, sess in enumerate(ss.sessions):
                prog = sess.get("progress",0)
                col1,col2,col3,col4,col5 = st.columns([3,3,2,2,3])
                with col1: st.markdown(f'<div class="session-name">{sess["name"]}</div>', unsafe_allow_html=True)
                with col2: st.markdown(f'<div style="padding:8px 0;"><div class="prog-bar-bg"><div class="prog-bar-fill" style="width:{prog}%"></div></div><span class="prog-pct">{prog}%</span></div>', unsafe_allow_html=True)
                with col3: st.markdown(f'<div class="session-date">{sess.get("last_checked","—")}</div>', unsafe_allow_html=True)
                with col4: st.markdown(f'<div style="padding:8px 0;"><span class="topic-chip">{sess.get("topics","—")}</span></div>', unsafe_allow_html=True)
                with col5:
                    btn_c1, btn_c2, btn_c3 = st.columns(3)
                    with btn_c1:
                        if st.button("▶", key=f"open_sess_{idx}", help=t("plan_btn_open_help")):
                            ss.active_session=idx; ss.material_view="list"; ss.plan_tab="study_materials"; ss.modal_step=0; st.rerun()
                    with btn_c2:
                        if st.button("✏️", key=f"edit_sess_{idx}", help=t("plan_btn_edit_help")):
                            ss["dialog_edit_idx"] = idx; st.rerun()
                    with btn_c3:
                        if st.button("🗑️", key=f"del_sess_{idx}", help=t("plan_btn_del_help")):
                            ss["dialog_del_idx"] = idx; st.rerun()
                st.markdown('<hr style="border:none;border-top:1px solid rgba(56,189,248,0.05);margin:0;">', unsafe_allow_html=True)

        active_idx = ss.get("active_session", None)
        active_sess_p = ss.sessions[active_idx] if (active_idx is not None and active_idx < len(ss.sessions)) else None
        if active_sess_p and ss.plan_tab == "study_materials":
            plan = active_sess_p.get("plan_data", []); sess_topics_p = active_sess_p["topics"]; sess_deadline_p = active_sess_p.get("deadline","")
            deadline_span = f'<span style="font-size:10px;color:rgba(56,189,248,0.45);margin-left:8px;font-family:\'Share Tech Mono\',monospace;">· Deadline: {sess_deadline_p}</span>' if sess_deadline_p else ''
            st.markdown(f'<div class="sp-header"><div class="sp-title">📅 Study Plan — <span style="color:#818cf8;">{sess_topics_p}</span> {deadline_span}</div></div>', unsafe_allow_html=True)
            if not plan:
                with st.spinner(f"Generating study plan untuk '{sess_topics_p}'..."):
                    try:
                        raw_plan = generate_study_plan(sess_topics_p, 5, lang=cur_lang())
                        if raw_plan:
                            plan = [{"id":i,"Hari":item.get("hari",f"Day {i+1}"),"Jam":item.get("jam","08:00-10:00"),"Materi":item.get("materi",""),"Penjelasan":item.get("penjelasan",""),"Selesai":False} for i,item in enumerate(raw_plan)]
                            ss.sessions[active_idx]["plan_data"] = plan
                            uid = ss.get("user_id") or get_or_create_user(ss.get("user_name","User"))
                            sync_session_to_db(uid, ss.sessions); st.rerun()
                    except: st.info("💡 Belum bisa generate study plan saat ini.")
            if plan:
                completed = sum(1 for p in plan if p.get("Selesai")); pct = int(completed/len(plan)*100)
                st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;"><div style="flex:1;height:5px;background:rgba(56,189,248,0.1);border-radius:3px;overflow:hidden;"><div style="height:100%;width:{pct}%;background:linear-gradient(90deg,#38bdf8,#818cf8);border-radius:3px;"></div></div><span style="font-size:11px;color:rgba(100,116,139,0.6);font-family:\'Share Tech Mono\',monospace;">{completed}/{len(plan)} · {pct}%</span></div>', unsafe_allow_html=True)
                for i, item in enumerate(plan):
                    c1, c2 = st.columns([1, 12])
                    with c1:
                        checked = st.checkbox("", value=item.get("Selesai",False), key=f"pb_plan_{active_idx}_{i}")
                        if checked != item.get("Selesai",False):
                            ss.sessions[active_idx]["plan_data"][i]["Selesai"] = checked
                            done = sum(1 for p in ss.sessions[active_idx]["plan_data"] if p.get("Selesai"))
                            ss.sessions[active_idx]["progress"] = int(done/len(plan)*100)
                            uid = ss.get("user_id") or get_or_create_user(ss.get("user_name","User"))
                            sync_session_to_db(uid, ss.sessions); st.rerun()
                    with c2:
                        tick = "✅ " if item.get("Selesai") else ""
                        bg = "rgba(56,189,248,0.05)" if item.get("Selesai") else "#0f172a"
                        brd = "rgba(56,189,248,0.25)" if item.get("Selesai") else "rgba(56,189,248,0.1)"
                        st.markdown(f'<div style="background:{bg};border:1px solid {brd};border-radius:10px;padding:10px 14px;margin-bottom:4px;"><span style="font-family:\'Share Tech Mono\',monospace;color:rgba(100,116,139,0.5);font-size:9px;">{item["Hari"]} · {item["Jam"]}</span><br><span style="color:#f1f5f9;font-size:13px;">{tick}{item["Materi"]}</span>' + (f'<br><span style="color:rgba(100,116,139,0.55);font-size:11px;">{item.get("Penjelasan","")}</span>' if item.get("Penjelasan") else '') + '</div>', unsafe_allow_html=True)
                if pct == 100: st.balloons(); st.success(t("plan_all_done"))

    elif ss.plan_tab == "study_materials":
        if ss.active_session is None or ss.active_session >= len(ss.sessions):
            st.markdown('<div style="text-align:center;padding:60px 20px;"><div style="font-size:2.5rem;color:rgba(56,189,248,0.15);margin-bottom:16px;">📚</div><div style="font-family:\'Orbitron\',monospace;font-size:1rem;color:#f1f5f9;margin-bottom:8px;">Belum ada session yang dipilih</div><div style="font-size:11px;color:rgba(56,189,248,0.35);font-family:\'Share Tech Mono\',monospace;letter-spacing:0.08em;">// Klik ▶ pada session untuk membuka Study Materials</div></div>', unsafe_allow_html=True)
            if st.button(t("plan_back_sessions"), type="primary"): ss.plan_tab="sessions"; st.rerun()
            st.stop()

        active_idx = ss.active_session; active_sess = ss.sessions[active_idx]
        sess_topics = active_sess["topics"]; sess_level = active_sess["level"]
        st.markdown(f'''<div style="margin-bottom:20px;">
            <div style="font-family:\'Share Tech Mono\',monospace;font-size:9px;color:rgba(56,189,248,0.4);letter-spacing:0.12em;">{t("plan_session_active")}</div>
            <div style="font-family:\'Orbitron\',monospace;font-size:1.15rem;font-weight:700;color:#38bdf8;">{active_sess["name"]}</div>
            <div style="font-size:11px;color:rgba(100,116,139,0.6);font-family:\'Share Tech Mono\',monospace;margin-top:4px;">{sess_topics} · {sess_level}</div>
            <hr style="border:none;border-top:1px solid rgba(56,189,248,0.1);margin:12px 0 18px;">
        </div>''', unsafe_allow_html=True)

        chapters_key = f"chapters_{cur_lang()}"
        if not active_sess.get(chapters_key):
            with st.spinner(f"{t('plan_generate_spinner')} '{sess_topics}'..."):
                try:
                    if cur_lang() == "en":
                        prompt=f"""Create a learning structure for the topic "{sess_topics}" at {sess_level} level.
Make 3 chapters, each chapter contains 3-4 learning materials + 1 quiz at the end.
Write ALL titles in English.
JSON format:
{{
  "chapters": [
    {{
      "id": 0,
      "title": "Chapter Title in English",
      "materials": [
        {{"id": 0, "title": "Material Title in English", "duration": 60, "type": "lesson", "done": false}},
        {{"id": 1, "title": "Material Title 2 in English", "duration": 60, "type": "lesson", "done": false}},
        {{"id": 2, "title": "Chapter Quiz", "duration": 30, "type": "quiz", "done": false}}
      ]
    }}
  ]
}}
Respond with JSON only, no markdown."""
                    else:
                        prompt=f"""Buatkan struktur belajar untuk topik "{sess_topics}" level {sess_level}.
Buat 3 chapter, setiap chapter berisi 3-4 materi pembelajaran + 1 quiz di akhir.
Tulis semua judul dalam Bahasa Indonesia.
Format JSON:
{{
  "chapters": [
    {{
      "id": 0,
      "title": "Judul Chapter",
      "materials": [
        {{"id": 0, "title": "Judul Materi", "duration": 60, "type": "lesson", "done": false}},
        {{"id": 1, "title": "Judul Materi 2", "duration": 60, "type": "lesson", "done": false}},
        {{"id": 2, "title": "Quiz Chapter", "duration": 30, "type": "quiz", "done": false}}
      ]
    }}
  ]
}}
Respond with JSON only, no markdown."""
                    resp=ask_ai(prompt, lang=cur_lang()) or ""
                    resp=resp.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    if not resp: raise Exception("AI mengembalikan respons kosong. Coba lagi.")
                    data=json.loads(resp)
                    existing = active_sess.get("chapters", active_sess.get(f"chapters_{'en' if cur_lang()=='id' else 'id'}", []))
                    new_chapters = data["chapters"]
                    for ci, ch in enumerate(new_chapters):
                        if ci < len(existing):
                            for mi, mat in enumerate(ch["materials"]):
                                if mi < len(existing[ci].get("materials", [])):
                                    mat["done"] = existing[ci]["materials"][mi].get("done", False)
                    ss.sessions[active_idx][chapters_key] = new_chapters
                    uid=ss.get("user_id") or get_or_create_user(ss.get("user_name","User"))
                    sync_session_to_db(uid,ss.sessions); st.rerun()
                except Exception as e: st.error(f"Gagal generate materi: {e}"); st.stop()

        chapters = active_sess.get(chapters_key, []); view = ss.get("material_view","list")

        if view == "list":
            for ci, chapter in enumerate(chapters):
                chapter_unlocked = True
                if ci > 0:
                    prev = chapters[ci-1]; chapter_unlocked = all(m.get("done",False) for m in prev["materials"])
                done_count = sum(1 for m in chapter["materials"] if m.get("done",False)); total_m = len(chapter["materials"])
                lock_icon = "🔒" if not chapter_unlocked else ""
                prog_text = f"· {done_count}/{total_m}" if chapter_unlocked else ""
                label = f"Chapter {ci+1} {lock_icon} {prog_text}  —  {chapter['title']}"
                with st.expander(label, expanded=st.session_state.get(f"ch_open_{ci}", ci==0 and chapter_unlocked)):
                    if not chapter_unlocked:
                        st.markdown(f'<div style="color:rgba(100,116,139,0.6);font-size:13px;padding:10px 0;">{t("plan_chapter_locked")}</div>', unsafe_allow_html=True)
                    else:
                        for mi, mat in enumerate(chapter["materials"]):
                            mat_unlocked = True
                            if mi > 0: mat_unlocked = chapter["materials"][mi-1].get("done",False)
                            is_done = mat.get("done",False); dot_class = "done" if is_done else ("active" if mat_unlocked else "locked")
                            icon = "📝" if mat["type"]=="quiz" else "📖"; check = "✓ " if is_done else ""
                            st.markdown(f'<div class="material-item" style="{"opacity:0.4" if not mat_unlocked and not is_done else ""}"><div class="material-dot {dot_class}"></div><div class="material-name">{icon} {check}{mat["title"]}</div><div class="material-time">⏱ {mat["duration"]} min</div></div>', unsafe_allow_html=True)
                            if mat_unlocked and not is_done:
                                btn_label = t("plan_start_quiz") if mat["type"]=="quiz" else t("plan_start_lesson")
                                if st.button(btn_label, key=f"open_mat_{ci}_{mi}", type="primary" if mat["type"]=="quiz" else "secondary"):
                                    ss.active_chapter=ci; ss.active_material=mi; ss.material_view="quiz" if mat["type"]=="quiz" else "read"; st.rerun()

        elif view == "read":
            ci=ss.active_chapter; mi=ss.active_material; chapter=chapters[ci]; mat=chapter["materials"][mi]; mat_title=mat["title"]
            content_key = f"content_{active_idx}_{ci}_{mi}_{cur_lang()}"
            if content_key not in ss:
                with st.spinner(f"{t('plan_generating_material')} '{mat_title}'..."):
                    try:
                        doc_ctx = f"\n\nDocument context:\n{active_sess['doc_text'][:2000]}" if active_sess.get("doc_text") and cur_lang()=="en" else (f"\n\nKonteks dokumen:\n{active_sess['doc_text'][:2000]}" if active_sess.get("doc_text") else "")
                        if cur_lang() == "en":
                            prompt = f"""Create comprehensive learning material about "{mat_title}" in the context of "{sess_topics}" for {sess_level} level.{doc_ctx}

Write in clear, easy-to-understand English.

FORMAT RULES — MUST FOLLOW:
- DO NOT use asterisks (**) or any markdown symbols
- DO NOT write opening phrases like "Sure!", "Great!", "Let's learn"
- DO NOT use bullet symbols like * or - at the start of lines
- Write like a textbook: go straight to the material, formal but approachable
- Structure: Section Title (no #), then explanatory paragraphs, then examples if needed
- Separate each section with a blank line
- For lists, use numbers (1. 2. 3.) not symbols
- End with a "Summary" section containing 2-3 key points"""
                        else:
                            prompt = f"""Buatkan materi pembelajaran lengkap tentang "{mat_title}" dalam konteks "{sess_topics}" untuk level {sess_level}.{doc_ctx}

Tulis dalam Bahasa Indonesia yang jelas dan mudah dipahami.

ATURAN FORMAT — WAJIB DIIKUTI:
- JANGAN gunakan tanda bintang (**) atau simbol markdown apapun
- JANGAN tulis kalimat pembuka seperti "Tentu!", "Baik!", "Mari kita pelajari", "Halo teman-teman"
- JANGAN gunakan bullet point simbol seperti * atau - di awal baris
- Tulis seperti buku pelajaran: langsung ke materi, formal tapi mudah dipahami
- Gunakan struktur: Judul Bagian (tanpa #), lalu paragraf penjelasan, lalu contoh jika perlu
- Pisahkan setiap bagian dengan baris kosong
- Untuk daftar/list, tulis dengan angka (1. 2. 3.) bukan simbol
- Akhiri dengan bagian "Ringkasan" berisi 2-3 poin penting"""
                        content = ask_ai(prompt, lang=cur_lang()) or ""
                        if not content.strip(): content = ("Failed to generate material, please try again." if cur_lang()=="en" else "Gagal memuat materi, silakan coba lagi.")
                        ss[content_key] = content
                    except Exception as e: ss[content_key] = f"Gagal load materi: {e}"
            content = ss.get(content_key, "")

            def format_content(text):
                import re as _re
                lines = text.split('\n')
                html = ""
                ol_open = False
                for line in lines:
                    line = line.strip()
                    line = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
                    line = _re.sub(r'\*(.+?)\*', r'\1', line)
                    line = _re.sub(r'^#+\s*', '', line)
                    if not line:
                        if ol_open: html += "</ol>"; ol_open = False
                        html += "<br>"
                        continue
                    num_match = _re.match(r'^(\d+)\.\s+(.+)', line)
                    if num_match:
                        if not ol_open: html += '<ol style="padding-left:20px;margin:8px 0;">'; ol_open = True
                        html += f'<li style="color:rgba(203,213,225,0.9);font-size:14px;line-height:1.85;margin-bottom:4px;">{num_match.group(2)}</li>'
                        continue
                    if ol_open: html += "</ol>"; ol_open = False
                    if _re.match(r'^[-•]\s+', line):
                        item = _re.sub(r'^[-•]\s+', '', line)
                        html += f'<li style="color:rgba(203,213,225,0.9);font-size:14px;line-height:1.85;margin-bottom:4px;margin-left:20px;">{item}</li>'
                        continue
                    if "ringkasan" in line.lower() or "kesimpulan" in line.lower() or "summary" in line.lower():
                        html += f'<div style="background:rgba(56,189,248,0.04);border-left:3px solid #818cf8;padding:10px 16px;margin:18px 0 6px;border-radius:0 8px 8px 0;"><span style="font-family:\'Share Tech Mono\',monospace;font-size:10px;color:#818cf8;letter-spacing:0.1em;text-transform:uppercase;">{line}</span></div>'
                    elif len(line) < 80 and not line.endswith('.') and line[0].isupper() and len(line.split()) <= 8:
                        html += f'<h3 style="font-family:\'Orbitron\',monospace;font-size:0.9rem;color:#38bdf8;margin:22px 0 8px;">{line}</h3>'
                    else:
                        html += f'<p style="color:rgba(203,213,225,0.9);font-size:14px;line-height:1.85;margin:0 0 10px;">{line}</p>'
                if ol_open: html += "</ol>"
                return html

            all_mats = [(c,m) for c in range(len(chapters)) for m in range(len(chapters[c]["materials"]))]
            cur_idx = next((i for i,(c,m) in enumerate(all_mats) if c==ci and m==mi), 0)
            has_prev = cur_idx>0; has_next = cur_idx<len(all_mats)-1
            next_ci,next_mi = all_mats[cur_idx+1] if has_next else (ci,mi)
            next_type = chapters[next_ci]["materials"][next_mi]["type"] if has_next else "lesson"

            st.markdown(f'<div class="read-area"><div class="read-breadcrumb">Chapter {ci+1} · {chapter["title"]}</div><div class="read-title">{mat_title}</div><div class="read-body">{format_content(content)}</div></div>', unsafe_allow_html=True)
            nav1,nav2,nav3=st.columns([1,2,1])
            with nav1:
                if has_prev:
                    prev_ci,prev_mi=all_mats[cur_idx-1]
                    if st.button(t("plan_prev"),key="mat_prev"): ss.active_chapter=prev_ci; ss.active_material=prev_mi; ss.material_view="read"; st.rerun()
            with nav2:
                if st.button(t("plan_back_list"),key="mat_list",use_container_width=True): ss.material_view="list"; st.rerun()
            with nav3:
                if has_next:
                    btn_label=t("plan_start_quiz") if next_type=="quiz" else f"{chapters[next_ci]['materials'][next_mi]['title']} →"
                    if st.button(btn_label,key="mat_next",type="primary"):
                        if (active_idx is not None and active_idx < len(ss.sessions)
                                and ci < len(chapters)
                                and mi < len(chapters[ci].get("materials", []))):
                            ss.sessions[active_idx][chapters_key][ci]["materials"][mi]["done"]=True
                            total_all=sum(len(c["materials"]) for c in chapters); done_all=sum(1 for c in chapters for m in c["materials"] if m.get("done"))
                            ss.sessions[active_idx]["progress"]=int(done_all/total_all*100)
                            uid=ss.get("user_id") or get_or_create_user(ss.get("user_name","User")); sync_session_to_db(uid,ss.sessions)
                            ss.active_chapter=next_ci; ss.active_material=next_mi; ss.material_view="quiz" if next_type=="quiz" else "read"; st.rerun()
                else:
                    if st.button(t("plan_finish"),key="mat_done",type="primary"):
                        ss.sessions[active_idx]["chapters"][ci]["materials"][mi]["done"]=True
                        total_all=sum(len(c["materials"]) for c in ss.sessions[active_idx]["chapters"]); done_all=sum(1 for c in ss.sessions[active_idx]["chapters"] for m in c["materials"] if m.get("done"))
                        ss.sessions[active_idx]["progress"]=int(done_all/total_all*100) if total_all else 0
                        uid=ss.get("user_id") or get_or_create_user(ss.get("user_name","User")); sync_session_to_db(uid,ss.sessions); ss.material_view="list"; st.rerun()

        elif view == "quiz":
            if ss.active_session is None or ss.active_session >= len(ss.sessions):
                ss.material_view = "list"
                st.rerun()
            ci=ss.active_chapter; mi=ss.active_material; chapter=chapters[ci]; quiz_topic=f"{chapter['title']} - {sess_topics}"
            st.markdown(f'''<div style="margin-bottom:20px;">
                <div style="font-family:\'Share Tech Mono\',monospace;font-size:9px;color:rgba(56,189,248,0.4);margin-bottom:4px;">Chapter {ci+1} · {chapter["title"]}</div>
                <div style="font-size:1.2rem;font-weight:700;color:#f1f5f9;margin-bottom:4px;font-family:\'Orbitron\',monospace;">Quiz: {chapter["title"]}</div>
                <div style="font-size:12px;color:rgba(56,189,248,0.35);font-family:\'Share Tech Mono\',monospace;">{t("quiz_chapter_sub")}</div>
            </div>''', unsafe_allow_html=True)

            qkey = f"sm_quiz_{active_idx}_{ci}_{cur_lang()}"
            if qkey not in ss:
                with st.spinner(t("quiz_making")):
                    try:
                        raw=generate_quiz(quiz_topic, sess_level if sess_level in ["Mudah","Sedang","Sulit","Easy","Medium","Hard"] else "Sedang", lang=cur_lang()) or ""
                        raw=raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                        if not raw: raise Exception("AI mengembalikan respons kosong. Coba lagi.")
                        questions=json.loads(raw); ss[qkey]={"questions":questions,"idx":0,"answers":{},"submitted":False}
                    except Exception as e: st.error(f"Gagal buat quiz: {e}"); st.stop()

            qdata=ss[qkey]; questions=qdata["questions"]; total_q=len(questions); idx=min(qdata["idx"],total_q-1)
            q=questions[idx]; opts=q["options"]; correct=q.get("answer",0); answered=len(qdata["answers"])
            labels=["A","B","C","D"]; pct_q=int((idx+1)/total_q*100)

            st.markdown(f'''<div style="background:#0f172a;border:1px solid rgba(56,189,248,0.12);border-radius:12px;padding:16px 22px;margin-bottom:16px;">
                <div style="display:flex;justify-content:space-between;font-size:11px;color:rgba(56,189,248,0.35);margin-bottom:8px;font-family:\'Share Tech Mono\',monospace;">
                    <span>{t("quiz_question_label")} {idx+1} {t("quiz_of")} {total_q}</span><span>{answered} {t("quiz_answered")}</span>
                </div>
                <div style="height:5px;background:rgba(99,102,241,0.12);border-radius:4px;margin-bottom:14px;">
                    <div style="height:100%;width:{pct_q}%;background:linear-gradient(90deg,#6366f1,#818cf8);border-radius:4px;"></div>
                </div>
                <div style="font-size:1rem;font-weight:600;color:#f1f5f9;line-height:1.65;">{q["question"]}</div>
            </div>''', unsafe_allow_html=True)

            if not qdata["submitted"]:
                st.markdown('<style>div[data-testid="stRadio"] label p{color:#f1f5f9 !important;font-family:DM Sans,sans-serif !important;}</style>', unsafe_allow_html=True)
                opt_labels=[re.sub(r'^[A-D]\.\s*','',o) for o in opts]
                chosen=st.radio("",options=range(len(opt_labels)),format_func=lambda x:f"{labels[x]}. {opt_labels[x]}",index=qdata["answers"].get(idx),key=f"sm_q_{active_idx}_{ci}_{idx}",label_visibility="collapsed")
                if chosen is not None and chosen!=qdata["answers"].get(idx): ss[qkey]["answers"][idx]=chosen; st.rerun()
                qn1,qn2=st.columns([1,1])
                with qn1:
                    if st.button(t("quiz_prev"),key="sq_pv",disabled=(idx==0),use_container_width=True): ss[qkey]["idx"]-=1; st.rerun()
                with qn2:
                    if idx<total_q-1:
                        if st.button(t("quiz_next"),key="sq_nx",type="primary",use_container_width=True): ss[qkey]["idx"]+=1; st.rerun()
                    else:
                        if st.button(t("quiz_submit"),key="sq_sub",type="primary",use_container_width=True): ss[qkey]["submitted"]=True; st.rerun()
            else:
                correct_ct=sum(1 for qi,qq in enumerate(questions) if qdata["answers"].get(qi)==qq.get("answer",0)); score=int(correct_ct/total_q*100)
                sc_color="#10b981" if score>=80 else "#f59e0b" if score>=60 else "#ef4444"
                st.markdown(f'''<div style="text-align:center;padding:28px;background:#0f172a;border:1px solid rgba(99,102,241,0.15);border-radius:14px;margin-bottom:20px;">
                    <div style="font-family:\'Orbitron\',monospace;font-size:2.8rem;font-weight:700;color:{sc_color};">{score}</div>
                    <div style="font-family:\'Share Tech Mono\',monospace;font-size:11px;color:rgba(100,116,139,0.5);">/ 100 · {correct_ct}/{total_q} {t("quiz_score_correct")}</div>
                    <div style="margin-top:10px;font-size:13px;color:#e2e8f0;">{t("quiz_pass") if score>=60 else t("quiz_fail")}</div>
                </div>''', unsafe_allow_html=True)

                analysis=t("quiz_analysis_excellent") if score>=80 else t("quiz_analysis_good") if score>=60 else t("quiz_analysis_poor")
                quiz_entry={"topic":f"Chapter {ci+1} - {chapter['title']}","level":sess_level,"score":score,"analysis":analysis}
                if "quiz_history" not in ss.sessions[active_idx]: ss.sessions[active_idx]["quiz_history"]=[]
                existing_idx = next((i for i, q in enumerate(ss.sessions[active_idx]["quiz_history"]) 
                     if q["topic"] == quiz_entry["topic"]), None)
                if existing_idx is not None:
                    old_score = ss.sessions[active_idx]["quiz_history"][existing_idx]["score"]
                    if quiz_entry["score"] > old_score:
                        quiz_entry["retry"] = True
                        ss.sessions[active_idx]["quiz_history"][existing_idx] = quiz_entry
                else:
                    ss.sessions[active_idx]["quiz_history"].append(quiz_entry)
                    ss.total_quizzes += 1
                uid = ss.get("user_id") or get_or_create_user(ss.get("user_name", "User"))
                sync_session_to_db(uid, ss.sessions)

                rb1,rb2=st.columns(2)
                with rb1:
                    if st.button(t("quiz_retry"),key="sq_retry",use_container_width=True): del ss[qkey]; st.rerun()
                with rb2:
                    if score>=60:
                        if st.button(t("quiz_continue"),key="sq_next_ch",type="primary",use_container_width=True):
                            if (active_idx is not None and active_idx < len(ss.sessions)
                                    and ci < len(chapters)
                                    and mi < len(chapters[ci].get("materials", []))):
                                ss.sessions[active_idx][chapters_key][ci]["materials"][mi]["done"]=True
                                total_all=sum(len(c["materials"]) for c in chapters); done_all=sum(1 for c in chapters for m in c["materials"] if m.get("done"))
                                ss.sessions[active_idx]["progress"]=int(done_all/total_all*100)
                                uid=ss.get("user_id") or get_or_create_user(ss.get("user_name","User")); sync_session_to_db(uid,ss.sessions); ss.material_view="list"; st.rerun()
                    else:
                        if st.button(t("quiz_back_read"),key="sq_back_read",use_container_width=True):
                            last_lesson=next((m for m in reversed(range(mi)) if chapter["materials"][m]["type"]=="lesson"),0)
                            ss.active_material=last_lesson; ss.material_view="read"; st.rerun()

                review_key = f"review_{qkey}"
                if review_key not in ss:
                    with st.spinner("..."):
                        try:
                            wrong_qs = []
                            for qi, qq in enumerate(questions):
                                user_ans=qdata["answers"].get(qi); correct_ans=qq.get("answer",0)
                                if user_ans != correct_ans:
                                    wrong_qs.append({"no":qi+1,"question":qq["question"],"correct":qq["options"][correct_ans],"user":qq["options"][user_ans] if user_ans is not None else t("quiz_not_answered")})
                            if wrong_qs:
                                if cur_lang() == "en":
                                    prompt=f"""For the topic "{quiz_topic}", provide a brief explanation (1-2 sentences) in English for why the correct answer is correct.
Format JSON: [{{"no": 1, "explanation": "explanation here..."}}]
Questions: {json.dumps(wrong_qs, ensure_ascii=False)}
JSON only."""
                                else:
                                    prompt=f"""Untuk topik "{quiz_topic}", berikan penjelasan singkat (1-2 kalimat) mengapa jawaban yang benar itu benar.
Format JSON: [{{"no": 1, "explanation": "penjelasan..."}}]
Soal: {json.dumps(wrong_qs, ensure_ascii=False)}
JSON only."""
                                raw_exp=ask_ai(prompt, lang=cur_lang()) or ""
                                raw_exp=raw_exp.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                                if not raw_exp: raise Exception("empty")
                                explanations={e["no"]:e["explanation"] for e in json.loads(raw_exp)}
                            else:
                                explanations={}
                            ss[review_key]=explanations
                        except: ss[review_key]={}

                explanations=ss.get(review_key,{})
                st.markdown(f'<div style="margin:16px 0 10px;font-family:\'Share Tech Mono\',monospace;font-size:10px;color:rgba(56,189,248,0.4);letter-spacing:0.1em;text-transform:uppercase;">{t("quiz_review_label")}</div>', unsafe_allow_html=True)
                for qi, qq in enumerate(questions):
                    user_ans=qdata["answers"].get(qi); correct_ans=qq.get("answer",0); is_correct=user_ans==correct_ans
                    opts_q=qq["options"]; labels_q=["A","B","C","D"]
                    icon="✅" if is_correct else "❌"; bg="rgba(16,185,129,0.06)" if is_correct else "rgba(239,68,68,0.06)"; border="#10b981" if is_correct else "#ef4444"
                    correct_ans_text=re.sub(r'^[A-D]\. *','',opts_q[correct_ans])
                    user_ans_text=re.sub(r'^[A-D]\. *','',opts_q[user_ans]) if user_ans is not None else "Tidak dijawab"
                    explanation=explanations.get(qi+1,"")
                    extra_html = ""
                    if not is_correct:
                        extra_html += f'<div style="font-size:12px;color:rgba(148,163,184,0.55);margin-top:4px;">{t("quiz_your_label")} <span style="color:#ef4444;font-weight:600;">{labels_q[user_ans] if user_ans is not None else "—"}. {user_ans_text}</span></div>'
                    if explanation:
                        extra_html += f'<div style="font-size:11px;color:rgba(148,163,184,0.55);font-style:italic;margin-top:6px;line-height:1.6;">{explanation}</div>'
                    card_html = (
                        f'<div style="background:{bg};border:1px solid {border};border-radius:10px;padding:14px 18px;margin-bottom:10px;">'
                        f'<div style="font-size:10px;color:rgba(100,116,139,0.45);font-family:\'Share Tech Mono\',monospace;margin-bottom:6px;">No. {qi+1} &nbsp;·&nbsp; {icon} {t("quiz_correct") if is_correct else t("quiz_wrong")}</div>'
                        f'<div style="font-size:13px;color:#f1f5f9;font-weight:600;margin-bottom:8px;line-height:1.5;">{qq["question"]}</div>'
                        f'<div style="font-size:12px;color:#10b981;font-weight:600;">{t("quiz_correct_label")} {labels_q[correct_ans]}. {correct_ans_text}</div>'
                        f'{extra_html}'
                        f'</div>'
                    )
                    st.markdown(card_html, unsafe_allow_html=True)

    # ── Dialog Add Session (2 steps only) ──
    def step_bar(current):
        steps=[]
        for i in range(1,3):
            if i<current: dot=f'<div style="width:28px;height:28px;border-radius:50%;background:#6366f1;color:#fff;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;">✓</div>'; line='<div style="flex:1;height:2px;background:#6366f1;"></div>'
            elif i==current: dot=f'<div style="width:28px;height:28px;border-radius:50%;background:#6366f1;color:#fff;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">{i}</div>'; line='<div style="flex:1;height:2px;background:rgba(99,102,241,0.2);"></div>'
            else: dot=f'<div style="width:28px;height:28px;border-radius:50%;background:rgba(99,102,241,0.1);color:rgba(148,163,184,0.4);border:1px solid rgba(99,102,241,0.25);display:flex;align-items:center;justify-content:center;font-size:11px;">{i}</div>'; line='<div style="flex:1;height:2px;background:rgba(99,102,241,0.15);"></div>'
            steps.append(dot)
            if i<2: steps.append(line)
        return f'<div style="display:flex;align-items:center;gap:4px;margin-bottom:16px;">{"".join(steps)}</div>'

    @st.dialog("Add Session", width="small")
    def dialog_step1():
        st.markdown(step_bar(1), unsafe_allow_html=True)
        st.markdown('<div style="margin-bottom:8px;"><div style="font-weight:600;font-size:15px;margin-bottom:2px;">Create New Session</div><div style="font-size:12px;color:#9ca3af;margin-bottom:10px;">A session is your isolated learning workspace</div><hr style="border:none;border-top:1px solid #e5e7eb;margin:0;"></div>', unsafe_allow_html=True)
        sname=st.text_input("SESSION NAME", placeholder="e.g. UTS Machine Learning", key="d1_name")
        topics=st.text_input("TOPICS", placeholder="e.g. Python, ML, Kalkulus", key="d1_topics")
        st.markdown("**YOUR LEVEL**")
        level=st.radio("", ["Beginner","Intermediate","Advance"], horizontal=True, key="d1_level", label_visibility="collapsed", index=None)
        st.divider()
        c1,c2=st.columns(2)
        with c1:
            if st.button("Cancel", use_container_width=True, key="d1_cancel"): ss.modal_step=0; st.rerun()
        with c2:
            if st.button("Continue →", use_container_width=True, type="primary", key="d1_cont"):
                if not sname.strip(): st.warning("Isi Session Name dulu!")
                elif level is None: st.warning("Pilih level dulu!")
                else: ss.modal_sname=sname.strip(); ss.modal_topics=topics.strip(); ss.modal_level=level; ss.modal_step=2; st.rerun()

    @st.dialog("Add Session", width="small")
    def dialog_step2():
        import datetime as _dt2
        st.markdown(step_bar(2), unsafe_allow_html=True)
        st.markdown('<div style="margin-bottom:8px;"><div style="font-weight:600;font-size:15px;margin-bottom:2px;">How Do You Want To Learn?</div><div style="font-size:12px;color:#9ca3af;margin-bottom:10px;">Set your study goal and pace</div><hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 8px 0;"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;font-weight:600;color:#6b7280;letter-spacing:0.08em;margin-bottom:2px;">DEADLINE</div>', unsafe_allow_html=True)
        deadline_date=st.date_input("DEADLINE", value=None, min_value=_dt2.date.today(), format="DD/MM/YYYY", key="d2_deadline", label_visibility="collapsed")
        deadline=deadline_date.strftime("%Y-%m-%d") if deadline_date else ""
        if deadline: st.markdown(f'<div style="font-size:11px;color:#10b981;margin-top:2px;">✓ {deadline_date.strftime("%d %B %Y")}</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;font-weight:600;color:#6b7280;letter-spacing:0.08em;margin-top:8px;margin-bottom:2px;">TOPICS</div>', unsafe_allow_html=True)
        topics2=st.text_input("TOPICS", placeholder="Topik spesifik yang ingin dipelajari", key="d2_topics", label_visibility="collapsed")
        st.markdown('<div style="font-size:11px;font-weight:600;color:#6b7280;letter-spacing:0.08em;margin-top:8px;margin-bottom:2px;">YOUR LEVEL</div>', unsafe_allow_html=True)
        level2=st.radio("", ["Beginner","Intermediate","Advance"], horizontal=True, key="d2_level", label_visibility="collapsed", index=None)
        st.markdown('<hr style="border:none;border-top:1px solid #e5e7eb;margin:10px 0 8px 0;">', unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:
            if st.button("← Back", use_container_width=True, key="d2_back"): ss.modal_step=1; st.rerun()
        with c2:
            if st.button("Create Session", use_container_width=True, type="primary", key="d2_create"):
                if deadline:
                    try: _dt2.datetime.strptime(deadline,"%Y-%m-%d")
                    except ValueError: st.warning("Format tanggal salah!"); st.stop()
                if level2 is None: st.warning("Pilih level dulu!")
                else:
                    today_str = _dt2.date.today().strftime("%d %b %Y")
                    new_session={"name":ss.modal_sname,"topics":ss.modal_topics or topics2.strip(),"level":level2,"deadline":deadline,"progress":0,"last_checked":today_str,"doc_text":"","doc_name":"","chat_messages":[],"plan_data":[],"plan_generated":False,"quiz_history":[],"streak":1}
                    ss.sessions.append(new_session)
                    uid=ss.get("user_id") or get_or_create_user(ss.get("user_name","User")); ss.user_id=uid
                    new_sid=create_session(uid,new_session); ss.sessions[-1]["id"]=new_sid
                    ss.just_created=True; ss.modal_step=0; st.rerun()

    if ss.modal_step==1: dialog_step1()
    elif ss.modal_step==2: dialog_step2()
