# routes/registration.py
from fastapi import APIRouter, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import get_db_connection
from notify import send_sms_notification
from datetime import datetime, timedelta
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def show_register_form(request: Request):
    """Display form for admin to register new vehicles/users."""
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/", response_class=HTMLResponse)
def register_vehicle(
    request: Request,
    background_tasks: BackgroundTasks,
    user_name: str = Form(...),
    phone_number: str = Form(...),
    license_plate: str = Form(...),
    vehicle_type: str = Form(...)
):
    """Register a new vehicle, assign a free slot, and notify user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1️⃣ Find first available slot
    cursor.execute("SELECT slot_id FROM slots WHERE is_occupied = FALSE ORDER BY slot_id LIMIT 1;")
    slot = cursor.fetchone()
    if not slot:
        cursor.close()
        conn.close()
        return HTMLResponse("<h3>⚠️ No vacant slots available!</h3>")

    slot_id = slot['slot_id'] if isinstance(slot, dict) else slot[0]

    # 2️⃣ Insert user
    cursor.execute(
        "INSERT INTO users (user_name, phone) VALUES (%s, %s) RETURNING user_id;",
        (user_name, phone_number)
    )
    user_row = cursor.fetchone()
    user_id = user_row["user_id"] if isinstance(user_row, dict) else user_row[0]

    # 3️⃣ Insert vehicle
    cursor.execute(
        """
        INSERT INTO vehicles (license_plate, user_id, parked_slot, vehicle_type, phone_number, entry_time)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING vehicle_id;
        """,
        (license_plate, user_id, slot_id, vehicle_type, phone_number, datetime.now())
    )
    vehicle_row = cursor.fetchone()
    vehicle_id = vehicle_row["vehicle_id"] if isinstance(vehicle_row, dict) else vehicle_row[0]

    # 4️⃣ Mark slot as occupied
    cursor.execute(
        "UPDATE slots SET is_occupied = TRUE, vehicle_id = %s WHERE slot_id = %s;",
        (vehicle_id, slot_id)
    )

    # 5️⃣ Create a free-token for link (optional expiration)
    token_uuid = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(hours=2)
    cursor.execute(
        """
        INSERT INTO free_tokens (token_uuid, vehicle_id, slot_id, expires_at)
        VALUES (%s, %s, %s, %s);
        """,
        (token_uuid, vehicle_id, slot_id, expires_at)
    )

    conn.commit()
    cursor.close()
    conn.close()

    # 6️⃣ Send SMS notification in background
    background_tasks.add_task(
        send_sms_notification,
        to_number=phone_number,
        slot_id=slot_id,
        vehicle_type=vehicle_type,
        vehicle_id=vehicle_id
    )

    # 7️⃣ Render success page
    return templates.TemplateResponse(
    "slot_details.html",
    {
        "request": request,
        "user_name": user_name,
        "slot_id": slot_id,
        "phone_number": phone_number,
        "vehicle_type": vehicle_type,
        "vehicle_id": vehicle_id
    }
)
