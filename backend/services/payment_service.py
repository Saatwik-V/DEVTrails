"""
services/payout_service.py
──────────────────────────────────────────────────────────────
Payout Calculation Service

Integrates XGBoost v3 model with claims processing pipeline.
Computes dynamic payout multipliers based on:
  - DCI (Disruption Composite Index)
  - Worker location and shift
  - Disruption type
  - Baseline earnings

Payout Formula:
  payout = baseline_earnings × (disruption_duration / 480) × multiplier
  
  Where multiplier ∈ [1.0, 5.0] is predicted by XGBoost model
"""

import logging
from typing import Dict, Optional
from datetime import datetime

from ml.xgboost_loader import (
    extract_features,
    predict_multiplier,
    predict_with_confidence,
    get_model_info,
)

# Setup logging — use child of gigkavach logger for unified log filtering
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gigkavach.payout_service")


class PayoutCalculationError(Exception):
    """Raised when payout calculation fails."""
    pass


def calculate_payout(
    baseline_earnings: float,
    disruption_duration: int,
    dci_score: float,
    worker_id: str,
    city: str,
    zone_density: str,
    shift: str,
    disruption_type: str,
    hour_of_day: int,
    day_of_week: int,
    include_confidence: bool = True,
) -> Dict:
    """
    Calculate dynamic payout for a disrupted gig worker.
    
    This is the main integration point between claims processing and the
    XGBoost v3 payout model. The model predicts a multiplier (1.0–5.0x)
    based on disruption severity and worker characteristics.
    
    Args:
        baseline_earnings: Daily baseline earnings (₹)
        disruption_duration: Duration of disruption (minutes, 0–480 max)
        dci_score: Disruption Composite Index (0–100)
        worker_id: Worker identifier for logging/audit trail
        city: Worker city ('Chennai', 'Delhi', 'Mumbai')
        zone_density: Geographic zone ('High'=CBD, 'Mid'=suburbs, 'Low'=outskirts)
        shift: Worker shift ('Morning', 'Night', etc.)
        disruption_type: Type of disruption ('Rain', 'Heatwave', 'Traffic_Gridlock', 'Flood')
        hour_of_day: Hour of disruption (0–23)
        day_of_week: Day of week (0=Monday, 6=Sunday)
        include_confidence: Include confidence metrics in output
        
    Returns:
        Dict with:
          - payout: Calculated payout amount (₹)
          - multiplier: XGBoost-predicted multiplier (1.0–5.0x)
          - confidence: Prediction confidence (optional)
          - breakdown: Calculation components
          - timestamp: Calculation timestamp
          
    Raises:
        PayoutCalculationError: If calculation fails
        
    Example:
        >>> result = calculate_payout(
        ...     baseline_earnings=850,
        ...     disruption_duration=240,
        ...     dci_score=78,
        ...     worker_id='WORKER_123',
        ...     city='Mumbai',
        ...     zone_density='Mid',
        ...     shift='Night',
        ...     disruption_type='Rain',
        ...     hour_of_day=19,
        ...     day_of_week=4,
        ... )
        >>> print(f"Payout: ₹{result['payout']:.0f}")
        >>> print(f"Multiplier: {result['multiplier']:.2f}x")
    """
    try:
        # Validate inputs
        _validate_payout_inputs(
            baseline_earnings,
            disruption_duration,
            dci_score,
            city,
            zone_density,
            shift,
            disruption_type,
            hour_of_day,
            day_of_week,
        )
        
        logger.info(
            f"Calculating payout for {worker_id}: "
            f"baseline=₹{baseline_earnings}, duration={disruption_duration}min, DCI={dci_score}"
        )
        
        # Step 1: Extract features from raw inputs
        # This automatically encodes categories and builds all 20 v3 features
        features = extract_features(
            dci_score=dci_score,
            baseline_earnings=baseline_earnings,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            city=city,
            zone_density=zone_density,
            shift=shift,
            disruption_type=disruption_type,
        )
        
        logger.debug(f"Features extracted for {worker_id}: {len(features)} features")
        
        # Step 2: Get multiplier from model
        if include_confidence:
            # Get prediction with confidence metrics
            model_result = predict_with_confidence(features)
            multiplier = model_result['multiplier']
            confidence = model_result['confidence']
            model_r2 = model_result['model_r2']
        else:
            # Simple prediction without confidence
            multiplier = predict_multiplier(features)
            confidence = None
            model_r2 = None
        
        logger.debug(f"Model predicted multiplier: {multiplier:.3f}x for {worker_id}")
        
        # Step 3: Apply payout formula
        # Payout = Baseline × (Duration / 480) × Multiplier
        # Where 480 minutes = 8 hour workday reference
        duration_factor = disruption_duration / 480.0
        payout = baseline_earnings * duration_factor * multiplier
        
        # Sanity checks
        if payout < 0:
            raise PayoutCalculationError(f"Calculated negative payout: ₹{payout}")
        if payout > baseline_earnings * 5.0:  # Max possible: 480 min × 5.0 multiplier
            logger.warning(
                f"Payout unusually high (₹{payout:.0f}) for {worker_id}. "
                f"Check DCI={dci_score}, multiplier={multiplier}"
            )
        
        result = {
            'payout': round(payout, 2),
            'multiplier': round(multiplier, 3),
            'breakdown': {
                'baseline_earnings': baseline_earnings,
                'duration_minutes': disruption_duration,
                'duration_factor': round(duration_factor, 3),
                'dci_score': dci_score,
                'city': city,
                'zone_density': zone_density,
                'shift': shift,
                'disruption_type': disruption_type,
            },
            'timestamp': datetime.now().isoformat(),
            'worker_id': worker_id,
        }
        
        if include_confidence:
            result['confidence'] = round(confidence, 3)
            result['model_r2'] = round(model_r2, 3)
            result['recommendation'] = model_result['recommendation']
        
        logger.info(
            f"✅ Payout calculated for {worker_id}: "
            f"₹{payout:.0f} (multiplier {multiplier:.2f}x)"
        )
        
        return result
        
    except PayoutCalculationError as e:
        logger.error(f"❌ Payout calculation failed for {worker_id}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in payout calculation for {worker_id}: {str(e)}")
        raise PayoutCalculationError(f"Payout calculation failed: {str(e)}")


def get_payout_model_info() -> Dict:
    """
    Get metadata about the payout prediction model.
    
    Returns:
        Dict with model name, creation date, hyperparameters, test R², etc.
        
    Example:
        >>> info = get_payout_model_info()
        >>> print(f"Model: {info['name']}")
        >>> print(f"Test R²: {info['test_r2']:.3f}")
    """
    return get_model_info()


def _validate_payout_inputs(
    baseline_earnings: float,
    disruption_duration: int,
    dci_score: float,
    city: str,
    zone_density: str,
    shift: str,
    disruption_type: str,
    hour_of_day: int,
    day_of_week: int,
) -> None:
    """Validate all payout calculation inputs."""
    
    # Baseline earnings
    if not isinstance(baseline_earnings, (int, float)):
        raise PayoutCalculationError(f"baseline_earnings must be numeric, got {type(baseline_earnings)}")
    if baseline_earnings < 100 or baseline_earnings > 2500:
        logger.warning(f"baseline_earnings=₹{baseline_earnings} outside typical range [100, 2500]")
    
    # Disruption duration
    if not isinstance(disruption_duration, int):
        raise PayoutCalculationError(f"disruption_duration must be integer (minutes)")
    if disruption_duration < 0 or disruption_duration > 480:
        raise PayoutCalculationError(f"disruption_duration={disruption_duration} outside [0, 480]")
    
    # DCI score
    if not isinstance(dci_score, (int, float)):
        raise PayoutCalculationError(f"dci_score must be numeric")
    if dci_score < 0 or dci_score > 100:
        logger.warning(f"dci_score={dci_score} outside typical range [0, 100]")
    
    # City
    valid_cities = {'Chennai', 'Delhi', 'Mumbai'}
    if city not in valid_cities:
        raise PayoutCalculationError(f"Invalid city '{city}', must be one of {valid_cities}")
    
    # Zone density
    valid_zones = {'High', 'Mid', 'Low'}
    if zone_density not in valid_zones:
        raise PayoutCalculationError(f"Invalid zone_density '{zone_density}', must be one of {valid_zones}")
    
    # Shift
    valid_shifts = {'Morning', 'Night'}  # Evening is implicit
    if shift not in valid_shifts:
        logger.warning(f"shift='{shift}' not in typical set {valid_shifts}")
    
    # Disruption type
    valid_types = {'Rain', 'Heatwave', 'Traffic_Gridlock', 'Flood'}
    if disruption_type not in valid_types:
        raise PayoutCalculationError(
            f"Invalid disruption_type '{disruption_type}', must be one of {valid_types}"
        )
    
    # Hour of day
    if not isinstance(hour_of_day, int):
        raise PayoutCalculationError(f"hour_of_day must be integer")
    if hour_of_day < 0 or hour_of_day > 23:
        raise PayoutCalculationError(f"hour_of_day={hour_of_day} outside [0, 23]")
    
    # Day of week
    if not isinstance(day_of_week, int):
        raise PayoutCalculationError(f"day_of_week must be integer")
    if day_of_week < 0 or day_of_week > 6:
        raise PayoutCalculationError(f"day_of_week={day_of_week} outside [0, 6]")


# ──────────────────────────────────────────────────────────
# Integration with claims pipeline
# ──────────────────────────────────────────────────────────

def process_claim_for_payout(claim: Dict) -> Dict:
    """
    Process a claim through the payout calculation pipeline.
    
    This is called by eligibility_service.py after validating worker
    eligibility and policy coverage.
    
    Args:
        claim: Dict with claim details from claims_trigger.py
        
    Returns:
        Dict with payout details, ready for fraud detection and payment
    """
    return calculate_payout(
        baseline_earnings=claim['baseline_earnings'],
        disruption_duration=claim['disruption_duration'],
        dci_score=claim['dci_score'],
        worker_id=claim['worker_id'],
        city=claim['city'],
        zone_density=claim.get('zone_density', 'Mid'),  # Default to Mid if not provided
        shift=claim['shift'],
        disruption_type=claim['disruption_type'],
        hour_of_day=claim['hour_of_day'],
        day_of_week=claim['day_of_week'],
        include_confidence=True,
    )


# ──────────────────────────────────────────────────────────
# Example usage & testing
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Show model info
    print("\n📊 XGBoost Payout Model Info:")
    info = get_payout_model_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # Example 1: Heavy disruption, night shift (high payout expected)
    print("\n\n📌 Example 1: Heavy disruption (DCI=78), Night shift → High payout")
    result1 = calculate_payout(
        baseline_earnings=850,
        disruption_duration=240,  # 4 hours
        dci_score=78,
        worker_id='DEMO_WORKER_001',
        city='Mumbai',
        zone_density='Mid',
        shift='Night',
        disruption_type='Rain',
        hour_of_day=19,
        day_of_week=4,
    )
    print(f"  Payout: ₹{result1['payout']:.0f}")
    print(f"  Multiplier: {result1['multiplier']:.2f}x")
    print(f"  Confidence: {result1['confidence']:.1%}")
    print(f"  Duration: {result1['breakdown']['duration_minutes']}min \u00d7 {result1['breakdown']['duration_factor']} factor")
    
    # Example 2: Mild disruption, low impact (low payout expected)
    print("\n\n📌 Example 2: Mild disruption (DCI=25), Morning shift → Low payout")
    result2 = calculate_payout(
        baseline_earnings=1200,
        disruption_duration=60,  # 1 hour
        dci_score=25,
        worker_id='DEMO_WORKER_002',
        city='Chennai',
        zone_density='Low',
        shift='Morning',
        disruption_type='Rain',
        hour_of_day=8,
        day_of_week=1,
    )
    print(f"  Payout: ₹{result2['payout']:.0f}")
    print(f"  Multiplier: {result2['multiplier']:.2f}x")
    print(f"  Confidence: {result2['confidence']:.1%}")
    print(f"  Duration: {result2['breakdown']['duration_minutes']}min \u00d7 {result2['breakdown']['duration_factor']} factor")
    
    # Example 3: Extreme event (traffic gridlock, high DCI)
    print("\n\n📌 Example 3: Extreme event (traffic gridlock, DCI=92), all day")
    result3 = calculate_payout(
        baseline_earnings=950,
        disruption_duration=480,  # Full 8-hour day
        dci_score=92,
        worker_id='DEMO_WORKER_003',
        city='Delhi',
        zone_density='High',
        shift='Morning',
        disruption_type='Traffic_Gridlock',
        hour_of_day=9,
        day_of_week=2,
    )
    print(f"  Payout: ₹{result3['payout']:.0f}")
    print(f"  Multiplier: {result3['multiplier']:.2f}x")
    print(f"  Confidence: {result3['confidence']:.1%}")
    print(f"  Duration: {result3['breakdown']['duration_minutes']}min \u00d7 {result3['breakdown']['duration_factor']} factor")
    
    print("\n\n✅ Payout service fully integrated with XGBoost v3 model!")
