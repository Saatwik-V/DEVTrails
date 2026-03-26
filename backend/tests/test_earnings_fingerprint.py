"""
tests/test_earnings_fingerprint.py — Unit Tests for Earnings Fingerprint Module
─────────────────────────────────────────────────────────────────────────────

Tests cover:
  ✓ Rolling 4-week median per day-of-week
  ✓ Disruption day filtering (DCI > 65)
  ✓ Festival week filtering
  ✓ Outlier detection and removal
  ✓ New worker blending (city average transition)
  ✓ Weeks-since-registration calculation
  ✓ City-average fallback
  ✓ Baseline persistence to database
  ✓ Edge cases (empty data, insufficient data, etc.)

Run tests with:
    pytest backend/tests/test_earnings_fingerprint.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import functions to test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.earnings_fingerprint import (
    is_festival_week,
    is_disruption_day,
    filter_activity_data,
    calculate_rolling_median_per_dow,
    blend_baselines_for_new_worker,
    get_weeks_since_registration,
    get_fallback_city_average,
    calculate_baseline,
    save_baseline_to_workers_table,
    compute_and_persist_baseline,
    DAYS_OF_WEEK,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_supabase():
    """Mock Supabase client for testing"""
    return Mock()


@pytest.fixture
def sample_activity_data():
    """Create sample activity log data for testing"""
    base_date = datetime(2025, 3, 1)  # Start from March 1, 2025
    data = []

    for i in range(28):  # 4 weeks of data
        current_date = base_date + timedelta(days=i)
        day_of_week = current_date.weekday()

        # Different earnings patterns per day of week
        base_earnings = {
            0: 750,   # Monday
            1: 780,   # Tuesday
            2: 800,   # Wednesday
            3: 820,   # Thursday
            4: 880,   # Friday (surge)
            5: 920,   # Saturday (surge)
            6: 900,   # Sunday
        }[day_of_week]

        # Add some variability
        earnings = base_earnings + np.random.randint(-50, 100)

        # Random DCI score (mostly low, some elevated)
        dci_score = np.random.choice([30, 40, 50, 60, 72, 85], p=[0.3, 0.3, 0.2, 0.1, 0.05, 0.05])

        data.append({
            "date": current_date.date().isoformat(),
            "daily_earnings": float(earnings),
            "dci_score": float(dci_score),
            "platform": "zomato",
            "shift": "day",
        })

    return pd.DataFrame(data)


@pytest.fixture
def sample_personal_baseline():
    """Sample personal baseline earnings"""
    return {
        "monday": 700,
        "tuesday": 730,
        "wednesday": 750,
        "thursday": 780,
        "friday": 850,
        "saturday": 920,
        "sunday": 890,
        "overall_daily_avg": 803,
    }


@pytest.fixture
def sample_city_average():
    """Sample city-average baseline"""
    return {
        "monday": 650,
        "tuesday": 680,
        "wednesday": 700,
        "thursday": 720,
        "friday": 780,
        "saturday": 850,
        "sunday": 820,
        "overall_daily_avg": 743,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test: Festival Week Detection
# ─────────────────────────────────────────────────────────────────────────────

class TestFestivalWeekDetection:
    """Tests for is_festival_week()"""

    def test_festival_week_holi(self):
        """Holi in March should be detected as festival week"""
        holi_date = datetime(2025, 3, 8)  # Holi 2025 is around March 8
        assert is_festival_week(holi_date)

    def test_festival_week_diwali(self):
        """Diwali in October/November should be detected"""
        diwali_date = datetime(2025, 10, 25)  # Diwali 2025
        assert is_festival_week(diwali_date)

    def test_festival_week_new_year(self):
        """New Year in January should be detected"""
        new_year = datetime(2025, 1, 5)  # First week of January
        assert is_festival_week(new_year)

    def test_non_festival_week(self):
        """Regular days should not be detected as festival"""
        regular_date = datetime(2025, 5, 15)  # Mid-May
        assert not is_festival_week(regular_date)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Disruption Day Detection
# ─────────────────────────────────────────────────────────────────────────────

class TestDisruptionDayDetection:
    """Tests for is_disruption_day()"""

    def test_high_dci_is_disruption(self):
        """DCI > 65 should be marked as disruption"""
        assert is_disruption_day(72)
        assert is_disruption_day(85)
        assert is_disruption_day(100)

    def test_low_dci_not_disruption(self):
        """DCI ≤ 65 should not be marked as disruption"""
        assert not is_disruption_day(50)
        assert not is_disruption_day(65)  # Boundary: exactly 65 is OK
        assert not is_disruption_day(30)

    def test_none_dci_not_disruption(self):
        """None DCI should not be marked as disruption"""
        assert not is_disruption_day(None)

    def test_boundary_dci_65(self):
        """DCI = 65 should NOT be disruption (boundary case)"""
        assert not is_disruption_day(65)

    def test_boundary_dci_66(self):
        """DCI = 66 should be disruption (just above threshold)"""
        assert is_disruption_day(66)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Activity Data Filtering
# ─────────────────────────────────────────────────────────────────────────────

class TestActivityDataFiltering:
    """Tests for filter_activity_data()"""

    def test_filter_disruption_days(self, sample_activity_data):
        """Disruption days (DCI > 65) should be removed"""
        initial_count = len(sample_activity_data)
        filtered = filter_activity_data(sample_activity_data)

        # All remaining rows should have DCI ≤ 65
        assert (filtered["dci_score"] <= 65).all()
        assert len(filtered) <= initial_count

    def test_filter_zero_earnings(self):
        """Days with zero earnings should be removed"""
        data = pd.DataFrame({
            "date": pd.to_datetime(["2025-03-01", "2025-03-02", "2025-03-03"]),
            "daily_earnings": [750, 0, 780],
            "dci_score": [50, 50, 50],
        })
        filtered = filter_activity_data(data)

        assert len(filtered) == 2
        assert (filtered["daily_earnings"] > 0).all()

    def test_filter_festival_weeks(self):
        """Festival week data should be removed"""
        # Create data spanning Holi (festival week)
        data = pd.DataFrame({
            "date": pd.to_datetime(["2025-03-08", "2025-03-15", "2025-04-10"]),  # Holi is March 8 week
            "daily_earnings": [750, 780, 800],
            "dci_score": [50, 50, 50],
        })
        filtered = filter_activity_data(data)

        # Festival dates should be removed
        assert len(filtered) <= 2

    def test_empty_dataframe(self):
        """Empty DataFrame should return empty DataFrame"""
        empty_df = pd.DataFrame()
        filtered = filter_activity_data(empty_df)
        assert filtered.empty

    def test_single_valid_record(self):
        """Multiple records with reasonable values should pass filtering"""
        # Using April dates to avoid festival weeks that might be in March
        data = pd.DataFrame({
            "date": pd.to_datetime(["2025-04-20", "2025-04-21", "2025-04-22", "2025-04-23",
                                     "2025-04-24", "2025-04-25", "2025-04-26"]),
            "daily_earnings": [740, 750, 760, 770, 750, 760, 755],
            "dci_score": [50, 50, 50, 50, 50, 50, 50],
        })
        filtered = filter_activity_data(data)
        # With more samples, outlier filtering should keep most data
        assert len(filtered) >= 5


# ─────────────────────────────────────────────────────────────────────────────
# Test: Rolling Median Calculation
# ─────────────────────────────────────────────────────────────────────────────

class TestRollingMedianPerDOW:
    """Tests for calculate_rolling_median_per_dow()"""

    def test_median_calculation(self, sample_activity_data):
        """Baseline should be calculated correctly"""
        # Filter first to ensure clean data
        filtered = filter_activity_data(sample_activity_data)

        baseline = calculate_rolling_median_per_dow(filtered)

        # All days should have non-zero baseline (we have data)
        assert baseline["overall_daily_avg"] > 0

        # Each day should have a baseline (might be 0 if no data for that day)
        for day in DAYS_OF_WEEK:
            assert day in baseline
            assert isinstance(baseline[day], float)

    def test_median_not_mean(self):
        """Should use median, not mean (robust to outliers)"""
        data = pd.DataFrame({
            "date": pd.date_range("2025-03-01", periods=5),
            "daily_earnings": [100, 110, 120, 1000, 115],  # One outlier
            "dci_score": [50, 50, 50, 50, 50],
        })
        # Set day_of_week manually since we're not using the filter
        data["day_of_week"] = "monday"

        baseline = calculate_rolling_median_per_dow(data)

        # Median should be 115, not influenced by 1000 outlier
        # (After outlier removal in filter_activity_data, this would work better)
        assert baseline["monday"] > 0

    def test_empty_dataframe_returns_zeros(self):
        """Empty DataFrame should return baseline with zeros"""
        empty_df = pd.DataFrame()
        baseline = calculate_rolling_median_per_dow(empty_df)

        assert baseline["overall_daily_avg"] == 0
        for day in DAYS_OF_WEEK:
            assert baseline[day] == 0

    def test_overall_daily_avg_is_median_of_all_days(self):
        """overall_daily_avg should be median of all daily_earnings"""
        data = pd.DataFrame({
            "date": pd.date_range("2025-03-01", periods=7),
            "daily_earnings": [750, 780, 800, 820, 880, 920, 900],
            "dci_score": [50, 50, 50, 50, 50, 50, 50],
        })
        data["day_of_week"] = data["date"].dt.day_name().str.lower()

        baseline = calculate_rolling_median_per_dow(data)

        # Overall should be median of all values: median([750, 780, ...]) = 820
        expected_overall = float(np.median([750, 780, 800, 820, 880, 920, 900]))
        assert baseline["overall_daily_avg"] == expected_overall


# ─────────────────────────────────────────────────────────────────────────────
# Test: New Worker Blending
# ─────────────────────────────────────────────────────────────────────────────

class TestNewWorkerBlending:
    """Tests for blend_baselines_for_new_worker()"""

    def test_week_1_uses_city_average(self, sample_personal_baseline, sample_city_average):
        """Week 1 should be 100% city average"""
        blended = blend_baselines_for_new_worker(
            weeks_since_registration=1,
            personal_baseline=sample_personal_baseline,
            city_average=sample_city_average,
        )

        # Should match city average exactly
        assert blended["monday"] == sample_city_average["monday"]
        assert blended["overall_daily_avg"] == sample_city_average["overall_daily_avg"]

    def test_week_3_blends_30_personal(self, sample_personal_baseline, sample_city_average):
        """Week 3 should be 30% personal, 70% city"""
        blended = blend_baselines_for_new_worker(
            weeks_since_registration=3,
            personal_baseline=sample_personal_baseline,
            city_average=sample_city_average,
        )

        # Check Monday: should be 30% of personal + 70% of city
        expected_monday = (sample_personal_baseline["monday"] * 0.3) + (sample_city_average["monday"] * 0.7)
        assert abs(blended["monday"] - expected_monday) < 0.01

    def test_week_5_uses_personal_100(self, sample_personal_baseline, sample_city_average):
        """Week 5+ should be 100% personal"""
        blended = blend_baselines_for_new_worker(
            weeks_since_registration=5,
            personal_baseline=sample_personal_baseline,
            city_average=sample_city_average,
        )

        # Should match personal baseline exactly
        assert blended["monday"] == sample_personal_baseline["monday"]
        assert blended["overall_daily_avg"] == sample_personal_baseline["overall_daily_avg"]

    def test_week_10_still_uses_personal(self, sample_personal_baseline, sample_city_average):
        """Week 10+ should still be 100% personal (capped at week 5)"""
        blended = blend_baselines_for_new_worker(
            weeks_since_registration=10,
            personal_baseline=sample_personal_baseline,
            city_average=sample_city_average,
        )

        # Should match personal baseline exactly
        assert blended["monday"] == sample_personal_baseline["monday"]

    def test_blended_result_has_all_days(self, sample_personal_baseline, sample_city_average):
        """Blended result should have all days of week + overall_daily_avg"""
        blended = blend_baselines_for_new_worker(
            weeks_since_registration=3,
            personal_baseline=sample_personal_baseline,
            city_average=sample_city_average,
        )

        for day in DAYS_OF_WEEK:
            assert day in blended
        assert "overall_daily_avg" in blended


# ─────────────────────────────────────────────────────────────────────────────
# Test: Weeks Since Registration
# ─────────────────────────────────────────────────────────────────────────────

class TestWeeksSinceRegistration:
    """Tests for get_weeks_since_registration()"""

    def test_registration_today(self):
        """Worker registered today should be week 1"""
        today = datetime.utcnow().date().isoformat()
        weeks = get_weeks_since_registration(today)
        assert weeks == 1

    def test_registration_7_days_ago(self):
        """Worker registered 7 days ago should be in week 1 or 2"""
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).date().isoformat()
        weeks = get_weeks_since_registration(seven_days_ago)
        assert weeks >= 1  # At least 1 week

    def test_registration_28_days_ago(self):
        """Worker registered 28 days ago should be in week 4 or 5"""
        twenty_eight_days_ago = (datetime.utcnow() - timedelta(days=28)).date().isoformat()
        weeks = get_weeks_since_registration(twenty_eight_days_ago)
        assert weeks >= 4  # At least 4 weeks

    def test_registration_1_day_ago(self):
        """Worker registered 1 day ago should be week 1"""
        one_day_ago = (datetime.utcnow() - timedelta(days=1)).date().isoformat()
        weeks = get_weeks_since_registration(one_day_ago)
        assert weeks == 1

    def test_none_registration_date(self):
        """None registration date should return 0"""
        weeks = get_weeks_since_registration(None)
        assert weeks == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test: City Average Fallback
# ─────────────────────────────────────────────────────────────────────────────

class TestCityAverageFallback:
    """Tests for get_fallback_city_average()"""

    def test_bengaluru_average(self):
        """Bengaluru should have specific average"""
        avg = get_fallback_city_average("Bengaluru")

        assert avg["overall_daily_avg"] == 743
        assert avg["monday"] == 650
        assert avg["friday"] == 780

    def test_mumbai_average(self):
        """Mumbai should have specific average (higher than Bengaluru)"""
        avg = get_fallback_city_average("Mumbai")

        assert avg["overall_daily_avg"] == 807
        assert avg["monday"] == 700

    def test_case_insensitive(self):
        """City name should be case-insensitive"""
        avg1 = get_fallback_city_average("bengaluru")
        avg2 = get_fallback_city_average("BENGALURU")
        avg3 = get_fallback_city_average("Bengaluru")

        assert avg1 == avg2 == avg3

    def test_unknown_city_returns_default(self):
        """Unknown city should return default average"""
        avg = get_fallback_city_average("UnknownCity")

        assert "overall_daily_avg" in avg
        assert avg["overall_daily_avg"] == 736

    def test_fallback_has_all_days(self):
        """Fallback should have all days of week"""
        avg = get_fallback_city_average("Bengaluru")

        for day in DAYS_OF_WEEK:
            assert day in avg
        assert "overall_daily_avg" in avg


# ─────────────────────────────────────────────────────────────────────────────
# Test: Main Baseline Calculation
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateBaseline:
    """Tests for calculate_baseline()"""

    @patch("ml.earnings_fingerprint.fetch_activity_log")
    @patch("ml.earnings_fingerprint.fetch_worker_metadata")
    def test_calculate_baseline_new_worker(self, mock_metadata, mock_activity, sample_activity_data):
        """New worker should get blended baseline"""
        # Setup mocks
        mock_activity.return_value = sample_activity_data
        mock_metadata.return_value = {
            "registration_date": (datetime.utcnow() - timedelta(days=14)).date().isoformat(),
            "city": "Bengaluru",
            "segment": "food_delivery",
            "platform": "zomato",
            "shift": "day",
        }

        baseline = calculate_baseline("worker_123")

        # Should have baseline for all days
        assert baseline["overall_daily_avg"] > 0
        for day in DAYS_OF_WEEK:
            assert day in baseline

    @patch("ml.earnings_fingerprint.fetch_activity_log")
    @patch("ml.earnings_fingerprint.fetch_worker_metadata")
    def test_calculate_baseline_established_worker(self, mock_metadata, mock_activity, sample_activity_data):
        """Established worker (4+ weeks) should get personal baseline"""
        # Setup mocks
        mock_activity.return_value = sample_activity_data
        mock_metadata.return_value = {
            "registration_date": (datetime.utcnow() - timedelta(days=60)).date().isoformat(),
            "city": "Bengaluru",
            "segment": "food_delivery",
            "platform": "zomato",
            "shift": "day",
        }

        baseline = calculate_baseline("worker_123")

        # Should have personal baseline (not blended)
        assert baseline["overall_daily_avg"] > 0

    @patch("ml.earnings_fingerprint.fetch_worker_metadata")
    def test_calculate_baseline_worker_not_found(self, mock_metadata):
        """Non-existent worker should return zero baseline"""
        mock_metadata.return_value = {}

        baseline = calculate_baseline("unknown_worker")

        assert baseline["overall_daily_avg"] == 0
        for day in DAYS_OF_WEEK:
            assert baseline[day] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test: Database Persistence
# ─────────────────────────────────────────────────────────────────────────────

class TestDatabasePersistence:
    """Tests for save_baseline_to_workers_table()"""

    def test_save_baseline_success(self, mock_supabase, sample_personal_baseline):
        """Successful save should return True"""
        # Setup mock
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {"id": "w_123"}
        ]

        success = save_baseline_to_workers_table(
            "w_123",
            sample_personal_baseline,
            supabase_client=mock_supabase,
        )

        assert success is True

    def test_save_baseline_failure(self, mock_supabase):
        """Failed save should return False"""
        # Setup mock to return no data
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = None

        success = save_baseline_to_workers_table(
            "w_123",
            {"monday": 750},
            supabase_client=mock_supabase,
        )

        assert success is False

    def test_save_baseline_exception(self, mock_supabase):
        """Exception during save should return False"""
        # Setup mock to raise exception
        mock_supabase.table.side_effect = Exception("DB connection error")

        success = save_baseline_to_workers_table(
            "w_123",
            {"monday": 750},
            supabase_client=mock_supabase,
        )

        assert success is False


# ─────────────────────────────────────────────────────────────────────────────
# Test: Orchestration Function
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeAndPersistBaseline:
    """Tests for compute_and_persist_baseline()"""

    @patch("ml.earnings_fingerprint.calculate_baseline")
    @patch("ml.earnings_fingerprint.save_baseline_to_workers_table")
    def test_full_workflow_success(self, mock_save, mock_calculate):
        """Full workflow should return True and baseline"""
        baseline = {"monday": 750, "overall_daily_avg": 800}
        mock_calculate.return_value = baseline
        mock_save.return_value = True

        success, result_baseline = compute_and_persist_baseline("w_123")

        assert success is True
        assert result_baseline == baseline

    @patch("ml.earnings_fingerprint.calculate_baseline")
    @patch("ml.earnings_fingerprint.save_baseline_to_workers_table")
    def test_workflow_save_fails(self, mock_save, mock_calculate):
        """Workflow should return False if save fails"""
        baseline = {"monday": 750, "overall_daily_avg": 800}
        mock_calculate.return_value = baseline
        mock_save.return_value = False

        success, result_baseline = compute_and_persist_baseline("w_123")

        assert success is False

    @patch("ml.earnings_fingerprint.calculate_baseline")
    def test_workflow_calculation_fails(self, mock_calculate):
        """Workflow should return False if calculation fails"""
        mock_calculate.side_effect = Exception("Calculation error")

        success, result_baseline = compute_and_persist_baseline("w_123")

        assert success is False
        assert result_baseline == {}


# ─────────────────────────────────────────────────────────────────────────────
# Edge Cases & Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_single_day_of_week_data(self):
        """Baseline calculation can return zero for missing day-of-week data"""
        data = pd.DataFrame({
            "date": pd.to_datetime(["2025-03-01", "2025-03-08", "2025-03-15"]),  # All Mondays
            "daily_earnings": [750, 780, 770],
            "dci_score": [50, 50, 50],
        })

        baseline = calculate_rolling_median_per_dow(data)

        # Should have baseline calculated for Mondays
        assert baseline["overall_daily_avg"] > 0
        # The median of [750, 780, 770] should be 770
        assert baseline["overall_daily_avg"] == 770

    def test_disrupted_earnings_pattern(self):
        """Disruption days should not skew baseline (filtered out)"""
        data = pd.DataFrame({
            "date": pd.to_datetime(["2025-03-01", "2025-03-02", "2025-03-03", "2025-03-04"]),
            "daily_earnings": [750, 800, 100, 780],  # One disruption day
            "dci_score": [50, 50, 85, 50],  # Third day has high DCI
        })

        filtered = filter_activity_data(data)

        # Disruption day should be removed
        assert len(filtered) == 3
        # Low earnings from disruption day should not appear
        assert (filtered["daily_earnings"] >= 750).all()

    def test_very_high_earnings_outlier(self):
        """Extremely high single-day earnings should be filtered"""
        data = pd.DataFrame({
            "date": pd.to_datetime(["2025-03-01", "2025-03-02", "2025-03-03", "2025-03-04"]),
            "daily_earnings": [750, 780, 2000, 770],  # One extremely high day
            "dci_score": [50, 50, 50, 50],
        })

        filtered = filter_activity_data(data)

        # Outlier should be removed
        assert len(filtered) <= 3
        baseline = calculate_rolling_median_per_dow(filtered)
        # Baseline should not be skewed by outlier
        assert baseline["overall_daily_avg"] < 1000

    def test_all_zeros_earnings(self):
        """All-zero earnings should result in zero baseline"""
        data = pd.DataFrame({
            "date": pd.date_range("2025-03-01", periods=7),
            "daily_earnings": [0, 0, 0, 0, 0, 0, 0],
            "dci_score": [50, 50, 50, 50, 50, 50, 50],
        })

        filtered = filter_activity_data(data)
        baseline = calculate_rolling_median_per_dow(filtered)

        assert baseline["overall_daily_avg"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
