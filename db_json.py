# db_json.py — Manajemen database berbasis file JSON untuk LearnAI
import json
import os
from datetime import datetime
from typing import List, Dict, Any

# Nama file database lokal
DB_FILE = "learnai_data.json"


def init_db():
    """
    Menginisialisasi file database JSON jika belum ada.
    Membuat struktur data awal dengan tabel: users, sessions,
    quiz_history, study_plans, chats, chat_history, dan next_ids.
    """
    if not os.path.exists(DB_FILE):
        default_data = {
            "users": [],
            "sessions": [],
            "quiz_history": [],
            "study_plans": [],
            "chats": {},
            "chat_history": {},
            "next_ids": {
                "user_id": 1,
                "session_id": 1,
                "quiz_id": 1,
                "plan_id": 1
            }
        }
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=2, ensure_ascii=False)


def load_data() -> Dict:
    """
    Membaca dan mengembalikan seluruh data dari file JSON database.

    Returns:
        dict: Seluruh data yang tersimpan di database.
    """
    init_db()
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: Dict):
    """
    Menyimpan data ke file JSON database.

    Args:
        data (dict): Data lengkap yang akan disimpan.
    """
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============= USER =============

def get_or_create_user(username: str) -> int:
    """
    Mengambil ID user berdasarkan username. Jika belum ada, buat user baru.

    Args:
        username (str): Nama pengguna.

    Returns:
        int: ID user yang ditemukan atau baru dibuat.
    """
    data = load_data()
    for user in data["users"]:
        if user["username"] == username:
            return user["id"]
    new_id = data["next_ids"]["user_id"]
    data["users"].append({
        "id": new_id,
        "username": username,
        "created_at": datetime.now().isoformat()
    })
    data["next_ids"]["user_id"] = new_id + 1
    save_data(data)
    return new_id


def get_user_sessions(user_id: int) -> List[Dict]:
    """
    Mengambil semua sesi belajar milik user beserta riwayat kuis dan rencana belajarnya.

    Args:
        user_id (int): ID user.

    Returns:
        list: Daftar sesi beserta data quiz_history dan plan_data.
    """
    data = load_data()
    sessions = [s for s in data["sessions"] if s["user_id"] == user_id]
    for session in sessions:
        session["quiz_history"] = [q for q in data["quiz_history"] if q["session_id"] == session["id"]]
        session["plan_data"] = [p for p in data["study_plans"] if p["session_id"] == session["id"]]
    return sessions


# ============= SESSION =============

def create_session(user_id: int, session_data: Dict[str, Any]) -> int:
    """
    Membuat sesi belajar baru untuk user, termasuk menyimpan
    quiz_history dan plan_data jika ada.

    Args:
        user_id (int): ID user pemilik sesi.
        session_data (dict): Data sesi yang akan disimpan.

    Returns:
        int: ID sesi yang baru dibuat.
    """
    data = load_data()
    new_id = data["next_ids"]["session_id"]
    new_session = {
        "id": new_id,
        "user_id": user_id,
        "name": session_data.get("name", ""),
        "topics": session_data.get("topics", ""),
        "level": session_data.get("level", ""),
        "deadline": session_data.get("deadline", ""),
        "progress": session_data.get("progress", 0),
        "last_checked": session_data.get("last_checked", datetime.now().strftime("%d %b %Y")),
        "doc_text": session_data.get("doc_text", ""),
        "doc_name": session_data.get("doc_name", ""),
        "chapters": session_data.get("chapters", []),
        "streak": session_data.get("streak", 1),
        "plan_generated": session_data.get("plan_generated", False),
        "created_at": datetime.now().isoformat()
    }
    data["sessions"].append(new_session)
    data["next_ids"]["session_id"] = new_id + 1
    for quiz in session_data.get("quiz_history", []):
        quiz_id = data["next_ids"]["quiz_id"]
        data["quiz_history"].append({"id": quiz_id, "session_id": new_id, "topic": quiz.get("topic", ""), "level": quiz.get("level", ""), "score": quiz.get("score", 0), "analysis": quiz.get("analysis", ""), "created_at": datetime.now().isoformat()})
        data["next_ids"]["quiz_id"] = quiz_id + 1
    for plan in session_data.get("plan_data", []):
        plan_id = data["next_ids"]["plan_id"]
        data["study_plans"].append({"id": plan_id, "session_id": new_id, "Hari": plan.get("Hari", ""), "Jam": plan.get("Jam", ""), "Materi": plan.get("Materi", ""), "Penjelasan": plan.get("Penjelasan", ""), "Selesai": plan.get("Selesai", False)})
        data["next_ids"]["plan_id"] = plan_id + 1
    save_data(data)
    return new_id


def update_session(session_id: int, session_data: Dict[str, Any]):
    """
    Memperbarui data sesi yang sudah ada, termasuk mengganti
    quiz_history dan plan_data dengan data terbaru.

    Args:
        session_id (int): ID sesi yang akan diperbarui.
        session_data (dict): Data baru untuk sesi tersebut.
    """
    data = load_data()
    for i, session in enumerate(data["sessions"]):
        if session["id"] == session_id:
            for field in ["name","topics","level","deadline","progress","last_checked","doc_text","doc_name","chapters","streak","plan_generated"]:
                if field in session_data:
                    data["sessions"][i][field] = session_data[field]
            break
    data["quiz_history"] = [q for q in data["quiz_history"] if q["session_id"] != session_id]
    for quiz in session_data.get("quiz_history", []):
        quiz_id = data["next_ids"]["quiz_id"]
        data["quiz_history"].append({"id": quiz_id, "session_id": session_id, "topic": quiz.get("topic", ""), "level": quiz.get("level", ""), "score": quiz.get("score", 0), "analysis": quiz.get("analysis", ""), "created_at": datetime.now().isoformat()})
        data["next_ids"]["quiz_id"] = quiz_id + 1
    data["study_plans"] = [p for p in data["study_plans"] if p["session_id"] != session_id]
    for plan in session_data.get("plan_data", []):
        plan_id = data["next_ids"]["plan_id"]
        data["study_plans"].append({"id": plan_id, "session_id": session_id, "Hari": plan.get("Hari", ""), "Jam": plan.get("Jam", ""), "Materi": plan.get("Materi", ""), "Penjelasan": plan.get("Penjelasan", ""), "Selesai": plan.get("Selesai", False)})
        data["next_ids"]["plan_id"] = plan_id + 1
    save_data(data)


def delete_session(session_id: int):
    """
    Menghapus sesi beserta semua quiz_history dan study_plans yang terkait.

    Args:
        session_id (int): ID sesi yang akan dihapus.
    """
    data = load_data()
    data["sessions"] = [s for s in data["sessions"] if s["id"] != session_id]
    data["quiz_history"] = [q for q in data["quiz_history"] if q["session_id"] != session_id]
    data["study_plans"] = [p for p in data["study_plans"] if p["session_id"] != session_id]
    save_data(data)


def sync_session_to_db(user_id: int, sessions: List[Dict]):
    """
    Sinkronisasi daftar sesi dari state aplikasi ke database.
    Sesi yang sudah ada akan diupdate, sesi baru akan dibuat,
    dan sesi yang dihapus dari state akan dihapus dari database.

    Args:
        user_id (int): ID user pemilik sesi.
        sessions (list): Daftar sesi terkini dari state aplikasi.
    """
    data = load_data()
    existing_ids = [s["id"] for s in data["sessions"] if s["user_id"] == user_id]
    for session in sessions:
        session_id = session.get("id")
        if session_id and session_id in existing_ids:
            update_session(session_id, session)
        else:
            session_copy = {k: v for k, v in session.items() if k != "id"}
            create_session(user_id, session_copy)
    current_ids = [s.get("id") for s in sessions if s.get("id")]
    for old_id in existing_ids:
        if old_id not in current_ids:
            delete_session(old_id)


# Inisialisasi database saat modul pertama kali diimport
init_db()
