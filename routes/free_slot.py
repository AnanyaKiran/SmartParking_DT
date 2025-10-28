from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import get_db_connection
from datetime import datetime, timezone

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/slots/free/{vehicle_id}", response_class=HTMLResponse)
def free_slot(vehicle_id: int, request: Request):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1️⃣ Get slot, entry time, and vehicle info
    cursor.execute("""
        SELECT v.license_plate, v.entry_time, v.vehicle_type, s.slot_id
        FROM vehicles v
        JOIN slots s ON s.vehicle_id = v.vehicle_id
        WHERE v.vehicle_id = %s;
    """, (vehicle_id,))
    data = cursor.fetchone()

    if not data:
        return HTMLResponse("<h3>❌ Invalid or expired link.</h3>")

    license_plate, entry_time, vehicle_type, slot_id = data

    # 2️⃣ Compute exit details
    exit_time = datetime.now()
    duration = exit_time - entry_time
    total_minutes = int(duration.total_seconds() / 60)
    hours = total_minutes / 60

    # 💰 Basic pricing logic
    rate_per_hour = 30 if vehicle_type == "4-wheeler" else 15
    amount = max(rate_per_hour * round(hours, 2), rate_per_hour)  # minimum 1 hour charge

    # 3️⃣ Update DB
    cursor.execute("UPDATE slots SET is_occupied = FALSE, vehicle_id = NULL WHERE slot_id = %s;", (slot_id,))
    cursor.execute("UPDATE vehicles SET exit_time = %s WHERE vehicle_id = %s;", (exit_time, vehicle_id))

    conn.commit()
    cursor.close()
    conn.close()

    # 4️⃣ Show exit summary
    return templates.TemplateResponse(
        "exit_summary.html",
        {
            "request": request,
            "license_plate": license_plate,
            "vehicle_type": vehicle_type,
            "slot_id": slot_id,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "duration": str(duration).split(".")[0],
            "amount": amount
        }
    )
