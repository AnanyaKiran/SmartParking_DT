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
@router.get("/free_by_token/{token}", response_class=HTMLResponse)
def free_by_token_confirm(request: Request, token: str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT ft.vehicle_id, ft.slot_id, ft.expires_at, ft.used, v.vehicle_type, v.entry_time
            FROM free_tokens ft
            LEFT JOIN vehicles v ON ft.vehicle_id = v.vehicle_id
            WHERE ft.token_uuid = %s;
        """, (token,))
        row = cursor.fetchone()
        if not row:
            return HTMLResponse("<h3>❌ Invalid or expired link.</h3>", status_code=404)
        if row["used"]:
            return HTMLResponse("<h3>⚠️ This link was already used.</h3>", status_code=410)
        if row["expires_at"] and datetime.now() > row["expires_at"]:
            return HTMLResponse("<h3>⏰ Link expired.</h3>", status_code=410)

        # Do the free action (idempotent)
        vehicle_id = row["vehicle_id"]
        slot_id = row["slot_id"]
        cursor.execute("UPDATE slots SET is_occupied=FALSE, vehicle_id=NULL WHERE slot_id=%s;", (slot_id,))
        cursor.execute("UPDATE vehicles SET parked_slot=NULL, entry_time=NULL WHERE vehicle_id=%s;", (vehicle_id,))
        cursor.execute("UPDATE free_tokens SET used=TRUE WHERE token_uuid=%s;", (token,))
        conn.commit()

        entry_time = row.get("entry_time")
        exit_time = datetime.now()

        # Compute duration/amount (reuse your logic)
        duration_seconds = (exit_time - entry_time).total_seconds() if entry_time else 0
        if duration_seconds < 60:
            duration_str = "Less than a minute"
        elif duration_seconds < 3600:
            minutes = int(duration_seconds // 60)
            duration_str = f"{minutes} minute{'s' if minutes!=1 else ''}"
        else:
            hours = int(duration_seconds // 3600)
            minutes = int((duration_seconds % 3600)//60)
            duration_str = f"{hours} hr {minutes} min"

        rate_map = {"2-wheeler": 30, "4-wheeler": 50, "bicycle": 10}
        rate = rate_map.get(row.get("vehicle_type"), 10)
        billable_hours = max(duration_seconds/3600, 0.25)
        amount_due = round(billable_hours * rate, 2)

        return templates.TemplateResponse("free_slot.html", {
            "request": request,
            "slot_id": slot_id,
            "vehicle_type": row.get("vehicle_type"),
            "entry_time": entry_time.strftime("%Y-%m-%d %H:%M:%S") if entry_time else "N/A",
            "exit_time": exit_time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": duration_str,
            "amount_due": amount_due
        })
    finally:
        cursor.close()
        conn.close()

