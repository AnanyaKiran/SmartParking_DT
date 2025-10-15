from twilio.rest import Client
import os
from dotenv import load_dotenv

# Load environment variables (Twilio credentials)
load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_sms_notification(to_number: str, slot_id: int, vehicle_type: str, vehicle_id: int):
    """
    Sends SMS to user with a clickable link to free the slot.
    """
    # Link points to the Vercel frontend
    slot_link = f"https://your-frontend.vercel.app/free_slot.html?vehicle_id={vehicle_id}"

    message_body = (
        f"🚗 Smart Parking Alert 🚗\n\n"
        f"Your {vehicle_type} has been parked in Slot {slot_id}.\n"
        f"Click here to free your slot when leaving:\n{slot_link}\n\n"
        f"Thank you for using Smart Parking!"
    )

    message = client.messages.create(
        body=message_body,
        from_=TWILIO_PHONE_NUMBER,
        to=to_number
    )
    print(f"✅ SMS sent to {to_number}: {message.sid}")

