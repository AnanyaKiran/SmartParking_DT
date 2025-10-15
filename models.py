from database import get_db_connection

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id SERIAL PRIMARY KEY,
        name TEXT,
        phone TEXT,
        email TEXT
    )
    """)

    # Slots table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS slots (
        slot_id SERIAL PRIMARY KEY,
        is_occupied BOOLEAN DEFAULT FALSE,
        vehicle_id INT
    )
    """)

    # Vehicles table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        vehicle_id SERIAL PRIMARY KEY,
        license_plate TEXT,
        user_id INT,
        parked_slot INT,
        vehicle_type TEXT,
        phone_number TEXT,
        entry_time TIMESTAMP
    )
    """)

    # Optional: Pre-populate 10 slots for demo
    cursor.execute("SELECT COUNT(*) FROM slots")
    count = cursor.fetchone()[0]
    if count == 0:
        for _ in range(10):
            cursor.execute("INSERT INTO slots (is_occupied, vehicle_id) VALUES (FALSE, NULL)")

    conn.commit()
    cursor.close()
    conn.close()
