"""
ml/nlp_classifier.py
──────────────────────────────
Zero-shot HuggingFace classifier designed to ingest raw RSS news headlines
and determine the mathematical probability of a civic income-disrupting event
(Bandh, Strike, Curfew).
"""
import logging
import random

logger = logging.getLogger("gigkavach.nlp")

try:
    from transformers import pipeline
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    logger.warning("HuggingFace Transformers or PyTorch not installed locally. Bypassing ML initialization with Mock NLP engine.")
    HUGGINGFACE_AVAILABLE = False

# Global variables act as an in-memory cache to prevent reloading 
# the heavy transformer weights on every single DCI polling cycle.
_classifier = None
_ner_pipeline = None

# Labels we actively penalize workers' zones for
DISRUPTION_LABELS = [
    "bandh", 
    "curfew", 
    "strike", 
    "protest", 
    "shutdown"
]

def load_models():
    """Lazy-loads the huggingface pipelines into memory."""
    if not HUGGINGFACE_AVAILABLE:
        return
        
    global _classifier, _ner_pipeline
    if _classifier is None:
        logger.info("Initializing HuggingFace zero-shot classifier (facebook/bart-large-mnli)...")
        # To avoid massive downloads taking forever in a hackathon demo, you can optionally 
        # swap the model string for a smaller one like typeform/distilbert-base-uncased-mnli
        _classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    
    if _ner_pipeline is None:
        logger.info("Initializing HuggingFace NER pipeline (dslim/bert-base-NER)...")
        # Lightweight NER for extracting location from headline
        _ner_pipeline = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")

def extract_location(text: str) -> str:
    """Uses basic Named Entity Recognition / Regex to isolate the affected geography."""
    load_models()
    try:
        if HUGGINGFACE_AVAILABLE and _ner_pipeline is not None:
            entities = _ner_pipeline(text)
            locations = [ent["word"] for ent in entities if ent["entity_group"] == "LOC"]
        else:
            locations = []
            
        # Fallback to simple hardcoded regex if NER fails to map local Indian city text
        if not locations:
            known_zones = ["Bengaluru", "Karnataka", "Koramangala", "Indiranagar", "Mumbai", "Delhi", "Agara"]
            for zone in known_zones:
                if zone.lower() in text.lower():
                    return zone
            return "Unknown"
            
        return ", ".join(locations)
    except Exception as e:
        logger.warning(f"NER location extraction failed: {e}")
        return "Unknown"

def analyze_headline(headline: str) -> dict:
    """
    Evaluates a single RSS headline against Disruption labels.
    Returns the maximum confidence score, the winning label, and inferred location.
    """
    load_models()
    
    try:
        if not HUGGINGFACE_AVAILABLE:
            # --- MOCK CLASSIFIER FOR LOCAL 3.13 ENVIRONMENTS ---
            headline_lower = headline.lower()
            is_disrupt = any(word in headline_lower for word in DISRUPTION_LABELS)
            mock_score = round(random.uniform(0.75, 0.98), 3) if is_disrupt else round(random.uniform(0.01, 0.20), 3)
            location = extract_location(headline)
            top_label = next((w for w in DISRUPTION_LABELS if w in headline_lower), "normal")
            return {
                "is_disruption": is_disrupt,
                "headline": headline,
                "top_label": top_label,
                "confidence_score": mock_score,
                "location": location
            }

        # --- REAL HUGGINGFACE CLASSIFIER ---
        result = _classifier(headline, DISRUPTION_LABELS)
        top_label = result["labels"][0]
        top_score = result["scores"][0]
        
        location = extract_location(headline)
        is_disruption = top_score >= 0.70  # 70% strict confidence threshold
        
        return {
            "is_disruption": is_disruption,
            "headline": headline,
            "top_label": top_label,
            "confidence_score": round(top_score, 3),
            "location": location
        }
    except Exception as e:
        logger.error(f"NLP Classification failed for '{headline}': {e}")
        return {
            "is_disruption": False,
            "headline": headline,
            "top_label": "error",
            "confidence_score": 0.0,
            "location": "Unknown"
        }

if __name__ == "__main__":
    import json
    
    # ─── QUICK SANITY TEST ───
    print("Loading models... (this may take a few seconds on first run)")
    test_headlines = [
        "Karnataka bandh: All schools and delivery services suspended in Bengaluru tomorrow",
        "New Italian restaurant opens on 100ft Road in Koramangala",
        "Auto union announces complete strike over aggregator prices",
    ]
    
    results = []
    for hl in test_headlines:
        res = analyze_headline(hl)
        results.append(res)
        
    print("\n--- NLP ANALYSIS TRACE ---")
    print(json.dumps(results, indent=2))
