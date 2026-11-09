
import os
from dotenv import load_dotenv
from mailjet_rest import Client

load_dotenv()

def send_email(recipient, subject, message):

    api_key = os.environ["MAILJET_API_KEY"]
    secret_key = os.environ["MAILJET_SECRET_KEY"]
    sender = os.environ["MAILJET_SENDER_EMAIL"]

    mailjet = Client(
        auth=(api_key, secret_key),
        version="v3.1"
    )

    data = {
        "Messages": [
            {
                "From": {
                    "Email": sender,
                    "Name": "Letterboxd Movie Tracker"
                },
                "To": [
                    {
                        "Email": recipient
                    }
                ],
                "Subject": subject,
                "TextPart": message
            }
        ]
    }

    result = mailjet.send.create(data=data)

    if result.status_code == 200:
        print("Email accepted by Mailjet!")
    else:
        print("Email request failed.")
        print("Status:", result.status_code)
        print("Response:", result.json())

    return result

if __name__ == "__main__":

    send_email(
        recipient="thankyou9866@gmail.com",
        subject="Letterboxd Tracker - Test Email",
        message="Hello! This is a test email from our Python Letterboxd Movie Tracker."
    )