import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from .models import EmailOTP

logger = logging.getLogger(__name__)


def send_otp_email(otp: EmailOTP) -> bool:
    """Send a styled OTP email to the user for email verification or password reset."""
    site_name = "GoTrip"
    primary_color = "#0f766e"
    try:
        from core.models import SiteSettings
        site = SiteSettings.load()
        site_name = site.site_name
        primary_color = site.primary_color or "#0f766e"
    except Exception:
        pass

    if otp.purpose == EmailOTP.Purpose.SIGNUP:
        subject = f"{site_name} - Verify your email address"
        action_title = "Verify Your Email"
        action_text = "complete your account registration"
    else:
        subject = f"{site_name} - Password Reset Code"
        action_title = "Reset Your Password"
        action_text = "reset your password"

    plain_message = (
        f"Hello,\n\n"
        f"Your verification code to {action_text} on {site_name} is:\n\n"
        f"    {otp.code}\n\n"
        f"This code will expire in 10 minutes.\n"
        f"If you did not request this code, please ignore this email.\n\n"
        f"Best regards,\n"
        f"The {site_name} Team"
    )

    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;padding:24px;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
      <div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.06);border:1px solid #e2e8f0;">
        <div style="background:{primary_color};padding:28px 24px;text-align:center;">
          <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;letter-spacing:-0.5px;">{site_name}</h1>
        </div>
        <div style="padding:32px 28px;">
          <h2 style="margin:0 0 12px;font-size:20px;font-weight:600;color:#0f172a;text-align:center;">{action_title}</h2>
          <p style="margin:0 0 24px;color:#475569;font-size:15px;line-height:1.6;text-align:center;">
            Please use the following 6-digit one-time password (OTP) to {action_text}:
          </p>
          <div style="background:#f1f5f9;border-radius:12px;padding:20px;text-align:center;margin:0 0 24px;border:1px dashed #cbd5e1;">
            <span style="font-family:Courier,'Lucida Console',monospace;font-size:36px;font-weight:700;letter-spacing:10px;color:{primary_color};padding-left:10px;display:inline-block;">{otp.code}</span>
            <p style="margin:10px 0 0;font-size:13px;color:#64748b;">Valid for <strong>10 minutes</strong></p>
          </div>
          <p style="margin:0 0 8px;color:#64748b;font-size:13px;line-height:1.5;">
            <strong>Important:</strong> Never share this code with anyone. Our support team will never ask for your verification code.
          </p>
          <p style="margin:0;color:#94a3b8;font-size:12px;line-height:1.5;">
            If you did not initiate this request, you can safely ignore this email.
          </p>
        </div>
        <div style="background:#f8fafc;padding:16px 28px;text-align:center;border-top:1px solid #e2e8f0;">
          <p style="margin:0;font-size:12px;color:#94a3b8;">&copy; {site_name}. All rights reserved.</p>
        </div>
      </div>
    </body>
    </html>
    """

    logger.info("Generated %s OTP code %s for %s", otp.purpose, otp.code, otp.email)

    # Save a file copy to sent_emails directory for quick local inspection
    try:
        from pathlib import Path
        email_dir = settings.BASE_DIR / "sent_emails"
        email_dir.mkdir(parents=True, exist_ok=True)
        (email_dir / "latest_otp.txt").write_text(
            f"Latest OTP Code: {otp.code}\n"
            f"Email: {otp.email}\n"
            f"Purpose: {otp.purpose}\n"
            f"Expires at: {otp.expires_at}\n\n"
            f"{plain_message}",
            encoding="utf-8",
        )
        (email_dir / "latest_email.html").write_text(html_message, encoding="utf-8")
    except Exception as e:
        logger.warning("Could not write sent_emails file: %s", e)

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[otp.email],
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
        return True
    except Exception as e:
        logger.exception("Failed sending OTP email to %s: %s", otp.email, e)
        # In development/test or if mail server fails, code is still logged
        return False
