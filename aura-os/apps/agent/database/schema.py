import sqlite3
import os

# Default DB Path in the agent's root directory
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aura.db")

def get_db_path() -> str:
    """Returns the absolute path to the SQLite database."""
    return os.getenv("SQLITE_DB_PATH", DB_PATH)

def init_db():
    """Initializes the database schema if tables do not exist."""
    db_file = get_db_path()
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Task Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        user_request TEXT NOT NULL,
        state TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Plan Steps Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plan_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        step_number INTEGER NOT NULL,
        description TEXT NOT NULL,
        tool_name TEXT,
        tool_args TEXT,      
        status TEXT NOT NULL, 
        result TEXT,         
        verification_result TEXT,
        FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
    );
    """)
    
    # Audit Log Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        task_id TEXT,
        tool_name TEXT NOT NULL,
        arguments TEXT NOT NULL,       
        result TEXT,                   
        risk_level TEXT NOT NULL,      
        permission_status TEXT NOT NULL 
    );
    """)
    
    # Memory Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        memory_type TEXT NOT NULL,
        session_id TEXT,
        key_name TEXT NOT NULL,
        value TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    conn.commit()
    conn.close()
    print(f"[Database] SQLite DB initialized at: {db_file}")

if __name__ == "__main__":
    init_db()
