"""
services/social_service.py — 4-Layer Social Disruption Redundancy
───────────────────────────────────────────────────────────────
Implements the 100% resilient fallback cascade for Social Disruption Index.
Layer 1: Deccan Herald RSS Feed (via feedparser)
Layer 2: The Hindu Karnataka RSS
Layer 3: Stale Redis Cache (Max 30m old)
Layer 4: Hardcoded Disruption Calendar
Fallback: Trigger SLA Breach and return 0.
"""

import logging
import feedparser
import json
import re
from datetime import datetime, date
from utils.redis_client import get_redis
from api.payouts import trigger_sla_breach

logger = logging.getLogger("gigkavach.social")

def analyze_rss_for_disruptions(feed_url: str) -> dict | None:
    """Downloads RSS and maps headlines containing keywords (strike, bandh, protest) to scores."""
    try:
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            return None
            
        disruption_keywords = ["strike", "bandh", "protest", "riot", "curfew", "hartal", "unrest"]
        score = 0
        matches = []
        
        for entry in feed.entries[:10]: # Check top 10 latest news
            title = entry.title
            
            # -------------------------------------------------------------
            # 🧠 TODO: INJECT YOUR CUSTOM NLP MODEL HERE!
            # -------------------------------------------------------------
            # Once your NLP classifier is ready, replace this basic keyword 
            # match with a call to your AI model to evaluate the headline.
            # Example:
            # if my_nlp_model.predict_is_disruption(title):
            #     score += 35
            # -------------------------------------------------------------
            
            title_lower = title.lower()
            if any(kw in title_lower for kw in disruption_keywords):
                matches.append(title)
                score += 35 # Each severe alert adds 35 to the social disruption score
                
        if len(matches) > 0:
            return {"social_disruption": min(100, score), "headlines": matches}
        return {"social_disruption": 0, "headlines": []}
    except Exception as e:
        logger.error(f"RSS Parsing failed for {feed_url}: {e}")
        return None

async def fetch_deccan_herald() -> dict | None:
    """Layer 1: Deccan Herald RSS."""
    # Note: Use an appropriate real URL; using a mockup for demonstration
    url = "https://www.deccanherald.com/bengaluru/rssfeed.xml"
    # To prevent actual HTTP hang in tests, we execute it directly
    # Since feedparser is synchronous, doing it in a real threadpool is better, but this is fine for parsing.
    return analyze_rss_for_disruptions(url)

async def fetch_the_hindu() -> dict | None:
    """Layer 2: The Hindu RSS."""
    url = "https://www.thehindu.com/news/national/karnataka/feeder/default.rss"
    return analyze_rss_for_disruptions(url)

async def fetch_hardcoded_calendar() -> dict | None:
    """Layer 4: Backup static event calendar."""
    # E.g., Major festival or known protest dates mapped
    today_str = date.today().isoformat()
    known_events = {
        "2026-05-01": {"social_disruption": 50, "event": "May Day / Labour Day Parade"},
        "2026-11-01": {"social_disruption": 60, "event": "Karnataka Rajyotsava Celebrations"},
    }
    
    if today_str in known_events:
        return known_events[today_str]
    return {"social_disruption": 0, "event": "No active planned events."}

async def get_social_score(pincode: str) -> dict:
    """Follows strict 4-Layer Cascade."""
    cache_key = f"social_data:{pincode}"
    rc = await get_redis()
    
    social_data = None
    
    # LAYER 1: Deccan Herald RSS
    social_data = await fetch_deccan_herald()
    if social_data is not None:
        social_data["source"] = "Layer_1_Deccan_Herald_RSS"
        logger.info(f"Social Layer 1 Success for {pincode}")

    # LAYER 2: The Hindu RSS
    if social_data is None:
        logger.warning(f"Social Layer 1 failed. Attempting Layer 2 (The Hindu) for {pincode}.")
        social_data = await fetch_the_hindu()
        if social_data is not None:
            social_data["source"] = "Layer_2_The_Hindu_RSS"
            logger.info(f"Social Layer 2 Success for {pincode}")

    # LAYER 3: Stale Redis Cache
    if social_data is None:
        logger.warning(f"Social Layer 2 failed. Attempting Layer 3 (Redis Cache) for {pincode}.")
        cached = await rc.get(cache_key)
        if cached:
            social_data = json.loads(cached)
            social_data["source"] = "Layer_3_Redis_Stale"
            logger.info(f"Social Layer 3 Success for {pincode}")

    # LAYER 4: Hardcoded Calendar
    if social_data is None:
        logger.warning(f"Social Layer 3 failed. Attempting Layer 4 (Calendar) for {pincode}.")
        social_data = await fetch_hardcoded_calendar()
        if social_data is not None:
            social_data["source"] = "Layer_4_Hardcoded_Calendar"
            logger.info(f"Social Layer 4 Success for {pincode}")

    # SLA BREACH FAIL-OUT
    if social_data is None:
        logger.critical(f"ALL 4 SOCIAL DATA LAYERS FAILED for {pincode}. Data complete blackout.")
        await trigger_sla_breach(pincode, "Complete Social Disruption Data Outage")
        return {"score": 0, "error": "All 4 layers crashed - SLA Breach Triggered"}

    # Assign Score Directly
    score = social_data.get("social_disruption", 0)
    social_data["score"] = score

    if social_data["source"] != "Layer_3_Redis_Stale":
        await rc.set(cache_key, json.dumps(social_data), ex=1800)

    return social_data
