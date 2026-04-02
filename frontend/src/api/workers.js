/**
 * Worker API endpoints
 */
import apiClient from './client.js';

const ENDPOINT = '/api/workers';

export const workerAPI = {
  /**
   * Get all workers with pagination and filters
   */
  getAll: async (params = {}) => {
    try {
      return await apiClient.get(ENDPOINT, { params });
    } catch {
      return await apiClient.get('/api/api/workers', { params });
    }
  },

  /**
   * Get single worker by ID
   */
  getById: async (id) => {
    try {
      return await apiClient.get(`${ENDPOINT}/${id}`);
    } catch {
      return await apiClient.get(`/api/api/workers/${id}`);
    }
  },
};
