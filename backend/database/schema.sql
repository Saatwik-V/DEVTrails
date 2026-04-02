-- database/schema.sql
-- Run this in your Supabase SQL Editor to create the necessary tables for GigKavach
-- Task 2+3 Fix: Added missing columns for workers & policies, and added the claims table.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════════════════════════
-- 1. WORKERS TABLE
-- Task 2 Fix: Added phone_number, platform, gig_score, coverage_active_from, onboarded_at
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS workers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255),
    phone VARCHAR(20),                              -- legacy alias
    phone_number VARCHAR(20) UNIQUE,                -- used by workers.py registration
    platform VARCHAR(50),                           -- 'zomato' | 'swiggy'
    upi_id VARCHAR(100),
    pin_codes TEXT[] DEFAULT ARRAY[]::TEXT[],
    shift VARCHAR(50),                              -- 'morning' | 'day' | 'night' | 'flexible'
    shift_start TIME,
    shift_end TIME,
    language VARCHAR(50) DEFAULT 'en',
    plan VARCHAR(50) DEFAULT 'basic',               -- 'basic' | 'plus' | 'pro'
    coverage_pct INTEGER DEFAULT 40,
    gig_score NUMERIC(5,2) DEFAULT 100.0,           -- Trust score, starts at perfect 100
    coverage_active_from TIMESTAMP WITH TIME ZONE,  -- 24-hr delay for new worker moral hazard prevention
    onboarded_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    is_active BOOLEAN DEFAULT true,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_workers_is_active ON workers (is_active);
CREATE INDEX IF NOT EXISTS idx_workers_created_at ON workers (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workers_phone_number ON workers (phone_number);
CREATE INDEX IF NOT EXISTS idx_workers_pincode ON workers USING GIN (pin_codes);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 2. POLICIES TABLE
-- Task 2 Fix: Added shift, pin_codes, week_end, premium_paid, is_active
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    plan VARCHAR(50) DEFAULT 'basic',
    shift VARCHAR(50),                              -- snapshot of worker shift at policy creation
    pin_codes TEXT[] DEFAULT ARRAY[]::TEXT[],
    status VARCHAR(50) DEFAULT 'active',
    week_start DATE NOT NULL,
    week_end DATE,                                  -- Mon-Sun cycle end
    coverage_pct INTEGER DEFAULT 40,
    premium_paid NUMERIC(8,2) DEFAULT 0,            -- ₹ weekly premium collected
    weekly_premium INTEGER DEFAULT 0,               -- legacy field
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_policies_worker_id ON policies (worker_id);
CREATE INDEX IF NOT EXISTS idx_policies_week_start ON policies (week_start DESC);
CREATE INDEX IF NOT EXISTS idx_policies_is_active ON policies (is_active);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 3. PAYOUTS TABLE
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS payouts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    claim_id UUID,                                  -- FK to claims (nullable for SLA auto-payouts)
    base_amount NUMERIC(10,2) DEFAULT 0,
    surge_multiplier DECIMAL(5, 2) DEFAULT 1.0,
    final_amount NUMERIC(10,2) DEFAULT 0,
    fraud_score DECIMAL(5, 2) DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',           -- 'pending'|'processing'|'completed'|'failed'
    triggered_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_payouts_worker_id ON payouts (worker_id);
CREATE INDEX IF NOT EXISTS idx_payouts_triggered_at ON payouts (triggered_at DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 4. CLAIMS TABLE — Task 3 New: required by cron/claims_trigger.py
-- Created when DCI ≥ 65 for a worker's zone. Processed every 5 min.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,

    -- Disruption context (from DCI engine at trigger time)
    dci_score NUMERIC(5,2) NOT NULL,
    disruption_duration INTEGER DEFAULT 0,          -- minutes (0-480)
    disruption_type VARCHAR(100) DEFAULT 'Unknown', -- Rain|Heatwave|Flood|Traffic_Gridlock|Bandh
    baseline_earnings NUMERIC(10,2) DEFAULT 0,      -- worker's daily baseline at claim time

    -- Geospatial context
    city VARCHAR(100) DEFAULT '',
    pincode VARCHAR(20),
    zone_density VARCHAR(20) DEFAULT 'Mid',         -- High|Mid|Low

    -- Temporal context (used by XGBoost features)
    hour_of_day INTEGER DEFAULT 0,
    day_of_week INTEGER DEFAULT 0,
    shift VARCHAR(50) DEFAULT 'Morning',

    -- Pipeline status tracking
    status VARCHAR(50) DEFAULT 'pending',           -- pending|processing|approved|rejected|error
    fraud_score NUMERIC(5,4),
    fraud_decision VARCHAR(50),                     -- APPROVE|FLAG_50|BLOCK
    is_fraud BOOLEAN,
    payout_amount NUMERIC(10,2),
    payout_multiplier NUMERIC(5,3),
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_claims_worker_id ON claims (worker_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims (status);
CREATE INDEX IF NOT EXISTS idx_claims_created_at ON claims (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_claims_pincode ON claims (pincode);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 5. ACTIVITIES TABLE
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    description TEXT,
    date TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS idx_activities_worker_id ON activities (worker_id);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 6. ACTIVITY_LOG TABLE
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    log_date TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    first_login_at TIMESTAMP WITH TIME ZONE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    active_hours INTEGER DEFAULT 0,
    orders_completed INTEGER DEFAULT 0,
    estimated_earnings NUMERIC(10,2) DEFAULT 0,
    zone_pin_codes TEXT[] DEFAULT ARRAY[]::TEXT[],
    platform_status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS idx_activity_log_worker_id ON activity_log (worker_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_date ON activity_log (log_date DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 7. ACTIVITY_HISTORY TABLE
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS activity_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    history_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS idx_activity_history_worker_id ON activity_history (worker_id);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 8. DCI_LOGS TABLE: Tracks every 5-min calculation for active zones
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dci_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pincode VARCHAR(20) NOT NULL,
    total_score INTEGER NOT NULL,
    rainfall_score INTEGER NOT NULL DEFAULT 0,
    aqi_score INTEGER NOT NULL DEFAULT 0,
    heat_score INTEGER NOT NULL DEFAULT 0,
    social_score INTEGER NOT NULL DEFAULT 0,
    platform_score INTEGER NOT NULL DEFAULT 0,
    severity_tier VARCHAR(50) NOT NULL,
    ndma_override_active BOOLEAN DEFAULT false,
    shift_active VARCHAR(50),                       -- shift window active at calculation time
    is_shift_window_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS idx_dci_logs_pincode_time ON dci_logs (pincode, created_at DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 9. FRAUD_FLAGS TABLE
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS fraud_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    flag_type VARCHAR(100),
    severity VARCHAR(50),
    message TEXT,
    is_resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    resolved_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_fraud_flags_worker_id ON fraud_flags (worker_id);

-- Appeals table for worker disputes on fraud flags or payouts
CREATE TABLE IF NOT EXISTS appeals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    phone VARCHAR(20),
    reason TEXT,
    status VARCHAR(50) DEFAULT 'open',          -- open|reviewing|approved|rejected|resolved
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    expires_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_appeals_worker_id ON appeals (worker_id);
CREATE INDEX IF NOT EXISTS idx_appeals_status ON appeals (status);
CREATE INDEX IF NOT EXISTS idx_appeals_created_at ON appeals (created_at DESC);

