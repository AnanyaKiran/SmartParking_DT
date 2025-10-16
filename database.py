import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Environment variables (set these in your .env file)
DB_NAME = os.getenv("POSTGRES_DB", "parking_db")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "Anu@1234")  # ⚠️ No < >
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# Database connection
def get_db_connection():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        cursor_factory=RealDictCursor
    )
    return conn

# Get slot by ID
def get_slot_by_id(slot_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT slot_id, is_occupied, vehicle_id FROM slots WHERE slot_id = %s;", (slot_id,))
    slot = cursor.fetchone()
    cursor.close()
    conn.close()
    return slot

# Free a slot
def free_slot(slot_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE slots SET is_occupied = FALSE, vehicle_id = NULL WHERE slot_id = %s;", (slot_id,))
    conn.commit()
    cursor.close()
    conn.close()
