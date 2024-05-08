import sqlite3
from flask import g

DATABASE = 'qna.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_api_key(key_name):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT key_value FROM api_keys WHERE key_name = ?", (key_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None

def init_db(app):
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_input_text (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text_type TEXT,
                text TEXT,
                UNIQUE(text_type)
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key_name TEXT PRIMARY KEY,
                key_value TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT,
                answer TEXT,
                question_session_id TEXT,
                asked_on DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        db.commit()
    app.teardown_appcontext(close_connection)
