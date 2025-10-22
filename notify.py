import os
from dotenv import load_dotenv
from twilio.rest import Client
from fastapi.background import BackgroundTasks

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
BASE_URL = os.getenv("BASE_URL")  # Use your Render URL in production

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_sms_notification(
    to_number: str,
    slot_id: int,
    vehicle_type: str,
    vehicle_id: int,
    user_name: str,
    background_tasks: BackgroundTasks = None
):
    """
    Sends SMS notification after registration with slot details
    and the link to free the slot later.
    """
    slot_link = f"{BASE_URL}/slots/free_by_user/{vehicle_id}"
        # Ensure phone number is in E.164 format for India
    to_number = to_number.strip()
    if not to_number.startswith("+"):
        to_number = "+91" + to_number

    message_body = (
        f"✅ Smart Parking Confirmation ✅\n\n"
        f"Hello {user_name}, your {vehicle_type} has been successfully parked.\n"
        f"🅿️ Slot Number: {slot_id}\n"
        f"🚘 Vehicle ID: {vehicle_id}\n\n"
        f"When you leave, click below to free your slot:\n"
        f"{slot_link}\n\n"
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
