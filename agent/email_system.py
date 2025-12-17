"""
Email integration system for sending notifications, reminders, and deliverables
"""

import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EmailType(str, Enum):
    """Types of emails the system can send"""

    DELIVERABLE = "deliverable"
    FEEDBACK_REQUEST = "feedback_request"
    INVOICE_REMINDER = "invoice_reminder"
    REVISION_CONFIRMATION = "revision_confirmation"
    SATISFACTION_SURVEY = "satisfaction_survey"
    WELCOME = "welcome"
    GENERAL = "general"


class EmailPriority(str, Enum):
    """Email priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class EmailTemplate(BaseModel):
    """Email template structure"""

    template_id: str
    email_type: EmailType
    subject: str
    body_text: str  # Plain text version
    body_html: Optional[str] = None  # HTML version
    variables: List[str] = Field(default_factory=list)  # Placeholders like {client_name}


class EmailMessage(BaseModel):
    """An email message to send"""

    message_id: str
    to_email: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    from_email: str = "content@jumpstart.com"
    reply_to: Optional[str] = None
    attachments: List[str] = Field(default_factory=list)  # File paths
    priority: EmailPriority = EmailPriority.NORMAL
    email_type: EmailType = EmailType.GENERAL
    created_at: datetime = Field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    status: str = "pending"  # pending, sent, failed


class EmailSystem:
    """Email sending and template management"""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.templates = self._load_templates()
        self.message_id_counter = 0

    def _load_templates(self) -> Dict[EmailType, EmailTemplate]:
        """Load email templates"""
        return {
            EmailType.DELIVERABLE: EmailTemplate(
                template_id="deliverable",
                email_type=EmailType.DELIVERABLE,
                subject="Your 30-Day Content Package is Ready! 🎉",
                body_text="""
Hi {client_name},

Great news! Your 30-post content package is complete and ready to use.

**What's Included:**
• 30 custom social media posts
• Brand voice guide
• Quality assurance report
• Posting schedule recommendations

**Files Attached:**
• {deliverable_file}
• {voice_guide_file}
• {qa_report_file}

**Next Steps:**
1. Review the posts and voice guide
2. Start posting according to the schedule
3. Share feedback after 2 weeks

If you need any revisions (up to 5 changes included), just reply to this email with specifics.

Looking forward to seeing your content perform!

Best regards,
The Content Jumpstart Team

---
Need help? Reply to this email or visit our support portal.
                """.strip(),
                variables=["client_name", "deliverable_file", "voice_guide_file", "qa_report_file"],
            ),
            EmailType.FEEDBACK_REQUEST: EmailTemplate(
                template_id="feedback_request",
                email_type=EmailType.FEEDBACK_REQUEST,
                subject="How are your posts performing? 📊",
                body_text="""
Hi {client_name},

It's been 2 weeks since we delivered your content package. We'd love to hear how it's going!

**Quick Feedback (2 minutes):**

1. How many posts have you used so far?
2. Which posts got the best engagement?
3. Any posts that didn't resonate?
4. Do you need any adjustments for future rounds?

Your feedback helps us improve your next content package.

Reply to this email or click here: {feedback_link}

Thanks for your time!

Best regards,
The Content Jumpstart Team
                """.strip(),
                variables=["client_name", "feedback_link"],
            ),
            EmailType.INVOICE_REMINDER: EmailTemplate(
                template_id="invoice_reminder",
                email_type=EmailType.INVOICE_REMINDER,
                subject="Friendly Reminder: Invoice #{invoice_number} 💳",
                body_text="""
Hi {client_name},

This is a friendly reminder that Invoice #{invoice_number} for ${amount} is now {days_overdue} days overdue.

**Invoice Details:**
• Amount: ${amount}
• Due Date: {due_date}
• Service: 30-Day Content Package

**Pay Now:**
{payment_link}

If you've already paid, please disregard this message. If you have any questions about the invoice, just reply to this email.

Thank you!

Best regards,
The Content Jumpstart Team
                """.strip(),
                variables=[
                    "client_name",
                    "invoice_number",
                    "amount",
                    "days_overdue",
                    "due_date",
                    "payment_link",
                ],
            ),
            EmailType.SATISFACTION_SURVEY: EmailTemplate(
                template_id="satisfaction_survey",
                email_type=EmailType.SATISFACTION_SURVEY,
                subject="Rate Your Experience 🌟",
                body_text="""
Hi {client_name},

Now that you've had time to use your content package, we'd love to know how we did.

**Quick Survey (1 minute):**
{survey_link}

Your feedback directly influences how we improve the service.

As a thank you, everyone who completes the survey gets 10% off their next project!

Thanks for your time!

Best regards,
The Content Jumpstart Team
                """.strip(),
                variables=["client_name", "survey_link"],
            ),
            EmailType.REVISION_CONFIRMATION: EmailTemplate(
                template_id="revision_confirmation",
                email_type=EmailType.REVISION_CONFIRMATION,
                subject="Revision Complete ✅",
                body_text="""
Hi {client_name},

Your revision request has been completed!

**What Changed:**
{revision_summary}

**Updated Files Attached:**
• {revised_deliverable_file}

Please review and let us know if you need any further adjustments.

You have {remaining_revisions} revision changes remaining in your package.

Best regards,
The Content Jumpstart Team
                """.strip(),
                variables=[
                    "client_name",
                    "revision_summary",
                    "revised_deliverable_file",
                    "remaining_revisions",
                ],
            ),
        }

    def create_email_from_template(
        self,
        email_type: EmailType,
        to_email: str,
        variables: Dict[str, str],
        attachments: List[str] = None,
    ) -> EmailMessage:
        """Create email from template with variable substitution"""
        template = self.templates.get(email_type)
        if not template:
            raise ValueError(f"Template not found for email type: {email_type}")

        # Substitute variables in subject and body
        subject = template.subject
        body_text = template.body_text

        for var_name, var_value in variables.items():
            placeholder = "{" + var_name + "}"
            subject = subject.replace(placeholder, str(var_value))
            body_text = body_text.replace(placeholder, str(var_value))

        self.message_id_counter += 1
        return EmailMessage(
            message_id=f"email_{int(datetime.now().timestamp())}_{self.message_id_counter}",
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            attachments=attachments or [],
            email_type=email_type,
        )

    def send_email(self, message: EmailMessage) -> tuple[bool, Optional[str]]:
        """Send an email message"""
        if not self.smtp_user or not self.smtp_password:
            # Development mode - log instead of sending
            return self._log_email(message)

        try:
            # Create MIME message
            msg = MIMEMultipart()
            msg["From"] = message.from_email
            msg["To"] = message.to_email
            msg["Subject"] = message.subject

            if message.reply_to:
                msg["Reply-To"] = message.reply_to

            # Add body
            msg.attach(MIMEText(message.body_text, "plain"))

            if message.body_html:
                msg.attach(MIMEText(message.body_html, "html"))

            # Add attachments
            for attachment_path in message.attachments:
                if Path(attachment_path).exists():
                    with open(attachment_path, "rb") as f:
                        attachment = MIMEApplication(f.read())
                        attachment.add_header(
                            "Content-Disposition", "attachment", filename=Path(attachment_path).name
                        )
                        msg.attach(attachment)

            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            message.status = "sent"
            message.sent_at = datetime.now()

            return True, None

        except Exception as e:
            message.status = "failed"
            return False, str(e)

    def _log_email(self, message: EmailMessage) -> tuple[bool, Optional[str]]:
        """Log email instead of sending (development mode)"""
        log_dir = Path("data/email_logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"EMAIL LOG - {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"To: {message.to_email}\n")
            f.write(f"From: {message.from_email}\n")
            f.write(f"Subject: {message.subject}\n")
            f.write(f"Type: {message.email_type.value}\n")
            f.write(f"Priority: {message.priority.value}\n")
            f.write("\n" + "-" * 60 + "\n\n")
            f.write(message.body_text)
            f.write("\n\n" + "-" * 60 + "\n")

            if message.attachments:
                f.write("\nAttachments:\n")
                for att in message.attachments:
                    f.write(f"  - {att}\n")

        message.status = "logged"
        message.sent_at = datetime.now()

        return True, f"Email logged to {log_file}"

    def send_deliverable_email(
        self, client_name: str, client_email: str, deliverable_files: List[str]
    ) -> tuple[bool, Optional[str]]:
        """Send deliverable email with attachments"""
        variables = {
            "client_name": client_name,
            "deliverable_file": Path(deliverable_files[0]).name if deliverable_files else "",
            "voice_guide_file": Path(deliverable_files[1]).name
            if len(deliverable_files) > 1
            else "",
            "qa_report_file": Path(deliverable_files[2]).name if len(deliverable_files) > 2 else "",
        }

        message = self.create_email_from_template(
            email_type=EmailType.DELIVERABLE,
            to_email=client_email,
            variables=variables,
            attachments=deliverable_files,
        )

        return self.send_email(message)

    def send_feedback_request(
        self,
        client_name: str,
        client_email: str,
        feedback_link: str = "https://jumpstart.com/feedback",
    ) -> tuple[bool, Optional[str]]:
        """Send feedback request email"""
        variables = {"client_name": client_name, "feedback_link": feedback_link}

        message = self.create_email_from_template(
            email_type=EmailType.FEEDBACK_REQUEST, to_email=client_email, variables=variables
        )

        return self.send_email(message)

    def send_invoice_reminder(
        self,
        client_name: str,
        client_email: str,
        invoice_number: str,
        amount: float,
        days_overdue: int,
        due_date: str,
        payment_link: str,
    ) -> tuple[bool, Optional[str]]:
        """Send invoice reminder email"""
        variables = {
            "client_name": client_name,
            "invoice_number": invoice_number,
            "amount": f"{amount:.2f}",
            "days_overdue": str(days_overdue),
            "due_date": due_date,
            "payment_link": payment_link,
        }

        message = self.create_email_from_template(
            email_type=EmailType.INVOICE_REMINDER, to_email=client_email, variables=variables
        )
        message.priority = EmailPriority.HIGH

        return self.send_email(message)
