import streamlit as st

def show_dashboard():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600&family=Space+Grotesk:wght@600;700&display=swap');

    section[data-testid="stMain"] { background: linear-gradient(135deg, #1a1040 0%, #0f0a2e 60%, #1a1040 100%) !important; }
    .block-container { padding-top: 2rem !important; }

    * { font-family: 'Plus Jakarta Sans', sans-serif !important; }

    .db-greeting h1 {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 26px; font-weight: 700; color: #fff; margin: 0 0 4px;
    }
    .db-greeting p { font-size: 14px; color: rgba(255,255,255,0.45); margin: 0 0 28px; }

    .section-label {
        font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.35);
        text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 10px;
    }

    /* --- Stat cards --- */
    .stat-card {
        background: rgba(255,255,255,0.06);
        border: 0.5px solid rgba(255,255,255,0.1);
        border-radius: 14px; padding: 18px 16px;
    }
    .stat-icon {
        width: 38px; height: 38px; border-radius: 9px;
        display: flex; align-items: center; justify-content: center;
        font-size: 19px; margin-bottom: 12px;
    }
    .icon-purple { background: rgba(91,63,204,0.3); }
    .icon-teal   { background: rgba(29,158,117,0.22); }
    .icon-amber  { background: rgba(245,158,11,0.2); }
    .icon-coral  { background: rgba(239,68,68,0.18); }
    .stat-val {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 28px; font-weight: 700; color: #fff; line-height: 1; margin-bottom: 4px;
    }
    .stat-lbl { font-size: 12px; color: rgba(255,255,255,0.42); }

    /* --- Panel --- */
    .panel {
        background: rgba(255,255,255,0.05);
        border: 0.5px solid rgba(255,255,255,0.1);
        border-radius: 14px; padding: 20px;
        height: 100%;
    }
    .panel-title {
        font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.38);
        text-transform: uppercase; letter-spacing: 0.09em; margin-bottom: 16px;
    }

    /* --- Progress bars --- */
    .prog-row { margin-bottom: 15px; }
    .prog-header { display: flex; justify-content: space-between; font-size: 13px;
        color: rgba(255,255,255,0.78); margin-bottom: 6px; }
    .prog-pct { color: rgba(255,255,255,0.38); font-size: 12px; }
    .prog-track { height: 5px; background: rgba(255,255,255,0.09); border-radius: 99px; overflow: hidden; }
    .prog-fill { height: 100%; border-radius: 99px; }
    .fill-purple { background: linear-gradient(90deg,#7c3aed,#a78bfa); }
    .fill-teal   { background: linear-gradient(90deg,#0f766e,#34d399); }
    .fill-amber  { background: linear-gradient(90deg,#b45309,#fbbf24); }
    .fill-coral  { background: linear-gradient(90deg,#b91c1c,#f87171); }

    /* --- Activity feed --- */
    .act-item { display: flex; gap: 10px; margin-bottom: 13px; align-items: flex-start; }
    .act-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 5px; flex-shrink: 0; }
    .dot-purple { background: #a78bfa; }
    .dot-teal   { background: #34d399; }
    .dot-amber  { background: #fbbf24; }
    .act-text { font-size: 13px; color: rgba(255,255,255,0.72); line-height: 1.5; }
    .act-time { font-size: 11px; color: rgba(255,255,255,0.32); margin-top: 2px; }

    /* --- Quick access cards --- */
    .quick-card {
        background: rgba(255,255,255,0.05);
        border: 0.5px solid rgba(255,255,255,0.1);
        border-radius: 13px; padding: 18px 14px; text-align: center;
        transition: all 0.18s;
    }
    .quick-card:hover {
        background: rgba(91,63,204,0.25);
        border-color: rgba(167,139,250,0.4);
    }
    .quick-icon { font-size: 28px; margin-bottom: 8px; }
    .quick-week {
        display: inline-block; font-size: 10px; font-weight: 600;
        background: rgba(91,63,204,0.4); color: #c4b5fd;
        border-radius: 5px; padding: 2px 8px; margin-bottom: 7px; letter-spacing: 0.04em;
    }
    .quick-name { font-size: 13px; font-weight: 600; color: #fff; margin-bottom: 3px; }
    .quick-desc { font-size: 11px; color: rgba(255,255,255,0.38); }

    /* hide default streamlit elements */
    #MainMenu, footer, header { visibility: hidden; }
    div[data-testid="stVerticalBlock"] > div { gap: 0 !important; }
    </style>
    """, unsafe_allow_html=True)

    # ── Greeting ──────────────────────────────────────────────────────────────
    from datetime import datetime
    hari = ["Senin","Selasa","Rabu","Kamis","Jumat","Sabtu","Minggu"]
    bulan = ["Januari","Februari","Maret","April","Mei","Juni",
             "Juli","Agustus","September","Oktober","November","Desember"]
    now = datetime.now()
    tgl_str = f"{hari[now.weekday()]}, {now.day} {bulan[now.month-1]} {now.year}"

    st.markdown(f"""
    <div class="db-greeting">
        <h1>Selamat datang kembali 👋</h1>
        <p>{tgl_str} · Terus semangat belajar hari ini!</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Stats row ──────────────────────────────────────────────────────────────
    # Ambil dari session_state supaya angkanya dinamis
    total_qa    = len(st.session_state.get("qa_history", []))
    total_quiz  = st.session_state.get("quiz_count", 0)
    total_docs  = 1 if st.session_state.get("rag_text", "") else 0
    streak      = st.session_state.get("streak_days", 1)

    st.markdown('<div class="section-label">Statistik kamu</div>', unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4)
    stats = [
        (s1, "icon-purple", "💬", total_qa,   "Pertanyaan dijawab"),
        (s2, "icon-teal",   "📝", total_quiz,  "Quiz diselesaikan"),
        (s3, "icon-amber",  "📄", total_docs,  "Dokumen diupload"),
        (s4, "icon-coral",  "🔥", streak,      "Hari streak belajar"),
    ]
    for col, icon_cls, emoji, val, label in stats:
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-icon {icon_cls}">{emoji}</div>
                <div class="stat-val">{val}</div>
                <div class="stat-lbl">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Progress + Activity ────────────────────────────────────────────────────
    p_col, a_col = st.columns(2)

    with p_col:
        qa_pct   = min(100, total_qa * 10)
        quiz_pct = min(100, total_quiz * 10)
        plan_pct = 40 if st.session_state.get("study_plan") else 0
        rag_pct  = 80 if st.session_state.get("rag_text") else 0

        st.markdown(f"""
        <div class="panel">
            <div class="panel-title">Progress per fitur</div>
            <div class="prog-row">
                <div class="prog-header"><span>💬 Ask AI</span><span class="prog-pct">{qa_pct}%</span></div>
                <div class="prog-track"><div class="prog-fill fill-purple" style="width:{qa_pct}%"></div></div>
            </div>
            <div class="prog-row">
                <div class="prog-header"><span>📝 Quiz</span><span class="prog-pct">{quiz_pct}%</span></div>
                <div class="prog-track"><div class="prog-fill fill-teal" style="width:{quiz_pct}%"></div></div>
            </div>
            <div class="prog-row">
                <div class="prog-header"><span>📚 Study Plan</span><span class="prog-pct">{plan_pct}%</span></div>
                <div class="prog-track"><div class="prog-fill fill-amber" style="width:{plan_pct}%"></div></div>
            </div>
            <div class="prog-row">
                <div class="prog-header"><span>📄 RAG</span><span class="prog-pct">{rag_pct}%</span></div>
                <div class="prog-track"><div class="prog-fill fill-coral" style="width:{rag_pct}%"></div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with a_col:
        # Bangun aktivitas dari session_state
        activities = []
        qa_hist  = st.session_state.get("qa_history", [])
        rag_hist = st.session_state.get("rag_history", [])

        if qa_hist:
            last_q = qa_hist[-1].get("question", "...")[:40]
            activities.append(("dot-purple", f"Bertanya: <b>{last_q}…</b>", "Baru saja · Ask AI"))
        if st.session_state.get("rag_filename"):
            fname = st.session_state.get("rag_filename", "dokumen")
            activities.append(("dot-amber", f"Upload dokumen <b>{fname}</b>", "Sesi ini · RAG"))
        if rag_hist:
            activities.append(("dot-teal", "Bertanya dari dokumen yang diupload", "Sesi ini · RAG"))
        if st.session_state.get("study_plan"):
            activities.append(("dot-purple", "Membuat study plan baru", "Sesi ini · Study Plan"))

        if not activities:
            activities = [
                ("dot-purple", "Belum ada aktivitas hari ini", "Mulai dengan Ask AI!"),
            ]

        items_html = ""
        for dot, text, time in activities[:4]:
            items_html += f"""
            <div class="act-item">
                <div class="act-dot {dot}"></div>
                <div>
                    <div class="act-text">{text}</div>
                    <div class="act-time">{time}</div>
                </div>
            </div>"""

        st.markdown(f"""
        <div class="panel">
            <div class="panel-title">Aktivitas terakhir</div>
            {items_html}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Quick Access ───────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Quick access fitur</div>', unsafe_allow_html=True)

    features = [
        ("💬", "Week 2", "Ask AI",       "Tanya apa saja dengan AI",         "ask_ai"),
        ("📚", "Week 3", "Study Plan",   "Buat rencana belajar personal",     "study_plan"),
        ("📝", "Week 4", "Quiz",         "Generate soal MCQ otomatis",        "quiz"),
        ("📄", "Week 5", "RAG",          "Upload PDF, tanya dari dokumen",    "rag"),
    ]

    q1, q2, q3, q4 = st.columns(4)
    cols = [q1, q2, q3, q4]

    for i, (emoji, week, name, desc, key) in enumerate(features):
        with cols[i]:
            st.markdown(f"""
            <div class="quick-card">
                <div class="quick-icon">{emoji}</div>
                <div class="quick-week">{week}</div>
                <div class="quick-name">{name}</div>
                <div class="quick-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Buka {name}", key=f"dash_btn_{key}", use_container_width=True):
                st.session_state.active_page = name.lower().replace(" ", "_")
                st.rerun()