"""
Action tools for Python Agent.
Provides functions to execute marketing actions like sending SMS.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MarketingActions:
    """
    Marketing action execution class.
    Handles various marketing actions such as SMS sending.
    """

    def __init__(self):
        """Initialize marketing actions."""
        self.sent_messages: list = []

    def send_sms(self, user_id: str, phone: str, message: str) -> Dict[str, Any]:
        """
        Send marketing SMS to user.

        Args:
            user_id: The user ID to send SMS to
            phone: The phone number to send SMS to
            message: The SMS message content

        Returns:
            Dictionary containing the result of the action
        """
        try:
            # In production, integrate with SMS API (e.g., Twilio, Aliyun SMS)
            # For now, just log and return success
            logger.info(f"[SMS] Sending to {user_id} ({phone}): {message}")

            result = {
                'success': True,
                'user_id': user_id,
                'phone': phone,
                'message': message,
                'timestamp': self._get_timestamp(),
                'action': 'SMS_SENT'
            }

            # Track sent messages for testing
            self.sent_messages.append(result)

            return result

        except Exception as e:
            logger.error(f"Failed to send SMS to {user_id}: {e}")
            return {
                'success': False,
                'user_id': user_id,
                'error': str(e),
                'action': 'SMS_FAILED'
            }

    def send_email(self, user_id: str, email: str, subject: str, content: str) -> Dict[str, Any]:
        """
        Send marketing email to user.

        Args:
            user_id: The user ID to send email to
            email: The email address
            subject: Email subject
            content: Email content

        Returns:
            Dictionary containing the result of the action
        """
        try:
            logger.info(f"[Email] Sending to {user_id} ({email}): {subject}")

            result = {
                'success': True,
                'user_id': user_id,
                'email': email,
                'subject': subject,
                'content': content,
                'timestamp': self._get_timestamp(),
                'action': 'EMAIL_SENT'
            }

            return result

        except Exception as e:
            logger.error(f"Failed to send email to {user_id}: {e}")
            return {
                'success': False,
                'user_id': user_id,
                'error': str(e),
                'action': 'EMAIL_FAILED'
            }

    def push_notification(self, user_id: str, title: str, body: str) -> Dict[str, Any]:
        """
        Send push notification to user.

        Args:
            user_id: The user ID
            title: Notification title
            body: Notification body

        Returns:
            Dictionary containing the result
        """
        try:
            logger.info(f"[Push] Sending to {user_id}: {title}")

            result = {
                'success': True,
                'user_id': user_id,
                'title': title,
                'body': body,
                'timestamp': self._get_timestamp(),
                'action': 'PUSH_SENT'
            }

            return result

        except Exception as e:
            logger.error(f"Failed to send push to {user_id}: {e}")
            return {
                'success': False,
                'user_id': user_id,
                'error': str(e),
                'action': 'PUSH_FAILED'
            }

    def skip_marketing(self, user_id: str, reason: str) -> Dict[str, Any]:
        """
        Skip marketing for this user and log the reason.

        Args:
            user_id: The user ID
            reason: Reason for skipping

        Returns:
            Dictionary containing the result
        """
        logger.info(f"[Skip] User {user_id}: {reason}")

        return {
            'success': True,
            'user_id': user_id,
            'reason': reason,
            'timestamp': self._get_timestamp(),
            'action': 'SKIP_MARKETING'
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_sent_messages(self) -> list:
        """Get list of sent messages (for testing)."""
        return self.sent_messages

    def clear_sent_messages(self):
        """Clear sent messages history (for testing)."""
        self.sent_messages = []


# Convenience functions for direct use
def send_sms(user_id: str, phone: str, message: str) -> Dict[str, Any]:
    """Send marketing SMS to user."""
    actions = MarketingActions()
    return actions.send_sms(user_id, phone, message)


def skip_marketing(user_id: str, reason: str) -> Dict[str, Any]:
    """Skip marketing for this user."""
    actions = MarketingActions()
    return actions.skip_marketing(user_id, reason)
