import psycopg2
from database import get_db_connection

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1️⃣ Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id SERIAL PRIMARY KEY,
        user_name VARCHAR(100),
        phone VARCHAR(20)
    );
    """)

    # 2️⃣ Slots table first (vehicles references slots)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS slots (
        slot_id SERIAL PRIMARY KEY,
        is_occupied BOOLEAN DEFAULT FALSE,
        vehicle_id INTEGER
    );
    """)

    # 3️⃣ Vehicles table with foreign keys
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        vehicle_id SERIAL PRIMARY KEY,
        license_plate VARCHAR(50),
        user_id INTEGER REFERENCES users(user_id),
        parked_slot INTEGER REFERENCES slots(slot_id) ON DELETE SET NULL,
        vehicle_type VARCHAR(50),
        phone_number VARCHAR(20),
        entry_time TIMESTAMP
    );
    """)

    # 4️⃣ Pre-populate 10 slots if empty
    cursor.execute("SELECT COUNT(*) FROM slots;")
    result = cursor.fetchone()
    count = result["count"] if result else 0

    if count == 0:
        for _ in range(10):
            cursor.execute(
                "INSERT INTO slots (is_occupied, vehicle_id) VALUES (FALSE, NULL);"
            )

    conn.commit()
    cursor.close()
    conn.close()
