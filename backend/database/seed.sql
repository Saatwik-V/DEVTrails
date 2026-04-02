-- database/seed.sql
-- Sample data for testing the GigKavach APIs

-- ═══════════════════════════════════════════════════════════════════════════════
-- INSERT SAMPLE WORKERS
-- ═══════════════════════════════════════════════════════════════════════════════
INSERT INTO workers (id, name, phone, upi_id, pin_codes, shift, shift_start, shift_end, language, plan, coverage_pct, is_active, last_seen_at)
VALUES
  ('550e8400-e29b-41d4-a716-446655440001', 'Rajesh Kumar', '9876543210', 'rajesh.kumar@upi', ARRAY['560001', '560002'], 'morning', '06:00:00', '14:00:00', 'Hindi', 'basic', 85, true, NOW() - INTERVAL '2 hours'),
  ('550e8400-e29b-41d4-a716-446655440002', 'Priya Singh', '9123456789', 'priya.singh@upi', ARRAY['560003', '560004'], 'day', '14:00:00', '22:00:00', 'Kannada', 'plus', 90, true, NOW() - INTERVAL '1 hour'),
  ('550e8400-e29b-41d4-a716-446655440003', 'Amit Patel', '8765432198', 'amit.patel@upi', ARRAY['560005'], 'night', '22:00:00', '06:00:00', 'English', 'pro', 95, true, NOW()),
  ('550e8400-e29b-41d4-a716-446655440004', 'Deepa Mehta', '7654321098', 'deepa.mehta@upi', ARRAY['560006', '560007'], 'morning', '06:00:00', '14:00:00', 'Telugu', 'basic', 60, true, NOW() - INTERVAL '30 minutes'),
  ('550e8400-e29b-41d4-a716-446655440005', 'Vikram Das', '6543210987', 'vikram.das@upi', ARRAY['560008'], 'day', '14:00:00', '22:00:00', 'Tamil', 'plus', 75, false, NOW() - INTERVAL '5 hours')
ON CONFLICT DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════════════════
-- INSERT SAMPLE POLICIES
-- ═══════════════════════════════════════════════════════════════════════════════
INSERT INTO policies (id, worker_id, plan, status, week_start, coverage_pct, weekly_premium)
VALUES
  ('650e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001', 'basic', 'active', CURRENT_DATE - INTERVAL '6 days', 85, 69),
  ('650e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440002', 'plus', 'active', CURRENT_DATE - INTERVAL '6 days', 90, 89),
  ('650e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440003', 'pro', 'active', CURRENT_DATE - INTERVAL '6 days', 95, 99),
  ('650e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440004', 'basic', 'active', CURRENT_DATE - INTERVAL '6 days', 60, 69),
  ('650e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440005', 'plus', 'inactive', CURRENT_DATE - INTERVAL '13 days', 75, 89)
ON CONFLICT DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════════════════
-- INSERT SAMPLE PAYOUTS
-- ═══════════════════════════════════════════════════════════════════════════════
INSERT INTO payouts (id, worker_id, base_amount, surge_multiplier, final_amount, fraud_score, status, triggered_at)
VALUES
  ('750e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001', 15000, 1.2, 18000, 0.15, 'completed', NOW() - INTERVAL '2 days'),
  ('750e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440001', 12000, 1.0, 12000, 0.05, 'completed', NOW() - INTERVAL '4 days'),
  ('750e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440002', 18000, 1.3, 23400, 0.08, 'completed', NOW() - INTERVAL '1 day'),
  ('750e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440002', 20000, 1.0, 20000, 0.12, 'pending', NOW()),
  ('750e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440003', 25000, 1.5, 37500, 0.02, 'completed', NOW() - INTERVAL '6 hours')
ON CONFLICT DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════════════════
-- INSERT SAMPLE ACTIVITIES
-- ═══════════════════════════════════════════════════════════════════════════════
INSERT INTO activities (id, worker_id, description, date)
VALUES
  ('850e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001', 'Completed 15 orders', NOW() - INTERVAL '1 day'),
  ('850e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440001', 'Payout received: ₹18,000', NOW() - INTERVAL '2 days'),
  ('850e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440002', 'Completed 22 orders', NOW() - INTERVAL '1 hour'),
  ('850e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440002', 'Surge pricing detected: 1.3x', NOW()),
  ('850e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440003', 'Night shift started', NOW() - INTERVAL '3 hours')
ON CONFLICT DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════════════════
-- INSERT SAMPLE ACTIVITY_LOG
-- ═══════════════════════════════════════════════════════════════════════════════
INSERT INTO activity_log (id, worker_id, log_date, first_login_at, last_login_at, active_hours, orders_completed, estimated_earnings, zone_pin_codes, platform_status)
VALUES
  ('950e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001', NOW() - INTERVAL '1 day', NOW() - INTERVAL '8 hours', NOW() - INTERVAL '2 hours', 8, 15, 12500, ARRAY['560001', '560002'], 'active'),
  ('950e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440002', NOW() - INTERVAL '1 day', NOW() - INTERVAL '10 hours', NOW() - INTERVAL '1 hour', 9, 22, 18500, ARRAY['560003', '560004'], 'active'),
  ('950e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440003', NOW() - INTERVAL '1 day', NOW() - INTERVAL '4 hours', NOW() - INTERVAL '30 minutes', 4, 12, 9800, ARRAY['560005'], 'active'),
  ('950e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440004', NOW() - INTERVAL '2 days', NOW() - INTERVAL '48 hours', NOW() - INTERVAL '36 hours', 6, 10, 8200, ARRAY['560006', '560007'], 'inactive'),
  ('950e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440005', NOW() - INTERVAL '3 days', NOW() - INTERVAL '72 hours', NOW() - INTERVAL '60 hours', 7, 14, 11500, ARRAY['560008'], 'dormant')
ON CONFLICT DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════════════════
-- INSERT SAMPLE ACTIVITY_HISTORY
-- ═══════════════════════════════════════════════════════════════════════════════
INSERT INTO activity_history (id, worker_id, history_data)
VALUES
  ('a50e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001', '{"totalOrders": 145, "totalEarnings": 125000, "avgDailyOrders": 15, "lastActive": "2026-03-27"}'),
  ('a50e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440002', '{"totalOrders": 198, "totalEarnings": 165000, "avgDailyOrders": 22, "lastActive": "2026-03-27"}'),
  ('a50e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440003', '{"totalOrders": 85, "totalEarnings": 72000, "avgDailyOrders": 12, "lastActive": "2026-03-27"}'),
  ('a50e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440004', '{"totalOrders": 120, "totalEarnings": 98000, "avgDailyOrders": 10, "lastActive": "2026-03-25"}'),
  ('a50e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440005', '{"totalOrders": 175, "totalEarnings": 142000, "avgDailyOrders": 14, "lastActive": "2026-03-24"}')
ON CONFLICT DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════════════════
-- INSERT SAMPLE FRAUD_FLAGS
-- ═══════════════════════════════════════════════════════════════════════════════
INSERT INTO fraud_flags (id, worker_id, flag_type, severity, message, is_resolved)
VALUES
  ('b50e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001', 'unusual_location', 'low', 'Location jump detected but resolved', true),
  ('b50e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440002', 'high_earnings_spike', 'medium', 'Unusual surge in earnings', false),
  ('b50e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440003', 'gps_spoofing', 'high', 'GPS coordinate mismatch with cell tower', false)
ON CONFLICT DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════════════════
-- INSERT SAMPLE DCI_LOGS
-- ═══════════════════════════════════════════════════════════════════════════════
INSERT INTO dci_logs (id, pincode, total_score, rainfall_score, aqi_score, heat_score, social_score, platform_score, severity_tier, is_shift_window_active)
VALUES
  ('c50e8400-e29b-41d4-a716-446655440001', '560001', 72, 15, 20, 25, 8, 4, 'moderate', true),
  ('c50e8400-e29b-41d4-a716-446655440002', '560002', 85, 25, 30, 20, 7, 3, 'high', true),
  ('c50e8400-e29b-41d4-a716-446655440003', '560003', 45, 5, 10, 15, 10, 5, 'low', true),
  ('c50e8400-e29b-41d4-a716-446655440004', '560004', 62, 18, 22, 18, 2, 2, 'moderate', true),
  ('c50e8400-e29b-41d4-a716-446655440005', '560005', 95, 35, 35, 20, 3, 2, 'critical', false)
ON CONFLICT DO NOTHING;
