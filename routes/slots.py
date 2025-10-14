from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import HTMLResponse
from database import get_db_connection
from datetime import datetime
import os
from dotenv import load_dotenv
from notify import send_sms_notification  # Twilio SMS function

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY")

router = APIRouter(prefix="/slots", tags=["Slots"])

# ------------------ GET SLOTS ------------------
@router.get("/")
def get_all_slots():
    conn = get_db_connection()
    slots = conn.execute("SELECT * FROM slots").fetchall()
    conn.close()
    return [dict(slot) for slot in slots]


@router.get("/vacant")
def get_vacant_slots():
    conn = get_db_connection()
    slots = conn.execute("SELECT * FROM slots WHERE is_occupied=0").fetchall()
    conn.close()
    return [dict(slot) for slot in slots]


@router.get("/filled")
def get_filled_slots():
    conn = get_db_connection()
    slots = conn.execute("SELECT * FROM slots WHERE is_occupied=1").fetchall()
    conn.close()
    return [dict(slot) for slot in slots]


# ------------------ OCCUPY SLOT ------------------
@router.post("/occupy/{slot_id}")
def occupy_slot(slot_id: int, vehicle_id: int, api_key: str = Header(None)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_db_connection()
    slot = conn.execute("SELECT is_occupied FROM slots WHERE slot_id=?", (slot_id,)).fetchone()

    if not slot:
        conn.close()
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot["is_occupied"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Slot already occupied")

    entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute(
        "UPDATE vehicles SET parked_slot=?, entry_time=? WHERE vehicle_id=?",
        (slot_id, entry_time, vehicle_id)
    )
    conn.execute(
        "UPDATE slots SET is_occupied=1, vehicle_id=? WHERE slot_id=?",
        (vehicle_id, slot_id)
    )
    conn.commit()

    vehicle = conn.execute(
        "SELECT vehicle_type, phone_number FROM vehicles WHERE vehicle_id=?",
        (vehicle_id,)
    ).fetchone()
    conn.close()

    # Send Twilio SMS with a clickable free-slot link
    if vehicle and vehicle["phone_number"]:
        cancel_url = f"http://127.0.0.1:8000/slots/free_by_user/{vehicle_id}"
        send_sms_notification(
            to_number=vehicle["phone_number"],
            slot_id=slot_id,
            vehicle_type=vehicle["vehicle_type"],
            cancel_url=cancel_url
        )
    else:
        print("[WARN] No phone number found; skipping SMS.")

    return {"message": f"Slot {slot_id} is now occupied", "entry_time": entry_time}


# ------------------ FREE SLOT ------------------
@router.post("/free/{slot_id}")
def free_slot(slot_id: int, api_key: str = Header(None)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_db_connection()
    slot = conn.execute("SELECT is_occupied, vehicle_id FROM slots WHERE slot_id=?", (slot_id,)).fetchone()

    if not slot:
        conn.close()
        raise HTTPException(status_code=404, detail="Slot not found")
    if not slot["is_occupied"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Slot already free")

    vehicle_id = slot["vehicle_id"]
    vehicle = conn.execute("SELECT entry_time, vehicle_type FROM vehicles WHERE vehicle_id=?", (vehicle_id,)).fetchone()

    entry_time = datetime.strptime(vehicle["entry_time"], "%Y-%m-%d %H:%M:%S")
    exit_time = datetime.now()
    hours_parked = max((exit_time - entry_time).total_seconds() / 3600, 0.01)

    rates = {"2-wheeler": 5, "4-wheeler": 10, "bicycle": 2}
    rate = rates.get(vehicle["vehicle_type"], 10)
    amount_due = round(hours_parked * rate, 2)

    conn.execute("UPDATE slots SET is_occupied=0, vehicle_id=NULL WHERE slot_id=?", (slot_id,))
    conn.execute("UPDATE vehicles SET parked_slot=NULL, entry_time=NULL WHERE vehicle_id=?", (vehicle_id,))
    conn.commit()
    conn.close()

    print(f"[NOTIFICATION] Slot {slot_id} freed. Amount due: ₹{amount_due}")
    return {"message": f"Slot {slot_id} is now free", "amount_due": amount_due}


# ------------------ FREE SLOT BY USER (from SMS link) ------------------
@router.get("/free_by_user/{vehicle_id}", response_class=HTMLResponse)
def free_slot_by_user(vehicle_id: int):
    """When user clicks link in SMS → this endpoint frees the slot."""
    conn = get_db_connection()
    vehicle = conn.execute("SELECT parked_slot, entry_time, vehicle_type FROM vehicles WHERE vehicle_id=?", (vehicle_id,)).fetchone()

    if not vehicle or not vehicle["parked_slot"]:
        conn.close()
        return HTMLResponse("<h3>⚠️ No active parking found for this vehicle.</h3>")

    slot_id = vehicle["parked_slot"]
    entry_time = datetime.strptime(vehicle["entry_time"], "%Y-%m-%d %H:%M:%S")
    exit_time = datetime.now()
    hours_parked = max((exit_time - entry_time).total_seconds() / 3600, 0.01)

    rates = {"2-wheeler": 5, "4-wheeler": 10, "bicycle": 2}
    rate = rates.get(vehicle["vehicle_type"], 10)
    amount_due = round(hours_parked * rate, 2)

    conn.execute("UPDATE slots SET is_occupied=0, vehicle_id=NULL WHERE slot_id=?", (slot_id,))
    conn.execute("UPDATE vehicles SET parked_slot=NULL, entry_time=NULL WHERE vehicle_id=?", (vehicle_id,))
    conn.commit()
    conn.close()

    return HTMLResponse(
        f"<h3>✅ Slot {slot_id} freed successfully!</h3>"
        f"<p>Amount due: ₹{amount_due}</p>"
        f"<p>Thank you for using Smart Parking!</p>"
    )
