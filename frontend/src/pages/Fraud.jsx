import { useState, useMemo, useEffect } from 'react';
import { X, AlertTriangle, Shield, TrendingDown, MapPin, Eye, MessageSquare, Ban } from 'lucide-react';
import { formatCurrency, getInitials } from '../utils/formatters';

const signalLabels = ['GPS', 'IP', 'Velocity', 'Entropy', 'Cluster', 'Loyalty'];

const mockFraudRows = [
  {
    id: 1,
    workerId: 'W001',
    worker: 'Amit Patel',
    gigScore: 82,
    trigger: '🌧️ Heavy Rainfall · DCI 78',
    reason: 'GPS Spoofing · Signal 1+4 triggered',
    signals: [false, true, false, true, false, false],
    fraudScore: 2,
    riskLevel: 'medium',
    path: 'B',
    pathLabel: '⚠ Soft Flag · 50% held',
    rowTone: 'normal',
  },
  {
    id: 2,
    workerId: 'W002',
    worker: 'Sneha Reddy',
    gigScore: 91,
    trigger: '🌡️ Heat Wave · DCI 82',
    reason: 'Claim Timing Cluster · 6 workers · 45s window',
    signals: [true, false, true, false, true, false],
    fraudScore: 5,
    riskLevel: 'high',
    path: 'C',
    pathLabel: '✗ Hard Block',
    rowTone: 'hard-block',
  },
  {
    id: 3,
    workerId: 'W003',
    worker: 'Rajesh Kumar',
    gigScore: 75,
    trigger: '💨 High Wind · DCI 65',
    reason: 'IP Mismatch · Different networks day-to-day',
    signals: [false, true, false, false, false, false],
    fraudScore: 1,
    riskLevel: 'low',
    path: 'A',
    pathLabel: '✓ Clean',
    rowTone: 'normal',
  },
  {
    id: 4,
    workerId: 'W004',
    worker: 'Priya Singh',
    gigScore: 88,
    trigger: '🌊 Flooding · DCI 90',
    reason: 'Velocity Spike · 3 payouts in 5 mins',
    signals: [false, false, true, true, false, false],
    fraudScore: 3,
    riskLevel: 'medium',
    path: 'B',
    pathLabel: '⚠ Soft Flag · Under Review',
    rowTone: 'normal',
  },
  {
    id: 5,
    workerId: 'W005',
    worker: 'Vikram Desai',
    gigScore: 85,
    trigger: '🌧️ Heavy Rainfall · DCI 78',
    reason: 'Zone Loyalty Mismatch · Never worked Koramangala',
    signals: [false, false, false, true, false, true],
    fraudScore: 2,
    riskLevel: 'low',
    path: 'A',
    pathLabel: '✓ Clean',
    rowTone: 'normal',
  },
];

const heatmapZones = [
  { zone: 'Koramangala', workers: 18, activity: 'high' },
  { zone: 'Whitefield', workers: 14, activity: 'high' },
  { zone: 'HSR Layout', workers: 12, activity: 'high' },
  { zone: 'Marathahalli', workers: 9, activity: 'medium' },
  { zone: 'Indiranagar', workers: 8, activity: 'medium' },
  { zone: 'Electronic City', workers: 7, activity: 'medium' },
  { zone: 'Bangalore North', workers: 6, activity: 'low' },
  { zone: 'Bangalore South', workers: 5, activity: 'low' },
];

export const Fraud = () => {
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [filterPath, setFilterPath] = useState('all');
  const [filterRisk, setFilterRisk] = useState('all');
  const [fraudRows, setFraudRows] = useState([]);
  const [loading, setLoading] = useState(false);

  // Fetch fraud alerts on mount (with fallback to mock data)
  useEffect(() => {
    const fetchFraudAlerts = async () => {
      try {
        setLoading(true);
        // API endpoint: GET /api/fraud or /api/v1/fraud-alerts or similar
        // For now, fallback to mock data since fraudAPI.getAll() maps to non-existent endpoint
        setFraudRows(mockFraudRows);
      } catch (err) {
        console.error('Error fetching fraud alerts:', err);
        setFraudRows(mockFraudRows);
      } finally {
        setLoading(false);
      }
    };

    fetchFraudAlerts();
  }, []);

  const stats = [
    {
      label: 'High Risk Active',
      value: mockFraudRows.filter((r) => r.riskLevel === 'high').length,
      color: 'bg-red-600 dark:bg-red-700',
      icon: AlertTriangle,
    },
    {
      label: 'Resolved This Week',
      value: 8,
      color: 'bg-green-600 dark:bg-green-700',
      icon: TrendingDown,
    },
    {
      label: 'DC Saved (Fraud Blocked)',
      value: '₹34,200',
      color: 'bg-gigkavach-orange dark:bg-orange-600',
      icon: Shield,
    },
  ];

  const filteredRows = useMemo(() => {
    let result = fraudRows;

    if (filterPath !== 'all') {
      result = result.filter((r) => r.path === filterPath);
    }

    if (filterRisk !== 'all') {
      result = result.filter((r) => r.riskLevel === filterRisk);
    }

    return result;
  }, [filterPath, filterRisk, fraudRows]);

  const getRiskBadgeColor = (level) => {
    const colors = {
      high: 'bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100',
      medium: 'bg-amber-100 dark:bg-amber-900 text-amber-900 dark:text-amber-100',
      low: 'bg-green-100 dark:bg-green-900 text-green-900 dark:text-green-100',
    };
    return colors[level];
  };

  const getPathBadgeColor = (path) => {
    const colors = {
      A: 'bg-green-100 dark:bg-green-900 text-green-900 dark:text-green-100',
      B: 'bg-amber-100 dark:bg-amber-900 text-amber-900 dark:text-amber-100',
      C: 'bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100',
    };
    return colors[path];
  };

  const getHeatmapColor = (activity) => {
    const colors = {
      high: 'bg-rose-600 dark:bg-rose-700',
      medium: 'bg-amber-500 dark:bg-amber-600',
      low: 'bg-emerald-600 dark:bg-emerald-700',
    };
    return colors[activity];
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Fraud Operations Center</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">Real-time signal monitoring, risk assessment & case management</p>
      </div>

      {/* Syndicate Detection Banner */}
      {!bannerDismissed && (
        <div className="bg-red-50 dark:bg-red-950 border-l-4 border-l-red-600 rounded-lg p-4 flex items-start justify-between gap-4">
          <div className="flex gap-4 flex-1">
            <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-red-900 dark:text-red-100">⚠️ Potential Fraud Ring Detected</p>
              <p className="text-sm text-red-800 dark:text-red-200 mt-2">
                6 workers claimed within 45s window in Koramangala. Claim clustering (Signal 5) triggered. All held at Path B pending review.
              </p>
              <div className="flex gap-2 mt-3">
                <button className="px-3 py-1 bg-red-600 text-white rounded text-sm font-medium hover:bg-red-700 transition-colors">
                  View Cluster
                </button>
                <button className="px-3 py-1 bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100 rounded text-sm font-medium hover:bg-red-200 dark:hover:bg-red-800 transition-colors">
                  View Timeline
                </button>
              </div>
            </div>
          </div>
          <button
            onClick={() => setBannerDismissed(true)}
            className="p-1 hover:bg-red-200 dark:hover:bg-red-900 rounded transition-colors flex-shrink-0"
          >
            <X className="w-5 h-5 text-red-600" />
          </button>
        </div>
      )}

      {/* KPI Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <div key={idx} className={`${stat.color} text-white rounded-lg p-6 shadow-lg`}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="text-sm opacity-90 font-medium">{stat.label}</p>
                  <p className="text-4xl font-bold mt-2">{stat.value}</p>
                </div>
                <Icon className="w-8 h-8 opacity-40" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Table - 3/4 width */}
        <div className="lg:col-span-3">
          {/* Filters */}
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm mb-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Filter by Path</label>
                <select
                  value={filterPath}
                  onChange={(e) => setFilterPath(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-gigkavach-orange"
                >
                  <option value="all">All Cases</option>
                  <option value="A">Path A - Clean</option>
                  <option value="B">Path B - Soft Flag</option>
                  <option value="C">Path C - Hard Block</option>
                </select>
              </div>
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Filter by Risk</label>
                <select
                  value={filterRisk}
                  onChange={(e) => setFilterRisk(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-gigkavach-orange"
                >
                  <option value="all">All Risk Levels</option>
                  <option value="low">Low Risk</option>
                  <option value="medium">Medium Risk</option>
                  <option value="high">High Risk</option>
                </select>
              </div>
            </div>
          </div>

          {/* Fraud Signal Monitor Table */}
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Worker</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Event</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Fraud Reason</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Signals</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Score</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Risk</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Path</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((row) => (
                    <tr
                      key={row.id}
                      className={`border-b dark:border-gray-700 transition-colors ${
                        row.rowTone === 'hard-block'
                          ? 'bg-red-50/60 dark:bg-red-950/20 hover:bg-red-100/60 dark:hover:bg-red-950/30'
                          : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                      }`}
                    >
                      {/* Worker */}
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gigkavach-orange to-orange-600 flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
                            {getInitials(row.worker.split(' ')[0], row.worker.split(' ')[1])}
                          </div>
                          <div>
                            <p className="font-medium text-gray-900 dark:text-white text-sm">{row.worker}</p>
                            <span className="text-xs bg-orange-100 dark:bg-orange-900 text-orange-900 dark:text-orange-100 px-2 py-0.5 rounded leading-relaxed">
                              Score {row.gigScore}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Trigger Event */}
                      <td className="px-4 py-4 text-xs text-gray-600 dark:text-gray-400 whitespace-nowrap">{row.trigger}</td>

                      {/* Fraud Reason */}
                      <td className="px-4 py-4 text-xs text-gray-600 dark:text-gray-400 max-w-xs">{row.reason}</td>

                      {/* Signals */}
                      <td className="px-4 py-4">
                        <div className="flex gap-1 flex-wrap">
                          {row.signals.map((signal, idx) => (
                            <div
                              key={idx}
                              title={signalLabels[idx]}
                              className={`w-5 h-5 rounded-sm border flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                                signal
                                  ? 'bg-red-100 dark:bg-red-900 border-red-400 dark:border-red-600 text-red-700 dark:text-red-100'
                                  : 'bg-green-100 dark:bg-green-900 border-green-400 dark:border-green-600 text-green-700 dark:text-green-100'
                              }`}
                            >
                              {idx + 1}
                            </div>
                          ))}
                        </div>
                      </td>

                      {/* Fraud Score */}
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-gray-900 dark:text-white whitespace-nowrap">{row.fraudScore}/6</span>
                          <div className="w-10 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden flex-shrink-0">
                            <div
                              className={`h-full ${
                                row.fraudScore >= 5
                                  ? 'bg-red-600 dark:bg-red-500'
                                  : row.fraudScore >= 3
                                    ? 'bg-amber-600 dark:bg-amber-500'
                                    : 'bg-green-600 dark:bg-green-500'
                              }`}
                              style={{ width: `${(row.fraudScore / 6) * 100}%` }}
                            />
                          </div>
                        </div>
                      </td>

                      {/* Risk Level */}
                      <td className="px-4 py-4">
                        <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${getRiskBadgeColor(row.riskLevel)}`}>
                          {row.riskLevel === 'high' ? '🔴 High' : row.riskLevel === 'medium' ? '🟡 Medium' : '🟢 Low'}
                        </span>
                      </td>

                      {/* Path */}
                      <td className="px-4 py-4">
                        <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${getPathBadgeColor(row.path)}`}>
                          {row.pathLabel}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-4">
                        <div className="flex gap-1">
                          <button className="p-1.5 hover:bg-blue-100 dark:hover:bg-blue-900 rounded transition-colors text-blue-600 dark:text-blue-400" title="Review case">
                            <Eye className="w-4 h-4" />
                          </button>
                          <button className="p-1.5 hover:bg-amber-100 dark:hover:bg-amber-900 rounded transition-colors text-amber-600 dark:text-amber-400" title="Appeal">
                            <MessageSquare className="w-4 h-4" />
                          </button>
                          <button className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900 rounded transition-colors text-red-600 dark:text-red-400" title="Blacklist">
                            <Ban className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Empty State */}
            {filteredRows.length === 0 && (
              <div className="p-12 text-center">
                <AlertTriangle className="w-12 h-12 text-gray-400 dark:text-gray-600 mx-auto mb-3 opacity-50" />
                <p className="text-gray-600 dark:text-gray-400 font-medium">No fraud cases match filters</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Sidebar - 1/4 width */}
        <div className="space-y-6">
          {/* Zone Fraud Density Heatmap */}
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4 text-sm flex items-center gap-2">
              <MapPin className="w-4 h-4 text-gigkavach-orange" />
              Zone Fraud Density
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">Last 7 Days</p>
            <div className="grid grid-cols-2 gap-2">
              {heatmapZones.map((z) => (
                <div
                  key={z.zone}
                  className={`${getHeatmapColor(z.activity)} text-white p-3 rounded-lg text-xs font-semibold text-center cursor-pointer hover:opacity-90 transition-opacity`}
                >
                  <p className="truncate text-xs leading-tight">{z.zone}</p>
                  <p className="text-xs opacity-90 mt-1">{z.workers} workers</p>
                </div>
              ))}
            </div>
          </div>

          {/* Operations Guide */}
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4 text-sm">Path Guide</h3>
            <div className="space-y-3 text-xs">
              <div className="pb-3 border-b dark:border-gray-700">
                <p className="font-medium text-green-700 dark:text-green-400 mb-1">✓ Path A: Clean</p>
                <p className="text-gray-600 dark:text-gray-400">Consensus passed · Payout released immediately</p>
              </div>
              <div className="pb-3 border-b dark:border-gray-700">
                <p className="font-medium text-amber-700 dark:text-amber-400 mb-1">⚠ Path B: Soft Flag</p>
                <p className="text-gray-600 dark:text-gray-400">50% held in escrow · Awaiting manual review</p>
              </div>
              <div>
                <p className="font-medium text-red-700 dark:text-red-400 mb-1">✗ Path C: Hard Block</p>
                <p className="text-gray-600 dark:text-gray-400">Payout withheld · Escalate to blacklist</p>
              </div>
            </div>
          </div>

          {/* Signal Legend */}
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-3 text-sm">Fraud Signals</h3>
            <div className="grid grid-cols-3 gap-2">
              {signalLabels.map((label, idx) => (
                <div key={idx} className="text-center">
                  <div className="w-6 h-6 rounded-sm bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-600 flex items-center justify-center text-xs font-bold text-red-700 dark:text-red-100 mx-auto mb-1">
                    {idx + 1}
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400">{label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
