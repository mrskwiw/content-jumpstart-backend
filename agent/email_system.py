"""
Email integration system for sending notifications, reminders, and deliverables
"""

import logging
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

logger = logging.getLogger(__name__)

# Valid EMAIL_PROVIDER values. An unrecognised value must NOT silently disable
# sending — it falls back to auto-selection (see _resolve_provider).
_ALLOWED_PROVIDERS = {"auto", "resend", "smtp", "log"}


class EmailType(str, Enum):
    """Types of emails the system can send"""

    DELIVERABLE = "deliverable"
    FEEDBACK_REQUEST = "feedback_request"
    INVOICE_REMINDER = "invoice_reminder"
    REVISION_CONFIRMATION = "revision_confirmation"
    SATISFACTION_SURVEY = "satisfaction_survey"
    PASSWORD_RESET = "password_reset"  # pragma: allowlist secret  # enum value, not a credential
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
    from_email: str = "noreply@content-jumpstart.com"
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
        # Accept SMTP_USER or SMTP_USERNAME — the .env template historically
        # documented SMTP_USERNAME while the code read SMTP_USER, which silently
        # left email in log-only mode. Honour both.
        self.smtp_user = smtp_user or os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")

        # Resend (preferred transactional provider). When RESEND_API_KEY is set,
        # send_email() routes through the Resend HTTP API; otherwise it falls back
        # to SMTP, then to dev-mode logging — so an unset key is a no-op.
        self.resend_api_key = os.getenv("RESEND_API_KEY")
        # Explicit override: auto | resend | smtp | log. "auto" picks the best
        # available transport (resend > smtp > log).
        self.email_provider = os.getenv("EMAIL_PROVIDER", "auto").lower()
        self.from_name = os.getenv("EMAIL_FROM_NAME", "Content Jumpstart")
        # Optional global sender override (else per-message from_email is used).
        self.from_override = os.getenv("EMAIL_FROM")

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
            EmailType.PASSWORD_RESET: EmailTemplate(
                template_id="password_reset",
                email_type=EmailType.PASSWORD_RESET,
                subject="Reset your Content Jumpstart password 🔐",
                body_text="""
Hi {client_name},

We received a request to reset the password for your Content Jumpstart account.

Click the link below to choose a new password:

{reset_link}

This link expires in {expiry_minutes} minutes and can only be used once.

If you didn't request this, you can safely ignore this email — your password
won't change until you visit the link above and set a new one.

Best regards,
The Content Jumpstart Team
                """.strip(),
                variables=["client_name", "reset_link", "expiry_minutes"],
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

    def _resolve_provider(self) -> str:
        """Pick the outbound transport: resend > smtp > log.

        An explicit EMAIL_PROVIDER wins, but an *unrecognised* value (typo /
        config drift) falls back to auto-selection with a warning rather than
        silently dropping every send into log-only mode.

        Transport is deterministic: the chosen transport is the only one tried.
        We intentionally do NOT auto-fall-back (e.g. Resend→SMTP) on a send
        failure — a provider error that actually queued the message would cause
        a double-send, and mixing transports per-request is non-deterministic.
        Failures are logged loudly instead (see _send_via_resend).
        """
        provider = self.email_provider
        if provider not in _ALLOWED_PROVIDERS:
            logger.warning("Unknown EMAIL_PROVIDER=%r; falling back to auto-selection.", provider)
            provider = "auto"
        if provider != "auto":
            return provider
        if self.resend_api_key:
            return "resend"
        if self.smtp_user and self.smtp_password:
            return "smtp"
        return "log"

    def _from_header(self, message: EmailMessage) -> str:
        """Build the `Name <addr>` From header (global override wins)."""
        addr = self.from_override or message.from_email
        return f"{self.from_name} <{addr}>"

    def send_email(self, message: EmailMessage) -> tuple[bool, Optional[str]]:
        """Send an email message via the resolved transport.

        Never raises — returns ``(ok, detail)`` so callers (often fire-and-forget
        background tasks) don't have to guard.
        """
        provider = self._resolve_provider()
        if provider == "resend":
            return self._send_via_resend(message)
        if provider == "smtp":
            return self._send_via_smtp(message)
        return self._log_email(message)

    def _build_resend_attachments(self, paths: List[str]) -> List[dict]:
        """Base64-encode existing files into Resend's attachment format."""
        import base64

        out: List[dict] = []
        for attachment_path in paths:
            fp = Path(attachment_path)
            if fp.exists():
                with open(fp, "rb") as f:
                    out.append(
                        {
                            "filename": fp.name,
                            "content": base64.b64encode(f.read()).decode("ascii"),
                        }
                    )
        return out

    def _send_via_resend(self, message: EmailMessage) -> tuple[bool, Optional[str]]:
        """Send via the Resend HTTP API (https://resend.com/docs)."""
        if not self.resend_api_key:
            return False, "RESEND_API_KEY not configured"

        payload: dict = {
            "from": self._from_header(message),
            "to": [message.to_email],
            "subject": message.subject,
            "text": message.body_text,
        }
        if message.body_html:
            payload["html"] = message.body_html
        if message.reply_to:
            payload["reply_to"] = message.reply_to
        attachments = self._build_resend_attachments(message.attachments)
        if attachments:
            payload["attachments"] = attachments

        try:
            import requests

            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15,
            )
            if resp.status_code // 100 == 2:
                message.status = "sent"
                message.sent_at = datetime.now()
                email_id = None
                try:
                    email_id = resp.json().get("id")
                except Exception:
                    pass
                return True, f"Sent via Resend (id={email_id})"

            message.status = "failed"
            detail = f"Resend API error {resp.status_code}: {resp.text[:200]}"
            logger.warning("Email send failed (to=%s): %s", message.to_email, detail)
            return False, detail

        except Exception as e:
            message.status = "failed"
            logger.warning("Email send errored (to=%s): %s", message.to_email, e)
            return False, str(e)

    def _send_via_smtp(self, message: EmailMessage) -> tuple[bool, Optional[str]]:
        """Send via SMTP (self-hosted / Gmail fallback)."""
        try:
            # Create MIME message
            msg = MIMEMultipart()
            msg["From"] = self._from_header(message)
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
            "voice_guide_file": (
                Path(deliverable_files[1]).name if len(deliverable_files) > 1 else ""
            ),
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
        feedback_link: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """Send feedback request email.

        ``feedback_link`` defaults to ``{APP_BASE_URL}/feedback`` so outbound links
        follow the configured domain (content-jumpstart.com) instead of a
        hardcoded host (DOMAIN-01 D-01d).
        """
        if not feedback_link:
            base = os.getenv("APP_BASE_URL", "https://content-jumpstart.com").rstrip("/")
            feedback_link = f"{base}/feedback"
        variables = {"client_name": client_name, "feedback_link": feedback_link}

        message = self.create_email_from_template(
            email_type=EmailType.FEEDBACK_REQUEST, to_email=client_email, variables=variables
        )

        return self.send_email(message)

    def send_password_reset(
        self,
        client_name: str,
        client_email: str,
        reset_link: str,
        expiry_minutes: int = 30,
    ) -> tuple[bool, Optional[str]]:
        """Send a self-service password-reset email (GAP-AUTH-01).

        ``reset_link`` is the fully-formed ``{APP_BASE_URL}/reset-password?token=…``
        URL built by the caller; ``expiry_minutes`` is surfaced in the copy so it
        stays in sync with the token's actual lifetime.
        """
        variables = {
            "client_name": client_name,
            "reset_link": reset_link,
            "expiry_minutes": str(expiry_minutes),
        }

        message = self.create_email_from_template(
            email_type=EmailType.PASSWORD_RESET, to_email=client_email, variables=variables
        )
        message.priority = EmailPriority.HIGH

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
