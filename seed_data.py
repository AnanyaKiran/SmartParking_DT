import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def seed_database():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()

    print("🚀 Seeding database...")

    # 1️⃣ Create 10 slots if they don’t exist
    print("🅿️  Creating slots...")
    for i in range(1, 11):
        cursor.execute("""
            INSERT INTO slots (slot_id, is_occupied, vehicle_id)
            VALUES (%s, FALSE, NULL)
            ON CONFLICT (slot_id) DO NOTHING;
        """, (i,))

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database seeded with 10 empty slots. No users or vehicles added.")
