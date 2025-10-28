# routes/registration.py
from fastapi import APIRouter, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import get_db_connection
import os
from notify_whatsapp import send_whatsapp_notification
from datetime import datetime, timedelta, timezone
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def show_register_form(request: Request):
    """Display the vehicle registration form."""
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/", response_class=HTMLResponse)
@router.post("/", response_class=HTMLResponse)
def register_vehicle(
    request: Request,
    background_tasks: BackgroundTasks,
    user_name: str = Form(...),
    phone_number: str = Form(...),
    license_plate: str = Form(...),
    vehicle_type: str = Form(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1️⃣ Find first available slot
        cursor.execute("""
            SELECT slot_id FROM slots 
            WHERE is_occupied = FALSE 
            ORDER BY slot_id LIMIT 1;
        """)
        slot = cursor.fetchone()
        if not slot:
            return HTMLResponse("<h3>⚠️ No vacant slots available!</h3>")

        slot_id = slot['slot_id'] if isinstance(slot, dict) else slot[0]

        # 2️⃣ Insert user record
        cursor.execute("""
            INSERT INTO users (user_name, phone) 
            VALUES (%s, %s) 
            RETURNING user_id;
        """, (user_name, phone_number))
        user_row = cursor.fetchone()
        user_id = user_row["user_id"] if isinstance(user_row, dict) else user_row[0]

        # 3️⃣ Insert vehicle record
        entry_time = datetime.now(timezone.utc)
        cursor.execute("""
            INSERT INTO vehicles (
                license_plate, user_id, parked_slot, vehicle_type, phone_number, entry_time
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING vehicle_id;
        """, (license_plate, user_id, slot_id, vehicle_type, phone_number, entry_time))
        vehicle_row = cursor.fetchone()
        vehicle_id = vehicle_row["vehicle_id"] if isinstance(vehicle_row, dict) else vehicle_row[0]

        # 4️⃣ Mark slot as occupied
        cursor.execute("""
            UPDATE slots 
            SET is_occupied = TRUE, vehicle_id = %s 
            WHERE slot_id = %s;
        """, (vehicle_id, slot_id))

        # 5️⃣ Create free-token (for exit link)
        token_uuid = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        cursor.execute("""
            INSERT INTO free_tokens (token_uuid, vehicle_id, slot_id, expires_at, used)
            VALUES (%s, %s, %s, %s, FALSE);
        """, (token_uuid, vehicle_id, slot_id, expires_at))

        # ✅ Build the WhatsApp free-slot link
        BASE_URL = os.getenv("BASE_URL", "https://your-app.onrender.com")
        slot_link = f"{BASE_URL}/free_by_token/{token_uuid}"

        # Commit DB changes
        conn.commit()

        # 6️⃣ Send WhatsApp notification asynchronously
        background_tasks.add_task(
            send_whatsapp_notification,
            phone_number=phone_number,
            slot_id=slot_id,
            vehicle_type=vehicle_type,
            vehicle_id=vehicle_id,
            token_uuid=token_uuid,
        )

        # 7️⃣ Show success page
        return templates.TemplateResponse(
            "slot_details.html",
            {
                "request": request,
                "user_name": user_name,
                "slot_id": slot_id,
                "phone_number": phone_number,
                "vehicle_type": vehicle_type,
                "vehicle_id": vehicle_id,
            },
        )

    except Exception as e:
        conn.rollback()
        print(f"❌ Registration Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")
    finally:
        cursor.close()
        conn.close()

