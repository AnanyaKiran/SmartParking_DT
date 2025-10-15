from fastapi import APIRouter, Header, HTTPException
from database import get_db_connection
from datetime import datetime
from fastapi.responses import HTMLResponse
from notify import send_sms_notification
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY")

router = APIRouter(prefix="/slots", tags=["Slots"])

# ------------------ GET SLOTS ------------------
@router.get("/")
def get_all_slots():
    conn = get_db_connection()
    slots = conn.cursor()
    slots.execute("SELECT * FROM slots")
    data = slots.fetchall()
    slots.close()
    conn.close()
    return data

@router.get("/vacant")
def get_vacant_slots():
    conn = get_db_connection()
    slots = conn.cursor()
    slots.execute("SELECT * FROM slots WHERE is_occupied=FALSE")
    data = slots.fetchall()
    slots.close()
    conn.close()
    return data

@router.get("/filled")
def get_filled_slots():
    conn = get_db_connection()
    slots = conn.cursor()
    slots.execute("SELECT * FROM slots WHERE is_occupied=TRUE")
    data = slots.fetchall()
    slots.close()
    conn.close()
    return data

# ------------------ OCCUPY SLOT ------------------
@router.post("/occupy/{slot_id}")
def occupy_slot(slot_id: int, vehicle_id: int, api_key: str = Header(None)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT is_occupied FROM slots WHERE slot_id=%s", (slot_id,))
    slot = cursor.fetchone()
    if not slot:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot["is_occupied"]:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Slot already occupied")

    entry_time = datetime.now()
    cursor.execute(
        "UPDATE vehicles SET parked_slot=%s, entry_time=%s WHERE vehicle_id=%s",
        (slot_id, entry_time, vehicle_id)
    )
    cursor.execute(
        "UPDATE slots SET is_occupied=TRUE, vehicle_id=%s WHERE slot_id=%s",
        (vehicle_id, slot_id)
    )

    cursor.execute("SELECT vehicle_type, phone_number FROM vehicles WHERE vehicle_id=%s", (vehicle_id,))
    vehicle = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    if vehicle and vehicle["phone_number"]:
        send_sms_notification(
            to_number=vehicle["phone_number"],
            slot_id=slot_id,
            vehicle_type=vehicle["vehicle_type"],
            vehicle_id=vehicle_id
        )

    return {"message": f"Slot {slot_id} occupied", "entry_time": entry_time, "vehicle_id": vehicle_id}

# ------------------ FREE SLOT ------------------
@router.post("/free/{slot_id}")
def free_slot(slot_id: int, api_key: str = Header(None)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch slot details
    cursor.execute("SELECT is_occupied, vehicle_id FROM slots WHERE slot_id=%s", (slot_id,))
    slot = cursor.fetchone()
    if not slot:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Slot not found")
    if not slot["is_occupied"]:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Slot already free")

    vehicle_id = slot["vehicle_id"]

    # Fetch vehicle details
    cursor.execute("SELECT entry_time, vehicle_type FROM vehicles WHERE vehicle_id=%s", (vehicle_id,))
    vehicle = cursor.fetchone()

    entry_time = vehicle["entry_time"]
    exit_time = datetime.now()
    hours_parked = max((exit_time - entry_time).total_seconds() / 3600, 0.01)

    rates = {"2-wheeler": 5, "4-wheeler": 10, "bicycle": 2}
    rate = rates.get(vehicle["vehicle_type"], 10)
    amount_due = round(hours_parked * rate, 2)

    # Free the slot
    cursor.execute("UPDATE slots SET is_occupied=FALSE, vehicle_id=NULL WHERE slot_id=%s", (slot_id,))
    cursor.execute("UPDATE vehicles SET parked_slot=NULL, entry_time=NULL WHERE vehicle_id=%s", (vehicle_id,))
    conn.commit()
    cursor.close()
    conn.close()

    print(f"[NOTIFICATION] Slot {slot_id} freed. Amount due: ₹{amount_due}")

    return {
        "message": f"Slot {slot_id} is now free",
        "hours_parked": round(hours_parked, 2),
        "amount_due": amount_due
    }


@router.get("/free_by_user/{vehicle_id}", response_class=HTMLResponse)
def free_slot_by_user(vehicle_id: int):
    """When user clicks SMS link → frees the slot and shows HTML response."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT parked_slot, entry_time, vehicle_type FROM vehicles WHERE vehicle_id=%s", (vehicle_id,))
    vehicle = cursor.fetchone()

    if not vehicle or not vehicle["parked_slot"]:
        cursor.close()
        conn.close()
        return HTMLResponse("<h3>⚠️ No active parking found for this vehicle.</h3>")

    slot_id = vehicle["parked_slot"]
    entry_time = vehicle["entry_time"]
    exit_time = datetime.now()
    hours_parked = max((exit_time - entry_time).total_seconds() / 3600, 0.01)

    rates = {"2-wheeler": 5, "4-wheeler": 10, "bicycle": 2}
    rate = rates.get(vehicle["vehicle_type"], 10)
    amount_due = round(hours_parked * rate, 2)

    # Free slot
    cursor.execute("UPDATE slots SET is_occupied=FALSE, vehicle_id=NULL WHERE slot_id=%s", (slot_id,))
    cursor.execute("UPDATE vehicles SET parked_slot=NULL, entry_time=NULL WHERE vehicle_id=%s", (vehicle_id,))
    conn.commit()
    cursor.close()
    conn.close()

    html_response = f"""
    <h3>✅ Slot {slot_id} freed successfully!</h3>
    <p>Amount due: ₹{amount_due}</p>
    <p>Thank you for using Smart Parking!</p>
    """
    return HTMLResponse(html_response)
