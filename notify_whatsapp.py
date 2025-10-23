import os
from dotenv import load_dotenv
from twilio.rest import Client
from fastapi.background import BackgroundTasks

load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
BASE_URL = os.getenv("BASE_URL")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_whatsapp_notification(
    to_number: str,
    slot_id: int,
    vehicle_type: str,
    vehicle_id: int,
    background_tasks: BackgroundTasks = None
):
    """
    Sends a WhatsApp notification to user via Twilio Sandbox.
    """

    # Format as WhatsApp-compatible number
    if not to_number.startswith("whatsapp:"):
        # ensure +91 for Indian users
        if not to_number.startswith("+"):
            to_number = "+91" + to_number.strip()
        to_number = f"whatsapp:{to_number}"

    # Link for freeing slot
    slot_link = f"{BASE_URL}/slots/free_by_user/{vehicle_id}"

    # WhatsApp message body
    body = (
        f"🚗 *Smart Parking Notification* 🚗\n\n"
        f"Your *{vehicle_type}* has been successfully registered and parked in *Slot {slot_id}*.\n\n"
        f"To free your slot, click below 👇\n{slot_link}\n\n"
        f"✅ Thank you for using Smart Parking!"
    )

    def _send():
        try:
            msg = client.messages.create(
                from_=WHATSAPP_NUMBER,  # must be 'whatsapp:+14155238886'
                to=to_number,
                body=body
            )
            print(f"✅ WhatsApp sent to {to_number}: {msg.sid}")
        except Exception as e:
            print(f"❌ WhatsApp send failed: {e}")

    # Send in background (non-blocking)
    if background_tasks:
        background_tasks.add_task(_send)
    else:
        _send()
