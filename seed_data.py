import psycopg2
from dotenv import load_dotenv
import os
from datetime import datetime

# Load .env variables
load_dotenv()

# Connect to your Render database
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

print("🚀 Seeding database...")

# 1️⃣ Create 10 slots (if not already there)
print("🅿️  Creating slots...")
for i in range(1, 11):
    cursor.execute("""
        INSERT INTO slots (slot_id, is_occupied, vehicle_id)
        VALUES (%s, FALSE, NULL)
        ON CONFLICT (slot_id) DO NOTHING;
    """, (i,))

# 2️⃣ Create 10 users
print("👤  Adding users...")
users = [
    ("Ananya Kiran", "9876543210"),
    ("Ravi Kumar", "9123456780"),
    ("Priya Sharma", "9988776655"),
    ("Rahul Mehta", "9012345678"),
    ("Sneha Iyer", "9345678901"),
    ("Ajay M U", "9912345678"),
    ("Ashwini R", "9988112233"),
    ("Arun Vijay", "9988774455"),
    ("Archana Ram", "9012348765"),
    ("Mani Sanjeev", "9874512360")
]

user_ids = []
for name, phone in users:
    cursor.execute("""
        INSERT INTO users (user_name, phone)
        VALUES (%s, %s)
        RETURNING user_id;
    """, (name, phone))
    user_ids.append(cursor.fetchone()[0])

# 3️⃣ Create 10 vehicles (each user gets one)
print("🚗  Registering vehicles...")
vehicles = [
    ("KA-05-AB-1234", "Car"),
    ("KA-03-MN-4567", "Bike"),
    ("KA-01-XY-8901", "Scooter"),
    ("KA-02-DS-5678", "SUV"),
    ("KA-04-QW-3456", "Scooter"),
    ("KA-05-PQ-4321", "Car"),
    ("KA-04-YZ-6548", "Bicycle"),
    ("KA-03-RR-9523", "Car"),
    ("KA-02-SP-0007", "Honda"),
    ("KA-01-NV-4528", "Bicycle")
]

vehicle_ids = []
for i, (plate, vtype) in enumerate(vehicles):
    slot_id = i + 1  # assign slot 1–10
    user_id = user_ids[i]
    phone = users[i][1]
    
    cursor.execute("""
        INSERT INTO vehicles (license_plate, user_id, parked_slot, vehicle_type, phone_number, entry_time)
        VALUES (%s, %s, %s, %s, %s, NOW())
        RETURNING vehicle_id;
    """, (plate, user_id, slot_id, vtype, phone))
    
    vehicle_id = cursor.fetchone()[0]
    vehicle_ids.append(vehicle_id)

    # Update slot as occupied
    cursor.execute("""
        UPDATE slots
        SET is_occupied = TRUE, vehicle_id = %s
        WHERE slot_id = %s;
    """, (vehicle_id, slot_id))

conn.commit()

print("\n✅ Database Seeded Successfully!\n")
print("👥 Users created:", len(user_ids))
print("🚘 Vehicles created:", len(vehicle_ids))
print("🅿️ Total slots:", 10)
print("\n✨ User 1 linked to Vehicle 1 and Slot 1")

cursor.close()
conn.close()
print("🎉 Done!")
