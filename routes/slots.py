# routes/slots.py
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Header
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import get_db_connection
from datetime import datetime
from notify_whatsapp import send_whatsapp_notification
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
        cursor.execute("""
            SELECT s.slot_id, s.is_occupied, s.vehicle_id, 
                   v.license_plate, u.user_name
            FROM slots s
            LEFT JOIN vehicles v ON s.vehicle_id = v.vehicle_id
            LEFT JOIN users u ON v.user_id = u.user_id
            ORDER BY s.slot_id;
        """)
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

    try:
        # Check slot availability
        cursor.execute("SELECT is_occupied FROM slots WHERE slot_id=%s", (slot_id,))
        slot = cursor.fetchone()
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        if slot[0]:
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

        # ✅ Send WhatsApp notification (background)
        if vehicle and vehicle[1]:
            phone = vehicle[1]
            if not phone.startswith("+"):
                phone = "+91" + phone.strip()

            background_tasks.add_task(
                send_whatsapp_notification,
                to_number=phone,
                slot_id=slot_id,
                vehicle_type=vehicle[0],
                vehicle_id=vehicle_id
            )

        return {
            "message": f"Slot {slot_id} occupied successfully",
            "entry_time": entry_time.isoformat(),
            "vehicle_id": vehicle_id
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        print(f"Error in occupy_slot: {e}")
        raise HTTPException(status_code=500, detail="Error occupying slot")
    finally:
        cursor.close()
        conn.close()


# ------------------ FREE SLOT (Admin/API) ------------------
@router.post("/free/{slot_id}")
def free_slot(slot_id: int, api_key: str = Header(None)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT is_occupied, vehicle_id FROM slots WHERE slot_id=%s", (slot_id,))
        slot = cursor.fetchone()
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        if not slot[0]:
            raise HTTPException(status_code=400, detail="Slot already free")

        vehicle_id = slot[1]
        cursor.execute("SELECT entry_time, vehicle_type FROM vehicles WHERE vehicle_id=%s", (vehicle_id,))
        vehicle = cursor.fetchone()

        entry_time = vehicle[0]
        exit_time = datetime.now()
        hours_parked = max((exit_time - entry_time).total_seconds() / 3600, 0.01)

        rates = {"2-wheeler": 30, "4-wheeler": 50, "bicycle": 10}
        rate = rates.get(vehicle[1], 10)
        amount_due = round(hours_parked * rate, 2)

        cursor.execute("UPDATE slots SET is_occupied=FALSE, vehicle_id=NULL WHERE slot_id=%s", (slot_id,))
        cursor.execute("UPDATE vehicles SET parked_slot=NULL, entry_time=NULL WHERE vehicle_id=%s", (vehicle_id,))
        conn.commit()

        return {
            "message": f"Slot {slot_id} is now free",
            "hours_parked": round(hours_parked, 2),
            "amount_due": amount_due
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        print(f"Error freeing slot: {e}")
        raise HTTPException(status_code=500, detail="Error freeing slot")
    finally:
        cursor.close()
        conn.close()


# ------------------ FREE SLOT BY USER ------------------
@router.get("/free_by_user/{vehicle_id}", response_class=HTMLResponse)
def free_slot_by_user(request: Request, vehicle_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Fetch vehicle and slot info
        cursor.execute("""
            SELECT parked_slot, entry_time, vehicle_type 
            FROM vehicles 
            WHERE vehicle_id = %s
        """, (vehicle_id,))
        vehicle = cursor.fetchone()

        if not vehicle or not vehicle["parked_slot"]:
            return HTMLResponse("<h3>⚠️ No active parking found for this vehicle.</h3>")

        slot_id = vehicle["parked_slot"]
        entry_time = vehicle["entry_time"]
        exit_time = datetime.now()

        # Calculate duration
        duration_seconds = (exit_time - entry_time).total_seconds()
        hours_parked = duration_seconds / 3600

        # Convert to readable duration string
        if duration_seconds < 60:
            duration_str = "Less than a minute"
        elif duration_seconds < 3600:
            minutes = int(duration_seconds // 60)
            duration_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = int(duration_seconds // 3600)
            minutes = int((duration_seconds % 3600) // 60)
            duration_str = f"{hours} hr {minutes} min"

        # Rate calculation
        rates = {"2-wheeler": 30, "4-wheeler": 50, "bicycle": 10}
        rate = rates.get(vehicle["vehicle_type"], 10)

        # Always charge for at least 15 minutes (0.25 hr)
        billable_hours = max(hours_parked, 0.25)
        amount_due = round(billable_hours * rate, 2)

        # Free the slot
        cursor.execute("UPDATE slots SET is_occupied=FALSE, vehicle_id=NULL WHERE slot_id=%s", (slot_id,))
        cursor.execute("UPDATE vehicles SET parked_slot=NULL, entry_time=NULL WHERE vehicle_id=%s", (vehicle_id,))
        conn.commit()

        # Send all data to template
        return templates.TemplateResponse(
            "free_slot.html",
            {
                "request": request,
                "vehicle_type": vehicle["vehicle_type"],
                "slot_id": slot_id,
                "entry_time": entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                "exit_time": exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                "duration": duration_str,
                "amount_due": amount_due
            }
        )

    finally:
        cursor.close()
        conn.close()
