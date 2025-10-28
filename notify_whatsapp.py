import os
import uuid
from datetime import datetime, timedelta, timezone
import psycopg2.extras
from dotenv import load_dotenv
from twilio.rest import Client
from database import get_db_connection

load_dotenv()

# ✅ Environment Variables
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
BASE_URL = os.getenv("BASE_URL", "https://smartparking-dt.onrender.com")

print("🚀 Loaded .env values:")
print("  TWILIO_ACCOUNT_SID:", ACCOUNT_SID)
print("  TWILIO_WHATSAPP_NUMBER:", WHATSAPP_NUMBER)
print("  BASE_URL:", BASE_URL)

client = Client(ACCOUNT_SID, AUTH_TOKEN)


def send_whatsapp_notification(
    phone_number: str,
    slot_id: int,
    vehicle_type: str,
    vehicle_id: int,
    token_uuid: str = None
):
    """
    Sends a WhatsApp notification to user via Twilio Sandbox with a secure free-slot token link.
    """

    # --- 1️⃣ Format phone number ---
    phone_number = phone_number.strip()
    if not phone_number.startswith("+"):
        phone_number = "+91" + phone_number  # assume Indian users
    to_number = f"whatsapp:{phone_number}"

    # --- 2️⃣ Reuse token if passed, else create new ---
    token = token_uuid or str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=2)

    # --- 3️⃣ Store token in DB only if new ---
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if token already exists for this vehicle (avoid duplicates)
        cursor.execute("""
            SELECT token_uuid FROM free_tokens
            WHERE vehicle_id = %s AND used = FALSE
        """, (vehicle_id,))
        existing = cursor.fetchone()

        if not existing:
            cursor.execute("""
                INSERT INTO free_tokens (token_uuid, vehicle_id, slot_id, expires_at, used)
                VALUES (%s, %s, %s, %s, FALSE)
            """, (token, vehicle_id, slot_id, expires_at))
            conn.commit()
            print(f"🔑 Token generated and stored: {token}")
        else:
            token = existing["token_uuid"]
            print(f"♻️ Reusing existing token: {token}")

        cursor.close()
        conn.close()
    except Exception as db_error:
        print(f"❌ Database error while saving token: {db_error}")
        return

    # --- 4️⃣ Build link ---
    slot_link = f"{BASE_URL}/slots/free_by_token/{token}"

    # --- 5️⃣ Compose message ---
    body = (
        f"🚗 *Smart Parking Confirmation* 🚗\n\n"
        f"Your *{vehicle_type}* is parked in *Slot {slot_id}*.\n\n"
        f"To free your slot, click below 👇\n{slot_link}\n\n"
        f"⏰ This link will expire in 2 hours.\n\n"
        f"✅ Thank you for using Smart Parking!"
    )

    # --- 6️⃣ Send WhatsApp message ---
    try:
        msg = client.messages.create(
            from_=WHATSAPP_NUMBER if WHATSAPP_NUMBER.startswith("whatsapp:") else f"whatsapp:{WHATSAPP_NUMBER}",
            to=to_number,
            body=body
        )
        print(f"✅ WhatsApp sent successfully! SID: {msg.sid}")
    except Exception as e:
        print(f"❌ WhatsApp send failed: {e}")
