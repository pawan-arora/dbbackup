from email.mime.text import MIMEText
from utils.logger import logger

class EmailNotifier:
    def notify_in_background(config, email_address, uploaded_files, db, count):
        from notification.email_sender import EmailSender
        sender = EmailSender(config)
        files_list = '\n'.join(uploaded_files)
        subject = "Backup Uploaded Successfully"
        body = (
            f"{count} backup(s) completed and uploaded successfully for database: {db}\n\n"
            f"Uploaded Files:\n{files_list}"
        )
        sender.send_notification(subject=subject, body=body, to_email=email_address)
