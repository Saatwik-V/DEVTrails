import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:3000",
});

export const dashboardAPI = {
  getTodayPayout: () => api.get("/api/payouts/total/today"),

  getTodayDCI: () => api.get("/dci/total/today"),

  getActiveWorkersWeek: () => api.get("/api/workers/active/week"),

  getRecentPayouts: () => api.get("/api/payouts?limit=3"),

  getActiveZones: () =>
    api.get("/api/v1/dci-alerts/latest?limit=3"),
};