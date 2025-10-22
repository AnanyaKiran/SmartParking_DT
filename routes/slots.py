# routes/slots.py
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Header
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import get_db_connection
from datetime import datetime
from notify import send_sms_notification
import os
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY")

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ------------------ Utility Function ------------------
def fetch_as_dict(cursor):
    """Convert DB rows into list of dictionaries"""
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ------------------ GET ALL SLOTS ------------------
@router.get("/")
def get_slots():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT slot_id, is_occupied, vehicle_id FROM slots ORDER BY slot_id;")
        slots = cursor.fetchall()
        cursor.close()
        conn.close()
        return slots
    except Exception as e:
        print("Error fetching slots:", e)
        return []


# ------------------ GET VACANT SLOTS ------------------
@router.get("/vacant")
def get_vacant_slots():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT slot_id, slot_name, is_occupied, vehicle_id
            FROM slots WHERE is_occupied=FALSE ORDER BY slot_id
        """)
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return data
    except Exception as e:
        print("Error fetching vacant slots:", e)
        return []


# ------------------ GET FILLED SLOTS ------------------
@router.get("/filled")
def get_filled_slots():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT slot_id, slot_name, is_occupied, vehicle_id
            FROM slots WHERE is_occupied=TRUE ORDER BY slot_id
        """)
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return data
    except Exception as e:
        print("Error fetching filled slots:", e)
        return []


# ------------------ OCCUPY SLOT ------------------
@router.post("/occupy/{slot_id}")
def occupy_slot(slot_id: int, vehicle_id: int, background_tasks: BackgroundTasks, api_key: str = Header(None)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check slot availability
    cursor.execute("SELECT is_occupied FROM slots WHERE slot_id=%s", (slot_id,))
    slot = cursor.fetchone()
    if not slot:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot[0]:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Slot already occupied")

    # Update vehicle and slot
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

    # Send SMS in background
    if vehicle and vehicle[1]:
        send_sms_notification(
            to_number=vehicle[1],
            slot_id=slot_id,
            vehicle_type=vehicle[0],
            vehicle_id=vehicle_id,
            background_tasks=background_tasks
        )

    return {
        "message": f"Slot {slot_id} occupied successfully",
        "entry_time": entry_time.isoformat(),
        "vehicle_id": vehicle_id
    }


# ------------------ FREE SLOT (Admin/API) ------------------
@router.post("/free/{slot_id}")
def free_slot(slot_id: int, api_key: str = Header(None)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_occupied, vehicle_id FROM slots WHERE slot_id=%s", (slot_id,))
    slot = cursor.fetchone()
    if not slot:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Slot not found")
    if not slot[0]:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Slot already free")

    vehicle_id = slot[1]
    cursor.execute("SELECT entry_time, vehicle_type FROM vehicles WHERE vehicle_id=%s", (vehicle_id,))
    vehicle = cursor.fetchone()

    entry_time = vehicle[0]
    exit_time = datetime.now()
    hours_parked = max((exit_time - entry_time).total_seconds() / 3600, 0.01)

    rates = {"2-wheeler": 5, "4-wheeler": 10, "bicycle": 2}
    rate = rates.get(vehicle[1], 10)
    amount_due = round(hours_parked * rate, 2)

    cursor.execute("UPDATE slots SET is_occupied=FALSE, vehicle_id=NULL WHERE slot_id=%s", (slot_id,))
    cursor.execute("UPDATE vehicles SET parked_slot=NULL, entry_time=NULL WHERE vehicle_id=%s", (vehicle_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return {
        "message": f"Slot {slot_id} is now free",
        "hours_parked": round(hours_parked, 2),
        "amount_due": amount_due
    }


# ------------------ FREE SLOT BY USER (from SMS link) ------------------
@router.get("/free_by_user/{vehicle_id}", response_class=HTMLResponse)
def free_slot_by_user(request: Request, vehicle_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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

    cursor.execute("UPDATE slots SET is_occupied=FALSE, vehicle_id=NULL WHERE slot_id=%s", (slot_id,))
    cursor.execute("UPDATE vehicles SET parked_slot=NULL, entry_time=NULL WHERE vehicle_id=%s", (vehicle_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        "free_slot.html",
        {
            "request": request,
            "slot_id": slot_id,
            "amount_due": amount_due,
            "vehicle_type": vehicle["vehicle_type"]
        }
    )


# ------------------ FREE SLOT USING TOKEN (confirmation + action) ------------------

@router.get("/free_by_token_confirm/{token}", response_class=HTMLResponse)
def show_free_confirm(request: Request, token: str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT token_uuid, vehicle_id, slot_id, expires_at, used
            FROM free_tokens WHERE token_uuid=%s;
        """, (token,))
        token_data = cursor.fetchone()
        if not token_data:
            return HTMLResponse("<h3>Invalid or expired link.</h3>", status_code=404)

        if token_data["used"] or (token_data["expires_at"] and token_data["expires_at"] < datetime.utcnow()):
            return HTMLResponse("<h3>Link expired or already used.</h3>", status_code=410)

        return templates.TemplateResponse(
            "confirm_free.html",
            {"request": request, "token": token, "slot_id": token_data["slot_id"]}
        )
    finally:
        cursor.close()
        conn.close()


@router.post("/free_by_token/{token}")
def free_by_token(token: str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT token_uuid, vehicle_id, slot_id, expires_at, used
            FROM free_tokens WHERE token_uuid=%s;
        """, (token,))
        token_data = cursor.fetchone()
        if not token_data:
            raise HTTPException(status_code=404, detail="Invalid token")

        if token_data["used"] or (token_data["expires_at"] and token_data["expires_at"] < datetime.utcnow()):
            raise HTTPException(status_code=400, detail="Token expired or already used")

        slot_id = token_data["slot_id"]
        vehicle_id = token_data["vehicle_id"]

        # Free slot and vehicle
        cursor.execute("UPDATE slots SET is_occupied=FALSE, vehicle_id=NULL WHERE slot_id=%s;", (slot_id,))
        cursor.execute("UPDATE vehicles SET parked_slot=NULL, entry_time=NULL WHERE vehicle_id=%s;", (vehicle_id,))
        cursor.execute("UPDATE free_tokens SET used=TRUE WHERE token_uuid=%s;", (token,))

        conn.commit()
    finally:
        cursor.close()
        conn.close()

    return {"message": f"Slot {slot_id} freed successfully"}
