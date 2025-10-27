# notify_whatsapp.py
import os
import uuid
from datetime import datetime, timedelta
import psycopg2.extras
from dotenv import load_dotenv
from twilio.rest import Client
from database import get_db_connection

load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")  # e.g. 'whatsapp:+14155238886'
BASE_URL = os.getenv("BASE_URL")

# 🔍 DEBUG PRINTS
print("🚀 Loaded .env values:")
print("  TWILIO_ACCOUNT_SID:", ACCOUNT_SID)
print("  TWILIO_WHATSAPP_NUMBER:", WHATSAPP_NUMBER)
print("  BASE_URL:", BASE_URL)

client = Client(ACCOUNT_SID, AUTH_TOKEN)


def send_whatsapp_notification(
    phone_number: str,
    slot_id: int,
    vehicle_type: str,
    vehicle_id: int
):
    """
    Sends a WhatsApp notification to user via Twilio Sandbox with a secure free-slot token link.
    """

    # --- 1️⃣ Format number for Twilio WhatsApp ---
    original = phone_number
    phone_number = phone_number.strip()
    if not phone_number.startswith("+"):
        phone_number = "+91" + phone_number
    to_number = f"whatsapp:{phone_number}"

    # --- 2️⃣ Create and store free-token ---
    token = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(hours=2)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            INSERT INTO free_tokens (token_uuid, vehicle_id, slot_id, expires_at, used)
            VALUES (%s, %s, %s, %s, FALSE)
        """, (token, vehicle_id, slot_id, expires_at))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"🔑 Token generated and stored: {token}")

    except Exception as db_error:
        print(f"❌ Database error while saving token: {db_error}")
        return

    # --- 3️⃣ Create secure link (✅ FIXED HERE) ---
    slot_link = f"{BASE_URL}/slots/free_by_token/{token}"

    # --- 4️⃣ Compose WhatsApp message ---
    body = (
        f"🚗 *Smart Parking Notification* 🚗\n\n"
        f"Your *{vehicle_type}* has been successfully registered and parked in *Slot {slot_id}*.\n\n"
        f"To free your slot, click below 👇\n{slot_link}\n\n"
        f"✅ Thank you for using Smart Parking!"
    )

    print(f"📞 Original number: {original}")
    print(f"📞 Formatted number: {to_number}")
    print(f"📤 Message body:\n{body}")
    print(f"FROM = {WHATSAPP_NUMBER}")

    # --- 5️⃣ Send message via Twilio ---
    try:
        msg = client.messages.create(
            from_=WHATSAPP_NUMBER if WHATSAPP_NUMBER.startswith("whatsapp:") else f"whatsapp:{WHATSAPP_NUMBER}",
            to=to_number,
            body=body
        )
        print(f"✅ WhatsApp sent to {to_number}: {msg.sid}")

    except Exception as e:
        print(f"❌ WhatsApp send failed: {e}")
