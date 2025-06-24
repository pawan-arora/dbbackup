import smtplib
from email.message import EmailMessage

class EmailSender:
    def __init__(self, config):
        self.config = config['email']

    def send_notification(self, subject, body, to_email):
        # Use to_email from argument instead of hardcoded
        smtp_server = self.config['smtp_server']
        smtp_port = self.config['smtp_port']
        smtp_user = self.config['username']
        smtp_pass = self.config['password']
        from_addr = self.config['from']

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_addr
        msg['To'] = to_email
        msg.set_content(body)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if self.config.get('starttls', True):
                server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
