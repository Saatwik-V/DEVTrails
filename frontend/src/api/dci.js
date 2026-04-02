/**
 * DCI (Disruption Composite Index) API endpoints
 * 
 * IMPORTANT: Backend uses 'pincode' (not 'zone'), and returns combined current + history
 * All aspirational methods removed to match actual backend capabilities.
 */
import apiClient from './client.js';

const ENDPOINT = '/dci';

export const dciAPI = {
  /**
   * Get current DCI score and 24hr history for a pincode
   * Returns: { pincode, current: {...}, history_24h: [...] }
   */
  getByPincode: (pincode) => {
    return apiClient.get(`${ENDPOINT}/${pincode}`);
  },

  /**
   * Get latest DCI alerts across all active zones (score > 65)
   * Used by Dashboard for "Active Zones" widget
   * Returns: { alerts: [ {pincode, area_name, dci_score, triggered_at} ] }
   */
  getLatestAlerts: () => {
    return apiClient.get(`${ENDPOINT}/latest-alerts`);
  },

  /**
   * Get total DCI today (aggregate metric)
   * Returns: { total_dci_today: number }
   */
  getTotalToday: () => {
    return apiClient.get(`${ENDPOINT}/total/today`);
  },
};
