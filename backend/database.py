import os
import sqlite3
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "datasanitizer.db")

def get_db_connection() -> sqlite3.Connection:
    """Tao va tra ve connection den co so du lieu SQLite."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def execute_query(sql: str, params: tuple = ()) -> int:
    """Thuc thi lenh INSERT/UPDATE/DELETE co parameter binding chong SQL Injection."""
    with get_db_connection() as conn:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.lastrowid

def fetch_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """Truy van va tra ve 1 ban ghi duoi dang dictionary."""
    with get_db_connection() as conn:
        cursor = conn.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None

def fetch_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Truy van va tra ve danh sach cac ban ghi."""
    with get_db_connection() as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

# ----------------- SECURITY & AUTH HELPERS -----------------
def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Bam mat khau bang PBKDF2-HMAC-SHA256 voi salt ngau nhien."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()
    return hashed, salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Kiem tra mat khau nhap vao co khop voi hash trong DB hay khong."""
    check_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(check_hash, password_hash)

def create_session(user_id: int, duration_days: int = 7) -> str:
    """Sinh session token ngau nhien va luu vao bang sessions."""
    token = secrets.token_hex(32)
    expires_at = datetime.utcnow() + timedelta(days=duration_days)
    execute_query(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at.isoformat())
    )
    return token

def get_user_by_session(token: str) -> Optional[Dict[str, Any]]:
    """Lay thong tin user hien tai tu session token (neu chua het han)."""
    now = datetime.utcnow().isoformat()
    sql = """
        SELECT u.id, u.email, u.username, u.created_at
        FROM users u
        JOIN sessions s ON u.id = s.user_id
        WHERE s.token = ? AND s.expires_at > ?
    """
    return fetch_one(sql, (token, now))

def delete_session(token: str) -> None:
    """Xoa session token khi nguoi dung logout."""
    execute_query("DELETE FROM sessions WHERE token = ?", (token,))

# ----------------- DATABASE INITIALIZATION -----------------
def init_db() -> None:
    """Khoi tao cac bang CSDL SQLite va nap cac Recipe mac dinh neu chua co."""
    with get_db_connection() as conn:
        # 1. Bang users
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Bang sessions
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 3. Bang pipeline_recipes
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                steps_json TEXT NOT NULL,
                is_public INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)

        # 4. Bang pipeline_history
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_id TEXT NOT NULL,
                stats_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        conn.commit()

    # Nap san 3 Recipe cong thuc chuan mau
    seed_default_recipes()

def seed_default_recipes() -> None:
    """Nap 3 cong thuc chuan cua he thong vao bang pipeline_recipes."""
    default_recipes = [
        {
            "name": "Bộ lọc dữ liệu khuyết thiếu & Ngoại lai",
            "description": "Chuẩn hóa Null, điền khuyết thiếu bằng Median và cắt tỉa ngoại lai IQR 1.5",
            "steps": [
                {"type": "standardize_nulls", "config": {}},
                {"type": "imputation", "config": {"strategy": "median", "columns": []}},
                {"type": "outlier", "config": {"method": "iqr", "threshold": 1.5, "handling": "remove", "columns": []}}
            ]
        },
        {
            "name": "Chuẩn hóa định dạng số & Khử trùng lặp",
            "description": "Làm sạch tiền tệ, xóa trùng lặp và làm tròn số thập phân",
            "steps": [
                {"type": "drop_duplicates", "config": {}},
                {"type": "clean_numeric", "config": {"columns": []}},
                {"type": "round", "config": {"decimals": 2, "to_integer": False, "columns": []}}
            ]
        },
        {
            "name": "Pipeline Chuẩn bị cho Machine Learning",
            "description": "Điền khuyết thiếu Median, mã hóa One-Hot và chuẩn hóa thang đo MinMax",
            "steps": [
                {"type": "imputation", "config": {"strategy": "median", "columns": []}},
                {"type": "encoding", "config": {"method": "one_hot", "columns": []}},
                {"type": "scaling", "config": {"method": "min_max", "columns": []}}
            ]
        }
    ]

    for rec in default_recipes:
        exists = fetch_one("SELECT id FROM pipeline_recipes WHERE name = ? AND is_public = 1", (rec["name"],))
        if not exists:
            execute_query(
                "INSERT INTO pipeline_recipes (user_id, name, description, steps_json, is_public) VALUES (?, ?, ?, ?, ?)",
                (None, rec["name"], rec["description"], json.dumps(rec["steps"], ensure_ascii=False), 1)
            )

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
