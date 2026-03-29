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
from utils.pincode_mapper import get_location_context

logger = logging.getLogger("gigkavach.social")

def analyze_rss_for_disruptions(feed_url: str, pincode: str, source_name: str) -> dict | None:
    """Downloads RSS and maps headlines containing keywords (strike, bandh, protest) to scores."""
    
    context = get_location_context(pincode)
    target_hood = context["neighborhood"].lower()
    target_city = context["city"].lower()
    target_state = context["state"].lower()
    try:
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            return None
            
        disruption_keywords = ["strike", "bandh", "protest", "riot", "curfew", "hartal", "unrest"]
        score = 0
        matches = []
        
        for entry in feed.entries[:3]: # Only parse the 3 freshest headlines
            title = entry.title
            
            # --- NLP INJECTION PIPELINE ---
            try:
                from ml.nlp_classifier import analyze_headline
                nlp_result = analyze_headline(title)
                
                if nlp_result["is_disruption"]:
                    extracted_loc = nlp_result["location"].lower()
                    
                    # --- HIERARCHICAL GEOGRAPHICAL GUARDRAIL ---
                    # Handle City Synonyms (e.g. Bangalore vs Bengaluru)
                    if target_city == "bangalore": 
                        target_city_alt = "bengaluru"
                    elif target_city == "bengaluru":
                        target_city_alt = "bangalore"
                    else:
                        target_city_alt = target_city
                        
                    # Payout triggers if the specific Neighborhood OR the overarching City/State is affected
                    is_local = (target_hood in extracted_loc) or \
                               (target_city in extracted_loc) or \
                               (target_city_alt in extracted_loc) or \
                               (target_state in extracted_loc)
                    
                    if is_local:
                        logger.critical(f"🚨 NLP DETECTED CIVIC DISRUPTION in {nlp_result['location']}! "
                                        f"(Confidence: {nlp_result['confidence_score']}) Headline: {title}")
                        return {
                            "social_disruption": 100, # Triggers the DCI max-override
                            "error": f"Verified '{nlp_result['top_label']}' detected via NLP",
                            "source": source_name,
                            "headline": title
                        }
                    else:
                        logger.info(f"Skipping NLP Disruption: News affected '{extracted_loc}', but worker is in '{target_city}/{target_hood}'.")
                        # If NLP explicitly says it's elsewhere, we don't want the regex fallback below to trigger.
                        continue 
            except ImportError as e:
                logger.warning(f"NLP Classifier module not found, using regex fallback. {e}")
                pass
            
            # --- REGEX FALLBACK ---
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

async def fetch_deccan_herald(pincode: str) -> dict | None:
    """Layer 1: Deccan Herald RSS."""
    # Note: Use an appropriate real URL; using a mockup for demonstration
    url = "https://www.deccanherald.com/bengaluru/rssfeed.xml"
    # To prevent actual HTTP hang in tests, we execute it directly
    # Since feedparser is synchronous, doing it in a real threadpool is better, but this is fine for parsing.
    return analyze_rss_for_disruptions(url, pincode, "Layer_1_Deccan_Herald_RSS")

async def fetch_the_hindu(pincode: str) -> dict | None:
    """Layer 2: The Hindu RSS."""
    url = "https://www.thehindu.com/news/national/karnataka/feeder/default.rss"
    return analyze_rss_for_disruptions(url, pincode, "Layer_2_The_Hindu_RSS")

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
    social_data = await fetch_deccan_herald(pincode)
    if social_data is not None:
        social_data["source"] = "Layer_1_Deccan_Herald_RSS"
        logger.info(f"Social Layer 1 Success for {pincode}")

    # LAYER 2: The Hindu RSS
    if social_data is None:
        logger.warning(f"Social Layer 1 failed. Attempting Layer 2 (The Hindu) for {pincode}.")
        social_data = await fetch_the_hindu(pincode)
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
