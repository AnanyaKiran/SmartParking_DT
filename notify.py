# notify.py
import os
from dotenv import load_dotenv
from twilio.rest import Client
from fastapi.background import BackgroundTasks

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
BASE_URL = os.getenv("BASE_URL")  # Dynamic link

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_sms_notification(to_number: str, slot_id: int, vehicle_type: str, vehicle_id: int, background_tasks: BackgroundTasks = None):
    """
    Sends SMS to the user with the slot link.
    Can run in background if background_tasks is provided.
    """
    slot_link = f"{BASE_URL}/slots/free_by_user/{vehicle_id}"
    message_body = (
        f"🚗 Smart Parking Alert 🚗\n\n"
        f"Your {vehicle_type} is parked in Slot {slot_id}.\n"
        f"Click here to free your slot:\n{slot_link}\n\n"
        f"Thank you for using Smart Parking!"
    )

    def _send():
        try:
            message = client.messages.create(
                body=message_body,
                from_=TWILIO_PHONE_NUMBER,
                to=to_number
            )
            print(f"✅ SMS sent to {to_number}: {message.sid}")
        except Exception as e:
            print(f"❌ Failed to send SMS to {to_number}: {e}")

    if background_tasks:
        background_tasks.add_task(_send)
    else:
        _send()
