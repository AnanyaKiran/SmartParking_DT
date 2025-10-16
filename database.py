import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ✅ Prefer DATABASE_URL if provided (Render usually gives this)
DATABASE_URL = os.getenv("DATABASE_URL")

# Otherwise, fall back to manual connection details
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASS = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")


def get_db_connection():
    """Establish connection to PostgreSQL (Render/Railway compatible)."""
    try:
        if DATABASE_URL:
            # Render uses DATABASE_URL format
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        else:
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                host=DB_HOST,
                port=DB_PORT,
                cursor_factory=RealDictCursor
            )
        return conn
    except Exception as e:
        print("❌ Database connection failed:", e)
        raise


def get_slot_by_id(slot_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT slot_id, is_occupied, vehicle_id FROM slots WHERE slot_id = %s;",
        (slot_id,)
    )
    slot = cursor.fetchone()
    cursor.close()
    conn.close()
    return slot


def free_slot(slot_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE slots SET is_occupied = FALSE, vehicle_id = NULL WHERE slot_id = %s;",
        (slot_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()
