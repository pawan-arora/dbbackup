import smtplib
from email.mime.text import MIMEText
from utils.logger import logger

class EmailNotifier:
    def __init__(self, config):
        self.email_conf = config.get('email', None)

    def send_notification(self, subject, body):
        if not self.email_conf:
            logger.warning("Email config not found, skipping email notification.")
            return

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.email_conf['from']
        msg['To'] = self.email_conf['to']

        try:
            with smtplib.SMTP(self.email_conf['smtp_server'], self.email_conf['smtp_port']) as server:
                if self.email_conf.get("starttls"):
                    server.starttls()
                if self.email_conf.get("username"):
                    server.login(self.email_conf["username"], self.email_conf["password"])
                server.send_message(msg)
            logger.info("Email notification sent.")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
