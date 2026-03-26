-- database/schema.sql
-- Run this in your Supabase SQL Editor to create the necessary tables for GigKavach DCI Logging

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- DCI Logs Table: Tracks every 5-min calculation for active zones
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
    is_shift_window_active BOOLEAN DEFAULT true, -- Tracks if heat/rules apply for current shift
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- Index for fast queries by pincode and time (needed for the history API endpoint)
CREATE INDEX idx_dci_logs_pincode_time ON dci_logs (pincode, created_at DESC);

-- Enable Row Level Security (RLS) but allow server-side bypass
ALTER TABLE dci_logs ENABLE ROW LEVEL SECURITY;

-- If you want frontend clients to read logs directly, you can create a policy:
-- CREATE POLICY "Allow public read access to DCI logs" ON dci_logs FOR SELECT USING (true);
