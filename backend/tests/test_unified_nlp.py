"""
tests/test_unified_nlp.py
───────────────────────────
Robust validation for Unified Disruption Engine (Social + NDMA).
Mocks all infrastructure (Redis, Supabase, APIs) to ensure clean execution.
"""
import sys
import os
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

# Ensure backend is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def run_unified_tests():
    print("🚀 STARTING ROBUST UNIFIED DISRUPTION VALIDATION...")
    print("--------------------------------------------------")
    
    # 1. --- DEFINE MOCKED OUTPUTS ---
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)

    mock_social_ndma = {
        "social_score": 0,
        "ndma_active": True,
        "headlines": ["Severe Flood Warning in Bengaluru South"],
        "source": "Mock_NDMA"
    }
    
    # 2. --- PATCH INFRASTRUCTURE ---
    with patch("services.social_service.get_redis", return_value=mock_redis), \
         patch("services.weather_service.get_redis", return_value=mock_redis), \
         patch("services.aqi_service.get_redis", return_value=mock_redis), \
         patch("services.platform_service.get_redis", return_value=mock_redis), \
         patch("utils.redis_client.get_redis", return_value=mock_redis), \
         patch("cron.dci_poller.set_dci_cache", return_value=True), \
         patch("cron.dci_poller._insert_log_to_db", return_value=True), \
         patch("cron.dci_poller.get_supabase", return_value=MagicMock()):

        # We also need to mock the individual services called by process_zone
        # To avoid actual HTTP calls or deeper logic failures
        from services.social_service import get_unified_disruption_status, get_social_score
        from cron.dci_poller import process_zone
        
        # Scenario 1: Natural Disaster Override
        print("\nSCENARIO 1: NDMA Flood Alert Handling")
        with patch("services.social_service.fetch_rss_feed") as mock_rss:
            # Mocking the 3 feedsDH, Hindu, NDMA
            mock_rss.side_effect = [
                {"social_score": 0, "ndma_active": True, "headlines": ["Flood Alert"]}, # NDMA
                {"social_score": 0, "ndma_active": False, "headlines": []}, # DH
                {"social_score": 0, "ndma_active": False, "headlines": []}  # Hindu
            ]
            
            status = await get_unified_disruption_status("560034")
            print(f"  -> NDMA Active: {status['ndma_active']}")
            
            if status['ndma_active']:
                 print("  ✅ PASSED: Unified Service detected NDMA status.")
            else:
                 print("  ❌ FAILED: NDMA detection failed.")

        # Scenario 2: Social Disruption Piling (Additive)
        print("\nSCENARIO 2: Social Disruption (Additive Score)")
        with patch("services.social_service.fetch_rss_feed") as mock_rss_2:
             mock_rss_2.side_effect = [
                {"social_score": 0, "ndma_active": False, "headlines": []},    # NDMA
                {"social_score": 35, "ndma_active": False, "headlines": ["Strike 1"]}, # DH
                {"social_score": 35, "ndma_active": False, "headlines": ["Strike 2"]}  # Hindu
            ]
             status = await get_unified_disruption_status("560034")
             print(f"  -> Social Score: {status['social_score']} (Expected 70)")
             
             if status['social_score'] == 70:
                 print("  ✅ PASSED: Social scores totaled correctly.")
             else:
                 print(f"  ❌ FAILED: Total was {status['social_score']}")

        # Scenario 3: Global DCI Engine Override
        print("\nSCENARIO 3: DCI Engine Bypass verification")
        with patch("cron.dci_poller.get_social_score") as mock_social_call:
             mock_social_call.return_value = {
                 "score": 0, 
                 "ndma_active": True, 
                 "headlines": ["Emergency Earthquake alert"]
             }
             # Mock other components to avoid their errors
             with patch("cron.dci_poller.get_weather_score", side_effect=AsyncMock(return_value={"score": 10})), \
                  patch("cron.dci_poller.get_aqi_score", side_effect=AsyncMock(return_value={"score": 10})), \
                  patch("cron.dci_poller.get_heat_score", side_effect=AsyncMock(return_value={"score": 10})), \
                  patch("cron.dci_poller.get_platform_score", side_effect=AsyncMock(return_value={"score": 10})):
                 
                 dci_data = await process_zone("560001")
                 print(f"  -> Final DCI: {dci_data['dci_score']}")
                 print(f"  -> Override Active: {dci_data['ndma_override_active']}")
                 
                 if dci_data['dci_score'] == 95 and dci_data['ndma_override_active']:
                     print("  ✅ PASSED: NDMA Override forced DCI 95.")
                 else:
                     print("  ❌ FAILED: Engine failed to override.")

if __name__ == "__main__":
    asyncio.run(run_unified_tests())
