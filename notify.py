from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_sms_notification(to_number: str, slot_id: int, vehicle_type: str, vehicle_id: int):
    slot_link = f"https://dt-parking-ananya-kirans-projects.vercel.app/slots/free_by_user/{vehicle_id}"

    message_body = (
        f"🚗 Smart Parking Alert 🚗\n\n"
        f"Your {vehicle_type} is parked in Slot {slot_id}.\n"
        f"Click here to free your slot:\n{slot_link}\n\n"
        f"Thank you for using Smart Parking!"
    )

    message = client.messages.create(
        body=message_body,
        from_=TWILIO_PHONE_NUMBER,
        to=to_number
    )

    print(f"✅ SMS sent to {to_number}: {message.sid}")
