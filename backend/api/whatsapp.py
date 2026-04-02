# FastAPI WhatsApp webhook handler for Twilio
from fastapi import APIRouter, Request, status, Depends
from fastapi.responses import Response as FastAPIResponse
import xml.etree.ElementTree as ET
import logging
from datetime import datetime

# Import handlers and utilities
try:
    from services.onboarding_handlers import route_message
    from services.whatsapp_service import notify_worker
except ImportError as e:
    logger_init = logging.getLogger("gigkavach.whatsapp")
    logger_init.error(f"Failed to import handlers: {e}")
    async def route_message(phone, body):
        return "GigKavach Help: Type JOIN to register, STATUS to check coverage, or RENEW to extend."

logger = logging.getLogger("gigkavach.whatsapp")
router = APIRouter(tags=["WhatsApp Webhook"])

@router.post("/whatsapp/webhook", status_code=status.HTTP_200_OK)
async def whatsapp_webhook(request: Request):
    """
    Handles incoming WhatsApp messages from Twilio webhook.
    Parses sender and message body, routes to appropriate handler.
    """
    form = await request.form()
    sender = form.get("From", "")  # Twilio format: whatsapp:+1234567890
    body = form.get("Body", "").strip()

    # Extract phone number (remove whatsapp: prefix if present)
    phone = sender.replace("whatsapp:", "") if "whatsapp:" in sender else sender
    
    logger.info(f"📨 Incoming message from {phone}: {body[:50]}")

    # Route to appropriate handler
    response_text = await route_message(phone, body)

    # Build TwiML XML response
    twiml = ET.Element("Response")
    message = ET.SubElement(twiml, "Message")
    message.text = response_text
    xml_str = ET.tostring(twiml, encoding="utf-8")

    logger.info(f"📤 Response to {phone}: {response_text[:50]}")
    return FastAPIResponse(content=xml_str, media_type="application/xml")

def send_whatsapp_alert(worker_id: str, message_type: str, context: dict = None):
    """
    Outbound notification bridge using the unified notify_worker service.
    (Used by DCI Poller / Settlement Service)
    """
    if context is None: context = {}
    
    # In a real scenario, we fetch the worker's phone and language from DB
    # For the hackathon demo, we default to English and generic phone stubs
    success = notify_worker(
        phone_number="+919876543210", # Mock mapping
        message_key=message_type, 
        language="en", 
        **context
    )
    
    logger.info(f"📱 [OUTBOUND ALERT] {message_type} sent to {worker_id} | Success: {success}")
    return {"status": "sent" if success else "failed", "timestamp": datetime.now().isoformat()}
