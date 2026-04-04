/**
 * Frontend constants and API URLs
 */

const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  `${VITE_API_URL}`;  // Always use local backend in development

const DEFAULT_WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL ||
  `${VITE_API_URL}`;  // Always use local WebSocket in development

// API Base Configuration
export const API_CONFIG = {
  BASE_URL: DEFAULT_API_BASE_URL,
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
};

// WebSocket Configuration
export const WS_CONFIG = {
  BASE_URL: DEFAULT_WS_BASE_URL,
  RECONNECT_ATTEMPTS: 5,
  RECONNECT_DELAY: 3000,
};

// DCI Configuration
export const DCI_CONFIG = {
  MIN_VALUE: 0,
  MAX_VALUE: 100,
  CRITICAL_THRESHOLD: 75,
  HIGH_THRESHOLD: 60,
  MEDIUM_THRESHOLD: 40,
  LOW_THRESHOLD: 0,
  UPDATE_INTERVAL: 5000, // 5 seconds
};

// Fraud Configuration
export const FRAUD_CONFIG = {
  SIGNALS_COUNT: 6,
  SIGNAL_LABELS: ['GPS', 'IP', 'Velocity', 'Entropy', 'Cluster', 'Loyalty'],
  HIGH_RISK_THRESHOLD: 5,
  MEDIUM_RISK_THRESHOLD: 3,
  LOW_RISK_THRESHOLD: 0,
  TIERS: {
    1: 'Tier 1',
    2: 'Tier 2',
    3: 'Tier 3',
  },
};

// Payout Configuration
export const PAYOUT_CONFIG = {
  STATUS_TYPES: ['paid', 'pending', 'failed', 'escrowed'],
  PLAN_TIERS: ['Shield Basic', 'Shield Plus', 'Shield Pro'],
  ESCROW_HOLD_PERCENTAGE: 50,
};

// Color Configuration
export const COLORS = {
  BRAND: {
    DARK: '#0F1B2D',
    DARKER: '#162236',
    ACCENT: '#FF6B35',
    SAFE: '#22C55E',
    WARNING: '#F59E0B',
    DANGER: '#EF4444',
  },
  STATUS: {
    ACTIVE: '#22C55E',
    INACTIVE: '#9CA3AF',
    PAID: '#22C55E',
    PENDING: '#F59E0B',
    HIGH_RISK: '#EF4444',
    MEDIUM_RISK: '#F59E0B',
    LOW_RISK: '#22C55E',
  },
  DCI: {
    CRITICAL: '#7F1D1D',
    HIGH: '#EF4444',
    MEDIUM: '#F59E0B',
    LOW: '#22C55E',
    EXCELLENT: '#059669',
  },
};

// Route Configuration
export const ROUTES = {
  DASHBOARD: '/dashboard',
  WORKERS: '/workers',
  WORKERS_DETAIL: '/workers/:id',
  LIVE_MAP: '/map',
  PAYOUTS: '/payouts',
  FRAUD: '/fraud',
  SETTINGS: '/settings',
  WORKER_STATUS: '/worker/status',
  WORKER_HISTORY: '/worker/history',
  WORKER_PROFILE: '/worker/profile',
};

// Pagination Configuration
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  PAGE_SIZES: [10, 20, 50, 100],
};

// Toast Configuration
export const TOAST_DURATION = 4000; // milliseconds

// Local Storage Keys
export const STORAGE_KEYS = {
  THEME: 'gigkavach_theme',
  USER_PREFERENCES: 'gigkavach_user_prefs',
  LAST_VIEWED_PAGE: 'gigkavach_last_page',
  AUTH_TOKEN: 'gigkavach_auth_token',
};

// Feature Flags
export const FEATURE_FLAGS = {
  ENABLE_LIVE_MAP: true,
  ENABLE_FORECAST: true,
  ENABLE_SIMULATION: true,
  ENABLE_SANDBOX_MODE: import.meta.env.VITE_SANDBOX_MODE === 'true',
};
