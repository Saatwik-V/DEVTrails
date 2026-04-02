"""
utils/messaging.py — WhatsApp & SMS Notification Helper
─────────────────────────────────────────────────────────
Handles all outbound messages to workers via:
  1. Twilio WhatsApp (primary channel)
  2. Twilio SMS (fallback for workers without WhatsApp — edge case #23)

All 30 worker-facing messages are stored in MESSAGES dict below in
5 languages. No runtime translation API is used — all messages are
pre-translated and stored statically (free, instant, reliable).

Usage:
    from utils.messaging import notify_worker
    notify_worker("+919876543210", "disruption_alert", language="hi", dci=74, amount=280)
"""

from twilio.rest import Client
from config.settings import settings
import logging

logger = logging.getLogger("gigkavach.messaging")


# ─── Multilingual Message Templates ──────────────────────────────────────────
# Keys are message identifiers. Each key maps to translations in 5 languages.
# Placeholders like {dci}, {amount}, {upi} are filled at send time.
#
# Languages: en=English, kn=Kannada, hi=Hindi, ta=Tamil, te=Telugu

MESSAGES: dict[str, dict[str, str]] = {

    # ── Onboarding Messages ──────────────────────────────────────────────────
    "welcome": {
        "en": "👋 Welcome to GigKavach! Reply with your language:\n1️⃣ English\n2️⃣ ಕನ್ನಡ\n3️⃣ हिंदी\n4️⃣ தமிழ்\n5️⃣ తెలుగు",
        "kn": "👋 GigKavach ಗೆ ಸ್ವಾಗತ! ನಿಮ್ಮ ಭಾಷೆ ಆಯ್ಕೆ ಮಾಡಿ:\n1️⃣ English\n2️⃣ ಕನ್ನಡ\n3️⃣ हिंदी\n4️⃣ தமிழ்\n5️⃣ తెలుగు",
        "hi": "👋 GigKavach में आपका स्वागत है! अपनी भाषा चुनें:\n1️⃣ English\n2️⃣ ಕನ್ನಡ\n3️⃣ हिंदी\n4️⃣ தமிழ்\n5️⃣ తెలుగు",
        "ta": "👋 GigKavach-க்கு வரவேற்கிறோம்! உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்:\n1️⃣ English\n2️⃣ ಕನ್ನಡ\n3️⃣ हिंदी\n4️⃣ தமிழ்\n5️⃣ తెలుగు",
        "te": "👋 GigKavach కి స్వాగతం! మీ భాషను ఎంచుకోండి:\n1️⃣ English\n2️⃣ ಕನ್ನಡ\n3️⃣ हिंदी\n4️⃣ தமிழ்\n5️⃣ తెలుగు",
    },

    "ask_platform": {
        "en": "Which platform do you deliver for?\n1️⃣ Zomato\n2️⃣ Swiggy",
        "kn": "ನೀವು ಯಾವ ಪ್ಲಾಟ್‌ಫಾರ್ಮ್‌ನಲ್ಲಿ ಡೆಲಿವರಿ ಮಾಡುತ್ತೀರಿ?\n1️⃣ Zomato\n2️⃣ Swiggy",
        "hi": "आप किस प्लेटफॉर्म पर डिलीवरी करते हैं?\n1️⃣ Zomato\n2️⃣ Swiggy",
        "ta": "நீங்கள் எந்த தளத்தில் டெலிவரி செய்கிறீர்கள்?\n1️⃣ Zomato\n2️⃣ Swiggy",
        "te": "మీరు ఏ ప్లాట్‌ఫారమ్‌లో డెలివరీ చేస్తారు?\n1️⃣ Zomato\n2️⃣ Swiggy",
    },

    "ask_shift": {
        "en": "What are your typical working hours?\n1️⃣ Morning (6AM–2PM)\n2️⃣ Day (9AM–9PM)\n3️⃣ Night (6PM–2AM)\n4️⃣ Flexible",
        "kn": "ನಿಮ್ಮ ಸಾಮಾನ್ಯ ಕೆಲಸದ ಸಮಯ ಯಾವುದು?\n1️⃣ ಬೆಳಿಗ್ಗೆ (6AM–2PM)\n2️⃣ ಹಗಲು (9AM–9PM)\n3️⃣ ರಾತ್ರಿ (6PM–2AM)\n4️⃣ ಯಾವುದಾದರೂ ಸಮಯ",
        "hi": "आप आमतौर पर किस समय काम करते हैं?\n1️⃣ सुबह (6AM–2PM)\n2️⃣ दिन (9AM–9PM)\n3️⃣ रात (6PM–2AM)\n4️⃣ कभी भी",
        "ta": "உங்கள் வேலை நேரம் என்ன?\n1️⃣ காலை (6AM–2PM)\n2️⃣ பகல் (9AM–9PM)\n3️⃣ இரவு (6PM–2AM)\n4️⃣ நெகிழ்வான",
        "te": "మీరు సాధారణంగా ఏ సమయానికి పని చేస్తారు?\n1️⃣ ఉదయం (6AM–2PM)\n2️⃣ పగలు (9AM–9PM)\n3️⃣ రాత్రి (6PM–2AM)\n4️⃣ ఎప్పుడైనా",
    },

    "ask_upi": {
        "en": "Please share your UPI ID for payouts (e.g. ravi@upi):",
        "kn": "ಪಾವತಿಗಾಗಿ ನಿಮ್ಮ UPI ID ಹಂಚಿಕೊಳ್ಳಿ (ಉದಾ: ravi@upi):",
        "hi": "पेमेंट के लिए अपना UPI ID दें (जैसे: ravi@upi):",
        "ta": "பணம் பெற உங்கள் UPI ID அனுப்பவும் (எ.கா: ravi@upi):",
        "te": "పేమెంట్ కోసం మీ UPI ID పంపండి (ఉదా: ravi@upi):",
    },

    "ask_pincode": {
        "en": "Share the pin codes of areas you deliver in (up to 5, comma-separated).\nExample: 560047, 560034",
        "kn": "ನೀವು ಡೆಲಿವರಿ ಮಾಡುವ ಪ್ರದೇಶಗಳ ಪಿನ್ ಕೋಡ್ ಕಳುಹಿಸಿ (5 ವರೆಗೆ):\nಉದಾ: 560047, 560034",
        "hi": "जिन इलाकों में आप डिलीवरी करते हैं उनके पिन कोड भेजें (5 तक):\nजैसे: 560047, 560034",
        "ta": "நீங்கள் டெலிவரி செய்யும் பகுதிகளின் பின் குறியீடுகள் அனுப்பவும் (5 வரை):\nஉதா: 560047, 560034",
        "te": "మీరు డెలివరీ చేసే ప్రాంతాల పిన్ కోడ్‌లు పంపండి (5 వరకు):\nఉదా: 560047, 560034",
    },

    "ask_plan": {
        "en": "Choose your weekly coverage plan:\n\n1️⃣ Shield Basic — ₹69/week — 40% daily earnings protected\n2️⃣ Shield Plus — ₹89/week — 50% daily earnings protected\n3️⃣ Shield Pro — ₹99/week — 70% daily earnings protected",
        "kn": "ನಿಮ್ಮ ವಾರದ ಯೋಜನೆ ಆಯ್ಕೆ ಮಾಡಿ:\n\n1️⃣ Shield Basic — ₹69/ವಾರ — 40% ದಿನದ ಸಂಪಾದನೆ ರಕ್ಷಣೆ\n2️⃣ Shield Plus — ₹89/ವಾರ — 50% ರಕ್ಷಣೆ\n3️⃣ Shield Pro — ₹99/ವಾರ — 70% ರಕ್ಷಣೆ",
        "hi": "अपनी साप्ताहिक योजना चुनें:\n\n1️⃣ Shield Basic — ₹69/हफ्ता — 40% कमाई सुरक्षित\n2️⃣ Shield Plus — ₹89/हफ्ता — 50% कमाई सुरक्षित\n3️⃣ Shield Pro — ₹99/हफ्ता — 70% कमाई सुरक्षित",
        "ta": "உங்கள் வாராந்திர திட்டத்தை தேர்ந்தெடுக்கவும்:\n\n1️⃣ Shield Basic — ₹69/வாரம் — 40% வருமானம் பாதுகாப்பு\n2️⃣ Shield Plus — ₹89/வாரம் — 50% பாதுகாப்பு\n3️⃣ Shield Pro — ₹99/வாரம் — 70% பாதுகாப்பு",
        "te": "మీ వారపు ప్లాన్ ఎంచుకోండి:\n\n1️⃣ Shield Basic — ₹69/వారం — 40% సంపాదన రక్షణ\n2️⃣ Shield Plus — ₹89/వారం — 50% రక్షణ\n3️⃣ Shield Pro — ₹99/వారం — 70% రక్షణ",
    },

    "onboarding_complete": {
        "en": "✅ You're covered! Your GigKavach {plan} plan is active from tomorrow.\nType STATUS to check your zone's disruption level anytime.",
        "kn": "✅ ನಿಮ್ಮ GigKavach {plan} ಯೋಜನೆ ನಾಳೆಯಿಂದ ಸಕ್ರಿಯ!\nSTATUS ಎಂದು ಟೈಪ್ ಮಾಡಿ ಯಾವಾಗ ಬೇಕಾದರೂ ನಿಮ್ಮ ಝೋನ್ ಸ್ಥಿತಿ ಪರಿಶೀಲಿಸಿ.",
        "hi": "✅ आपका GigKavach {plan} प्लान कल से एक्टिव हो जाएगा!\nSTATUS टाइप करके कभी भी अपने ज़ोन की स्थिति जानें।",
        "ta": "✅ உங்கள் GigKavach {plan} திட்டம் நாளையிலிருந்து செயலில் உள்ளது!\nSTATUS என்று தட்டச்சு செய்து எந்த நேரத்திலும் உங்கள் மண்டல நிலையை சரிபார்க்கவும்.",
        "te": "✅ మీ GigKavach {plan} ప్లాన్ రేపటి నుండి యాక్టివ్ అవుతుంది!\nSTATUS టైప్ చేసి ఎప్పుడైనా మీ జోన్ స్థితిని చెక్ చేయండి.",
    },

    "already_onboarded": {
        "en": "✅ You're already registered! Type STATUS to check coverage.",
        "kn": "✅ ನೀವು ಈಗಾಗಲೇ ನೋಂದಾಯಿತರಾಗಿದ್ದೀರಿ! STATUS ಟೈಪ್ ಮಾಡಿ ಕವರೇಜ್ ಪರಿಶೀಲಿಸಿ.",
        "hi": "✅ आप पहले से पंजीकृत हैं! STATUS टाइप करके कवरेज जांचें।",
        "ta": "✅ நீங்கள் ஏற்கனவே பதிவுசெய்யப்பட்டுள்ளீர்கள்! STATUS என்று தட்டச்சு செய்து அட்டையை சரிபார்க்கவும்.",
        "te": "✅ మీరు ఇప్పటికే నమోదు చేయబడ్డారు! STATUS టైప్ చేసి కవరేజ్ చెక్ చేయండి.",
    },

    # ── Disruption Alerts ────────────────────────────────────────────────────
    "disruption_alert": {
        "en": "🚨 Disruption detected in your zone (DCI: {dci}).\nYour coverage is active. Payout will be calculated at end of your shift today.",
        "kn": "🚨 ನಿಮ್ಮ ಝೋನ್‌ನಲ್ಲಿ ಅಡ್ಡಿ ಪತ್ತೆಯಾಗಿದೆ (DCI: {dci}).\nನಿಮ್ಮ ಕವರೇಜ್ ಸಕ್ರಿಯ. ಶಿಫ್ಟ್ ಕೊನೆಯಲ್ಲಿ ಪಾವತಿ ಲೆಕ್ಕ ಹಾಕಲಾಗುವುದು.",
        "hi": "🚨 आपके ज़ोन में बाधा पकड़ी गई (DCI: {dci})।\nआपकी कवरेज एक्टिव है। आज शिफ्ट खत्म होने पर पेमेंट भेजा जाएगा।",
        "ta": "🚨 உங்கள் மண்டலத்தில் இடையூறு கண்டறியப்பட்டது (DCI: {dci}).\nஉங்கள் அட்டை செயலில் உள்ளது. இன்று உங்கள் ஷிப்ட் முடிவில் கட்டணம் கணக்கிடப்படும்.",
        "te": "🚨 మీ జోన్‌లో అంతరాయం గుర్తించబడింది (DCI: {dci}).\nమీ కవరేజ్ యాక్టివ్ గా ఉంది. నేడు మీ షిఫ్ట్ చివరలో పేమెంట్ లెక్కించబడుతుంది.",
    },

    # ── Payout Confirmations ─────────────────────────────────────────────────
    "payout_sent": {
        "en": "💸 ₹{amount} sent to {upi}. Ref: {ref}.\nYour income is protected. 🛡️",
        "kn": "💸 ₹{amount} {upi} ಗೆ ಕಳುಹಿಸಲಾಗಿದೆ. Ref: {ref}.\nನಿಮ್ಮ ಆದಾಯ ಸುರಕ್ಷಿತ. 🛡️",
        "hi": "💸 ₹{amount} {upi} में भेज दिया गया। Ref: {ref}.\nआपकी कमाई सुरक्षित है। 🛡️",
        "ta": "💸 ₹{amount} {upi} க்கு அனுப்பப்பட்டது. Ref: {ref}.\nஉங்கள் வருமானம் பாதுகாக்கப்பட்டுள்ளது. 🛡️",
        "te": "💸 ₹{amount} {upi} కి పంపబడింది. Ref: {ref}.\nమీ సంపాదన రక్షించబడింది. 🛡️",
    },

    # Soft flag — 50% payout, 48hr re-verification in progress
    "payout_partial": {
        "en": "Your payout is processing. Verification active due to signal conditions in your zone. No action needed.\n₹{amount} will arrive today. Remaining balance auto-credits in 48hrs.",
        "kn": "ನಿಮ್ಮ ಪಾವತಿ ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿದೆ. ನಿಮ್ಮ ಝೋನ್‌ನ ಸಿಗ್ನಲ್ ಸ್ಥಿತಿಯಿಂದ ಪರಿಶೀಲನೆ ಸಕ್ರಿಯ. ₹{amount} ಇಂದು ಬರುತ್ತದೆ.",
        "hi": "आपका पेमेंट प्रोसेस हो रहा है। आपके ज़ोन में सिग्नल की स्थिति के कारण वेरिफिकेशन चल रहा है। ₹{amount} आज आएगा।",
        "ta": "உங்கள் கட்டணம் செயலாக்கப்படுகிறது. சிக்னல் நிலை காரணமாக சரிபார்ப்பு செயலில் உள்ளது. ₹{amount} இன்று வரும்.",
        "te": "మీ పేమెంట్ ప్రాసెస్ అవుతోంది. సిగ్నల్ పరిస్థితుల కారణంగా వెరిఫికేషన్ యాక్టివ్ గా ఉంది. ₹{amount} నేడు వస్తుంది.",
    },

    # UPI failure — ask worker to update UPI (edge case #18)
    "upi_failed": {
        "en": "⚠️ We couldn't send ₹{amount} to {upi}. Please reply with your correct UPI ID.\nYou have 48 hours before this payout lapses.",
        "kn": "⚠️ ₹{amount} {upi} ಗೆ ಕಳುಹಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ನಿಮ್ಮ ಸರಿಯಾದ UPI ID ಕಳುಹಿಸಿ. ₹ 48 ಗಂಟೆ ಒಳಗೆ ಪಾವತಿ ಆಗಲಿದೆ.",
        "hi": "⚠️ ₹{amount} {upi} में भेज नहीं सके। कृपया सही UPI ID भेजें। 48 घंटों में भुगतान होगा।",
        "ta": "⚠️ ₹{amount} {upi} க்கு அனுப்ப முடியவில்லை. சரியான UPI ID அனுப்பவும். 48 மணி நேரத்தில் பணம் வரும்.",
        "te": "⚠️ ₹{amount} {upi} కి పంపలేకపోయాం. దయచేసి సరైన UPI ID పంపండి. 48 గంటలలో పేమెంట్ జరుగుతుంది.",
    },

    # STATUS command response
    "status_response": {
        "en": "📊 Zone {pin_code} Status:\nDCI Score: {dci} ({severity})\nCoverage: {plan} ✅\nShift: {shift}\nType HELP for all commands.",
        "kn": "📊 ಝೋನ್ {pin_code} ಸ್ಥಿತಿ:\nDCI: {dci} ({severity})\nಕವರೇಜ್: {plan} ✅\nHELP ಟೈಪ್ ಮಾಡಿ ಎಲ್ಲ ಆಜ್ಞೆಗಳಿಗಾಗಿ.",
        "hi": "📊 ज़ोन {pin_code} की स्थिति:\nDCI: {dci} ({severity})\nकवरेज: {plan} ✅\nसभी कमांड के लिए HELP टाइप करें।",
        "ta": "📊 மண்டல {pin_code} நிலை:\nDCI: {dci} ({severity})\nகவரேஜ்: {plan} ✅\nHELP என்று தட்டச்சு செய்யுங்கள்.",
        "te": "📊 జోన్ {pin_code} స్థితి:\nDCI: {dci} ({severity})\nకవరేజ్: {plan} ✅\nHELP టైప్ చేయండి.",
    },

    # HELP command
    "help": {
        "en": "GigKavach Commands:\n• STATUS — Zone DCI & coverage\n• RENEW — Renew for next week\n• SHIFT — Update working hours\n• LANG — Change language\n• APPEAL — Contest a decision\n• HELP — Show this menu",
        "kn": "GigKavach ಆಜ್ಞೆಗಳು:\n• STATUS — ಝೋನ್ DCI & ಕವರೇಜ್\n• RENEW — ಮುಂದಿನ ವಾರ ನವೀಕರಿಸಿ\n• SHIFT — ಕೆಲಸದ ಸಮಯ ನವೀಕರಿಸಿ\n• LANG — ಭಾಷೆ ಬದಲಿಸಿ\n• APPEAL — ನಿರ್ಧಾರವನ್ನು ಆಕ್ಷೇಪಿಸಿ",
        "hi": "GigKavach कमांड:\n• STATUS — जोन DCI और कवरेज\n• RENEW — अगले हफ्ते नवीनीकरण\n• SHIFT — काम का समय बदलें\n• LANG — भाषा बदलें\n• APPEAL — फैसले को चुनौती दें",
        "ta": "GigKavach கட்டளைகள்:\n• STATUS — மண்டல DCI & அட்டை\n• RENEW — அடுத்த வாரம் புதுப்பிக்க\n• SHIFT — வேலை நேரம் புதுப்பிக்க\n• LANG — மொழி மாற்று\n• APPEAL — முடிவை சவால் செய்",
        "te": "GigKavach కమాండ్లు:\n• STATUS — జోన్ DCI & కవరేజ్\n• RENEW — వచ్చే వారం రెన్యూ\n• SHIFT — పని సమయం అప్డేట్\n• LANG — భాష మార్చు\n• APPEAL — నిర్ణయాన్ని సవాల్ చేయి",
    },
}


# ─── Twilio Client ────────────────────────────────────────────────────────────

def get_twilio_client() -> Client:
    """Returns configured Twilio client"""
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


# ─── Core Send Functions ─────────────────────────────────────────────────────

def send_whatsapp(to_number: str, message: str) -> str | None:
    """
    Sends a WhatsApp message via Twilio.
    to_number should be in E.164 format: +919876543210
    Returns Twilio message SID on success, None on failure.
    """
    try:
        client = get_twilio_client()
        msg = client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,          # whatsapp:+14155238886
            to=f"whatsapp:{to_number}",
            body=message
        )
        logger.info(f"WhatsApp sent to {to_number} | SID: {msg.sid}")
        return msg.sid
    except Exception as e:
        logger.error(f"WhatsApp send failed to {to_number}: {e}")
        return None


def send_sms(to_number: str, message: str) -> str | None:
    """
    SMS fallback for workers without WhatsApp (edge case #23).
    Only for critical notifications: payout alerts and UPI failures.
    """
    try:
        client = get_twilio_client()
        msg = client.messages.create(
            from_=settings.TWILIO_SMS_NUMBER,
            to=to_number,
            body=message
        )
        logger.info(f"SMS sent to {to_number} | SID: {msg.sid}")
        return msg.sid
    except Exception as e:
        logger.error(f"SMS send failed to {to_number}: {e}")
        return None


# ─── High-Level Helper ───────────────────────────────────────────────────────

def notify_worker(
    phone_number: str,
    message_key: str,
    language: str = "en",
    has_whatsapp: bool = True,
    **kwargs  # Template placeholders e.g. dci=74, amount=280, upi="ravi@upi"
) -> bool:
    """
    Main notification function used throughout the codebase.

    Args:
        phone_number: Worker's phone in E.164 (+919...)
        message_key: Key from MESSAGES dict (e.g. "disruption_alert")
        language: "en" | "kn" | "hi" | "ta" | "te"
        has_whatsapp: If False, falls back to SMS (edge case #23)
        **kwargs: Template variables to fill into message

    Returns:
        True if message sent successfully, False if failed
    """
    # Get template — fallback to English if translation missing
    template = MESSAGES.get(message_key, {}).get(language) \
        or MESSAGES.get(message_key, {}).get("en", "")

    if not template:
        logger.error(f"Unknown message key: {message_key}")
        return False

    # Fill in template placeholders e.g. {dci}, {amount}
    try:
        message = template.format(**kwargs)
    except KeyError as e:
        logger.error(f"Missing placeholder {e} for message '{message_key}'")
        return False

    # Send via WhatsApp (primary) or SMS (fallback)
    if has_whatsapp:
        sid = send_whatsapp(phone_number, message)
    else:
        sid = send_sms(phone_number, message)

    return sid is not None
