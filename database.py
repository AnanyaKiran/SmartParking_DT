import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from dotenv import load_dotenv
import atexit

# Load environment variables
load_dotenv()

# Prefer DATABASE_URL (Render usually provides this)
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallbacks (for local dev)
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASS = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# Global pool
DB_POOL = None


def init_db_pool(minconn=1, maxconn=10):
    """
    Initializes a connection pool (only once).
    On Render, multiple workers may start at once — so keep pool small.
    """
    global DB_POOL
    if DB_POOL:
        return DB_POOL

    try:
        if DATABASE_URL:
            DB_POOL = pool.ThreadedConnectionPool(
                minconn, maxconn,
                DATABASE_URL,
                cursor_factory=RealDictCursor
            )
        else:
            DB_POOL = pool.ThreadedConnectionPool(
                minconn, maxconn,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                host=DB_HOST,
                port=DB_PORT,
                cursor_factory=RealDictCursor
            )
        print("✅ Database connection pool initialized.")
        return DB_POOL
    except Exception as e:
        print("❌ Database pool initialization failed:", e)
        raise


def get_db_connection():
    """
    Gets a connection from the pool. Initializes the pool if needed.
    """
    global DB_POOL
    if DB_POOL is None:
        init_db_pool()
    try:
        conn = DB_POOL.getconn()
        return conn
    except Exception as e:
        print("❌ Failed to get DB connection from pool:", e)
        raise


def release_db_connection(conn):
    """
    Returns a connection to the pool.
    """
    global DB_POOL
    if DB_POOL and conn:
        DB_POOL.putconn(conn)


# Automatically close pool when app shuts down
@atexit.register
def close_db_pool():
    global DB_POOL
    if DB_POOL:
        DB_POOL.closeall()
        print("🧹 Database connection pool closed.")


# --- Optional helper functions (your existing ones, using the pool safely) ---

def get_all_slots():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT slot_id, is_occupied, vehicle_id FROM slots ORDER BY slot_id;")
            slots = cursor.fetchall()
            return slots
    finally:
        release_db_connection(conn)


def get_slot_by_id(slot_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT slot_id, is_occupied, vehicle_id FROM slots WHERE slot_id = %s;",
                (slot_id,)
            )
            slot = cursor.fetchone()
            return slot
    finally:
        release_db_connection(conn)


def free_slot(slot_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE slots SET is_occupied = FALSE, vehicle_id = NULL WHERE slot_id = %s RETURNING *;",
                (slot_id,)
            )
            conn.commit()
            return cursor.fetchone()
    finally:
        release_db_connection(conn)
