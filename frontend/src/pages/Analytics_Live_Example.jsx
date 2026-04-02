// frontend/src/pages/Analytics_Live.jsx
// Updated version with live API wiring
// This file demonstrates how P1.6 would wire live data

import { useState, useEffect } from 'react';
import { dashboardAPI } from '../api/dashboard';

export function AnalyticsPageLiveVersion() {
  const [weeklyData, setWeeklyData] = useState([]);
  const [stats, setStats] = useState({
    totalPremiums: 0,
    totalPayouts: 0,
    avgLossRatio: 0,
  });

  // Fetch analytics data on mount
  useEffect(() => {
    async function fetchAnalyticsData() {
      try {
        // Get aggregated payout statistics
        const statsResponse = await dashboardAPI.getPayoutStats();
        if (statsResponse?.data) {
          setStats({
            totalPremiums: statsResponse.data.total_premiums || 0,
            totalPayouts: statsResponse.data.total_payouts || 0,
            avgLossRatio: (statsResponse.data.total_payouts / 
              statsResponse.data.total_premiums * 100) || 0,
          });
        }

        // Get weekly trend data
        const trendsResponse = await dashboardAPI.getWeeklyTrends();
        if (trendsResponse?.data) {
          setWeeklyData(trendsResponse.data.weeks || []);
        }
      } catch (error) {
        console.error('Failed to fetch analytics:', error);
        // Fallback to mock data
        setWeeklyData(mockWeeklyData);
      }
    }

    fetchAnalyticsData();
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold">Analytics</h1>
      <div className="mt-6 grid grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded shadow">
          <p className="text-gray-600">Total Premiums</p>
          <p className="text-2xl font-bold">₹{stats.totalPremiums.toLocaleString()}</p>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <p className="text-gray-600">Total Payouts</p>
          <p className="text-2xl font-bold">₹{stats.totalPayouts.toLocaleString()}</p>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <p className="text-gray-600">Loss Ratio</p>
          <p className="text-2xl font-bold">{stats.avgLossRatio.toFixed(1)}%</p>
        </div>
      </div>
    </div>
  );
}

const mockWeeklyData = [
  { week: 'Wk 1', premiums: 78000, payouts: 64000, lossRatio: 82 },
  { week: 'Wk 2', premiums: 82000, payouts: 66000, lossRatio: 80.5 },
];
