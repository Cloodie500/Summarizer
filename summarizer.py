import imaplib
import email
from email.header import decode_header
import os
import smtplib
from email.mime.text import MIMEText
import requests

def fetch_unread_emails():
    email_user = os.environ.get("EMAIL_USER")
    email_pass = os.environ.get("EMAIL_PASS")
    imap_server = os.environ.get("IMAP_SERVER", "imap.gmail.com")

    # Connect to IMAP
    mail = imaplib.IMAP4_SSL(imap_server)
    mail.login(email_user, email_pass)
    mail.select("inbox")

    # Search for unread emails
    _, messages = mail.search(None, 'UNSEEN')
    email_ids = messages[0].split()

    emails_data = []
    # Fetch up to 5 unread emails
    for e_id in email_ids[:5]:
        _, msg_data = mail.fetch(e_id, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                # Decode subject
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")
                
                # Read text content
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                emails_data.append({"subject": subject, "body": body})

    mail.logout()
    return emails_data

def summarize_text(text):
    api_key = os.environ.get("AI_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Summarize these emails into clear, short bullet points."},
            {"role": "user", "content": f"Summarize these emails:\n\n{text}"}
        ]
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
    return response.json()['choices'][0]['message']['content']

def send_email(summary_text):
    email_user = os.environ.get("EMAIL_USER")
    email_pass = os.environ.get("EMAIL_PASS")
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")

    msg = MIMEText(summary_text)
    msg["Subject"] = "Daily AI Email Summary"
    msg["From"] = email_user
    msg["To"] = email_user

    with smtplib.SMTP_SSL(smtp_server, 465) as server:
        server.login(email_user, email_pass)
        server.send_message(msg)

if __name__ == "__main__":
    unread_emails = fetch_unread_emails()
    if unread_emails:
        combined = "\n---\n".join([f"Subject: {e['subject']}\nBody: {e['body']}" for e in unread_emails])
        summary = summarize_text(combined)
        send_email(summary)
        print("Summary sent successfully.")
    else:
        print("No unread emails found.")
