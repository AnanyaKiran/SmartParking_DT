from fastapi import APIRouter, Header, HTTPException
from database import get_db_connection
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY")

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

@router.post("/add")
def add_vehicle(license_plate: str, user_id: int, vehicle_type: str, api_key: str = Header(None)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_db_connection()
    conn.execute("INSERT INTO vehicles (license_plate, user_id, vehicle_type) VALUES (?, ?, ?)", (license_plate, user_id, vehicle_type))
    conn.commit()
    conn.close()
    return {"message": f"Vehicle {license_plate} registered"}

@router.post("/remove/{vehicle_id}")
def remove_vehicle(vehicle_id: int, api_key: str = Header(None)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_db_connection()
    vehicle = conn.execute("SELECT parked_slot FROM vehicles WHERE vehicle_id=?", (vehicle_id,)).fetchone()
    if vehicle and vehicle["parked_slot"]:
        conn.execute("UPDATE slots SET is_occupied=0, vehicle_id=NULL WHERE slot_id=?", (vehicle["parked_slot"],))
    conn.execute("DELETE FROM vehicles WHERE vehicle_id=?", (vehicle_id,))
    conn.commit()
    conn.close()
    return {"message": f"Vehicle {vehicle_id} removed"}

def notify_user(phone, message):
    # For testing
    print(f"[NOTIFICATION to {phone}]: {message}")

    # OR real SMS using Twilio (optional)
