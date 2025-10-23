from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from database import get_db_connection
import os
from dotenv import load_dotenv
from notify_whatsapp import send_whatsapp_notification

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY")

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

@router.post("/add")
def add_vehicle(
    license_plate: str,
    user_id: int,
    vehicle_type: str,
    phone_number: str,  # Add this parameter if you want to send WhatsApp
    background_tasks: BackgroundTasks,
    api_key: str = Header(None)
):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert vehicle
    cursor.execute(
        """
        INSERT INTO vehicles (license_plate, user_id, vehicle_type, phone_number)
        VALUES (%s, %s, %s, %s) RETURNING vehicle_id
        """,
        (license_plate, user_id, vehicle_type, phone_number)
    )
    vehicle_row = cursor.fetchone()
    vehicle_id = vehicle_row[0] if vehicle_row else None

    conn.commit()

    # ---------------- WhatsApp Notification ----------------
    if vehicle_id and phone_number:
        background_tasks.add_task(
            send_whatsapp_notification,
            to_number=phone_number,
            slot_id=0,  # no slot assigned yet
            vehicle_type=vehicle_type,
            vehicle_id=vehicle_id
        )

    cursor.close()
    conn.close()
    return {"message": f"Vehicle {license_plate} registered", "vehicle_id": vehicle_id}


@router.post("/remove/{vehicle_id}")
def remove_vehicle(vehicle_id: int, background_tasks: BackgroundTasks, api_key: str = Header(None)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT parked_slot FROM vehicles WHERE vehicle_id=%s", (vehicle_id,))
    vehicle = cursor.fetchone()
    if not vehicle:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if vehicle["parked_slot"]:
        cursor.execute(
            "UPDATE slots SET is_occupied=FALSE, vehicle_id=NULL WHERE slot_id=%s",
            (vehicle["parked_slot"],)
        )

    cursor.execute("DELETE FROM vehicles WHERE vehicle_id=%s", (vehicle_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"Vehicle {vehicle_id} removed"}
