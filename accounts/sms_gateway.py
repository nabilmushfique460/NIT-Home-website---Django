import logging
import requests
from abc import ABC, abstractmethod
from django.conf import settings

logger = logging.getLogger(__name__)


class SMSGateway(ABC):

    @abstractmethod
    def send(self, phone: str, message: str) -> bool:
        pass


class BulkSMSBDGateway(SMSGateway):
    API_URL = 'http://bulksmsbd.net/api/smsapi'

    def send(self, phone: str, message: str) -> bool:
        api_key = getattr(settings, 'SMS_API_KEY', '')
        sender_id = getattr(settings, 'SMS_SENDER_ID', '')

        # Normalize Bangladeshi mobile number format
        normalized = phone.strip().replace('+', '').replace(' ', '').replace('-', '')
        if normalized.startswith('0'):
            normalized = '88' + normalized

        # If SMS credentials are not configured, log to console for development testing
        if not api_key:
            logger.warning(
                "SMS_API_KEY not configured. [SIMULATED SMS] to %s: \"%s\"",
                normalized, message
            )
            print(f"\n=======================================================\n"
                  f"[SMS GATEWAY SIMULATION] To: {normalized}\n"
                  f"Message: {message}\n"
                  f"=======================================================\n")
            return True

        try:
            resp = requests.get(
                self.API_URL,
                params={
                    'api_key': api_key,
                    'type': 'text',
                    'number': normalized,
                    'senderid': sender_id,
                    'message': message,
                },
                timeout=10
            )
            logger.info("BulkSMSBD response: %s", resp.text)
            # BulkSMSBD response starting with 202 signifies successful gateway submission
            return resp.text.strip().startswith('202')
        except requests.RequestException as e:
            logger.error("BulkSMSBD HTTP request failed: %s", str(e))
            return False


def get_sms_gateway() -> SMSGateway:
    return BulkSMSBDGateway()
