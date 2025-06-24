from email.mime.text import MIMEText
from utils.logger import logger
from utils.logger import disable_console_logging

class EmailNotifier:
    def notify_in_background(config, email_address, uploaded_files, db, count):
        from notification.email_sender import EmailSender
        disable_console_logging()

        logger.info(f"Sending notification email to {email_address} for {db} backups")
        sender = EmailSender(config)
        files_list = '\n'.join(uploaded_files)
        subject = "Backup Uploaded Successfully"
        body = (
            f"{count} backup(s) completed and uploaded successfully for database: {db}\n\n"
            f"Uploaded Files:\n{files_list}"
        )
        sender.send_notification(subject=subject, body=body, to_email=email_address)
