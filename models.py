import sqlite3

def create_tables():
    conn = sqlite3.connect("parking.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        email TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS slots (
        slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
        is_occupied BOOLEAN DEFAULT 0,
        vehicle_id INTEGER
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_plate TEXT,
        user_id INTEGER,
        parked_slot INTEGER,
        vehicle_type TEXT,
        entry_time DATETIME
    )""")

    cursor.execute("SELECT COUNT(*) FROM slots")
    count = cursor.fetchone()[0]
    if count == 0:
        for i in range(1, 11):
            cursor.execute("INSERT INTO slots (is_occupied, vehicle_id) VALUES (0, NULL)")

    conn.commit()
    conn.close()
