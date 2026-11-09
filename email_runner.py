
import os
from dotenv import load_dotenv

from weekly_report import (
    get_weekly_rating_report,
    get_weekly_streaming_report,
    format_weekly_email
)

from email_sender import send_email

load_dotenv()


def run_weekly_report():

    # Step 1: Get movie rating changes
    rating_report = get_weekly_rating_report()

    # Step 2: Get streaming changes
    streaming_report = get_weekly_streaming_report()

    # Step 3: Format the email
    email_body = format_weekly_email(
        rating_report,
        streaming_report
    )

    # Step 4: Get recipients from .env
    recipients = [
    email.strip()
    for email in os.environ["MAILJET_RECIPIENTS"].split(",")
    if email.strip()
]

    # Step 5: Send the report to each recipient
    for recipient in recipients:

        send_email(
            recipient=recipient,
            subject="Weekly Letterboxd Movie Report",
            message=email_body
        )

    print("Weekly report email requests completed!")


if __name__ == "__main__":
    run_weekly_report()
