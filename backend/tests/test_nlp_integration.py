"""
tests/test_nlp_integration.py
───────────────────────────────
Validation script for the Social Service NLP Pipeline.
Tests Hierarchical Geofencing, City-wide overrides, and Cross-regional ignores.
"""
import sys
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure the backend directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- MOCK DATA SETS ---
# Headings must contain the Neighborhood/City exactly as they appear in the mapper (or synonyms)
MOCK_FEEDS = {
    "AGARA_STRIKE": [{"title": "Gig workers union calls for 24-hour strike in Agara tomorrow"}],
    "BENGALURU_BANDH": [{"title": "Complete Bengaluru Bandh announced by major unions for next 48 hours"}],
    "KARNATAKA_BANDH": [{"title": "Total state-wide Karnataka Bandh announced, all services crippled"}],
    "DELHI_CURFEW": [{"title": "Strict night curfew implemented in Delhi due to civil unrest"}],
    "NORMAL_NEWS": [{"title": "New tree planting drive starts in Brigade Road parks tomorrow"}]
}

async def run_integration_test():
    print("🚀 STARTING NLP INTEGRATION VALIDATION...")
    print("------------------------------------------")
    
    from services.social_service import get_social_score
    
    # Global Patching for External Infrastructure (Redis, SLA triggers)
    with patch('services.social_service.get_redis', new_callable=AsyncMock) as mock_redis_func, \
         patch('services.social_service.trigger_sla_breach', new_callable=AsyncMock):
        
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis_func.return_value = mock_redis
        
        # 1. TEST CASE: Pinpoint Neighborhood Disruption (Agara 560034)
        with patch('feedparser.parse') as mock_parse:
            mock_parse.return_value.entries = [MagicMock(title=MOCK_FEEDS["AGARA_STRIKE"][0]["title"])]
            
            result_34 = await get_social_score("560034") # Agara
            result_38 = await get_social_score("560038") # Indiranagar
            
            print(f"CASE 1 (Agara Strike):")
            print(f"  -> Score for 560034 (Agara): {result_34.get('score')} | Result: {'✅ PASSED' if result_34.get('score') == 100 else '❌ FAILED'}")
            print(f"  -> Score for 560038 (Indiranagar): {result_38.get('score', 0)} | Result: {'✅ PASSED' if result_38.get('score', 0) != 100 else '❌ FAILED'}")

        # 2. TEST CASE: City-wide Shutdown (Bengaluru Bandh)
        with patch('feedparser.parse') as mock_parse:
            mock_parse.return_value.entries = [MagicMock(title=MOCK_FEEDS["BENGALURU_BANDH"][0]["title"])]
            
            result_34 = await get_social_score("560034")
            result_38 = await get_social_score("560038")
            
            print(f"\nCASE 2 (Bengaluru-wide Bandh):")
            print(f"  -> Score for 560034: {result_34.get('score')} | Result: {'✅ PASSED' if result_34.get('score') == 100 else '❌ FAILED'}")
            print(f"  -> Score for 560038: {result_38.get('score')} | Result: {'✅ PASSED' if result_38.get('score') == 100 else '❌ FAILED'}")

        # 3. TEST CASE: State-wide Shutdown (Karnataka Bandh)
        with patch('feedparser.parse') as mock_parse:
            mock_parse.return_value.entries = [MagicMock(title=MOCK_FEEDS["KARNATAKA_BANDH"][0]["title"])]
            
            result_34 = await get_social_score("560034")
            
            print(f"\nCASE 3 (Karnataka-wide Bandh):")
            print(f"  -> Score for 560034 (Karnataka worker): {result_34.get('score')} | Result: {'✅ PASSED' if result_34.get('score') == 100 else '❌ FAILED'}")

        # 4. TEST CASE: Cross-Regional Ignore (Delhi News)
        with patch('feedparser.parse') as mock_parse:
            mock_parse.return_value.entries = [MagicMock(title=MOCK_FEEDS["DELHI_CURFEW"][0]["title"])]
            
            result_34 = await get_social_score("560034")
            
            print(f"\nCASE 4 (Delhi Curfew - Cross Regional):")
            print(f"  -> Score for 560034: {result_34.get('score', 0)} | Result: {'✅ PASSED' if result_34.get('score', 0) != 100 else '❌ FAILED'}")

        # 5. TEST CASE: Normal News
        with patch('feedparser.parse') as mock_parse:
            mock_parse.return_value.entries = [MagicMock(title=MOCK_FEEDS["NORMAL_NEWS"][0]["title"])]
            
            result_34 = await get_social_score("560034")
            
            print(f"\nCASE 5 (Normal News):")
            print(f"  -> Score for 560034: {result_34.get('score', 0)} | Result: {'✅ PASSED' if result_34.get('score', 0) != 100 else '❌ FAILED'}")

if __name__ == "__main__":
    asyncio.run(run_integration_test())
