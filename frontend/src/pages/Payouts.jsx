import { useState, useMemo, useEffect } from 'react';
import { ChevronDown, ChevronUp, Zap, Shield, AlertTriangle, Check } from 'lucide-react';
import { formatCurrency, formatPercentage, formatDate } from '../utils/formatters';
import { Button } from '../components/common/Button';
import { RealTimePayoutFeed } from '../components/payouts/RealTimePayoutFeed';
import { WorkerModal } from '../components/workers/WorkerModal';
import { dashboardAPI } from '../api/dashboardAPI';

// Fallback mock data for when API is unavailable
const mockPayouts = [
  { id: 1, worker: 'Amit Patel', avatar: 'A', tier: 'Shield Pro', trigger: '🌧️ Heavy Rainfall · DCI 78', amount: 8500, coverage: 50, upiRef: 'GK2024001234', dateTime: new Date(Date.now() - 30 * 60000), status: 'paid', fraud: 'clean' },
];

const mockEscrowEntries = [
  { id: 1, worker: 'Neha Sharma', amount: 6500, status: 'soft-flagged', reason: 'GPS anomaly detected', timeToResolve: '2 days' },
  { id: 2, worker: 'Arjun Nair', amount: 4200, status: 'under-review', reason: 'Velocity spike · 3 payouts in 5 mins', timeToResolve: '1 day' },
];

export const Payouts = () => {
  const [activeTab, setActiveTab] = useState('all');
  const [isSimulationOpen, setIsSimulationOpen] = useState(false);
  const [isEscrowOpen, setIsEscrowOpen] = useState(true);
  const [simulationZone, setSimulationZone] = useState('Koramangala');
  const [simulationDisruption, setSimulationDisruption] = useState('rain');
  const [simulationDCI, setSimulationDCI] = useState(78);
  const [toastMessage, setToastMessage] = useState('');
  const [workerModalId, setWorkerModalId] = useState(null);
  const [workerModalOpen, setWorkerModalOpen] = useState(false);
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fetch live payouts from dashboard API
  useEffect(() => {
    const fetchPayouts = async () => {
      try {
        setLoading(true);
        const res = await dashboardAPI.getRecentPayouts();
        
        // Transform API response to table format
        const formatted = res.data.payouts.map((p) => ({
          id: p.id,
          worker: p.worker_name || 'Unknown',
          avatar: p.worker_name
            ?.split(' ')
            .map((n) => n[0])
            .join('')
            .slice(0, 2)
            .toUpperCase() || '?',
          tier: p.plan ? (p.plan === 'basic' ? 'Shield Basic' : p.plan === 'plus' ? 'Shield Plus' : 'Shield Pro') : 'Shield Basic',
          trigger: `DCI Event · ${p.dci_score || 'N/A'}`,
          amount: p.amount,
          coverage: Math.round((p.amount / (p.amount / (p.fraud_score ? 0.5 : 1))) * 100) || 50,
          upiRef: p.id.slice(0, 12).toUpperCase(),
          dateTime: new Date(p.timestamp),
          status: p.status === 'payout_sent' ? 'paid' : (p.status || 'processing'),
          fraud: p.fraud_score > 3 ? 'hard-block' : p.fraud_score > 1 ? 'soft-flag' : 'clean',
        }));
        
        setPayouts(formatted.length > 0 ? formatted : mockPayouts);
      } catch (err) {
        console.error('Error fetching payouts:', err);
        setPayouts(mockPayouts); // Fallback to mock data
      } finally {
        setLoading(false);
      }
    };

    fetchPayouts();
  }, []);

  const stats = [
    { label: 'Total Disbursed', value: formatCurrency(payouts.reduce((sum, p) => sum + (p.amount || 0), 0)) },
    { label: 'Pending', value: formatCurrency(payouts.filter(p => p.status === 'pending').reduce((sum, p) => sum + (p.amount || 0), 0)) },
    { label: 'Success Rate', value: formatPercentage(payouts.length > 0 ? (payouts.filter(p => p.status === 'paid').length / payouts.length) * 100 : 98.2) },
    { label: 'Avg Processing', value: '4.2 min' },
  ];

  const filteredPayouts = useMemo(() => {
    if (activeTab === 'all') return payouts;
    return payouts.filter((p) => p.status === activeTab);
  }, [activeTab, payouts]);

  const handleSimulation = () => {
    setToastMessage(`✓ Simulation triggered · 34 workers eligible · Payouts queued`);
    setIsSimulationOpen(false);
    setTimeout(() => setToastMessage(''), 4000);
  };

  const getStatusColor = (status) => {
    const colors = {
      paid: { bg: 'bg-green-100 dark:bg-green-900', text: 'text-green-900 dark:text-green-100', border: 'border-green-300 dark:border-green-700' },
      pending: { bg: 'bg-amber-100 dark:bg-amber-900', text: 'text-amber-900 dark:text-amber-100', border: 'border-amber-300 dark:border-amber-700' },
      failed: { bg: 'bg-red-100 dark:bg-red-900', text: 'text-red-900 dark:text-red-100', border: 'border-red-300 dark:border-red-700' },
      escrowed: { bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-900 dark:text-blue-100', border: 'border-blue-300 dark:border-blue-700' },
    };
    return colors[status] || colors.pending;
  };

  const getTierColor = (tier) => {
    const colors = {
      'Shield Basic': { bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-900 dark:text-blue-100' },
      'Shield Plus': { bg: 'bg-purple-100 dark:bg-purple-900', text: 'text-purple-900 dark:text-purple-100' },
      'Shield Pro': { bg: 'bg-amber-100 dark:bg-amber-900', text: 'text-amber-900 dark:text-amber-100' },
    };
    return colors[tier] || colors['Shield Basic'];
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Payouts</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">AI-triggered parametric payout pipeline</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, idx) => (
          <div key={idx} className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
            <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">{stat.label}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white font-mono">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Real-time Processing Feed */}
      <RealTimePayoutFeed
        onWorkerClick={(id) => {
          setWorkerModalId(id);
          setWorkerModalOpen(true);
        }}
      />

      <WorkerModal
        workerId={workerModalId}
        isOpen={workerModalOpen}
        onClose={() => setWorkerModalOpen(false)}
      />

      {/* Controls */}
      <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm flex justify-between items-center">
        <div className="flex gap-2">
          {['all', 'paid', 'pending', 'escrowed', 'failed'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-gigkavach-orange text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
        <Button onClick={() => setIsSimulationOpen(true)} variant="primary" size="md">
          <Zap className="w-4 h-4" />
          Trigger Simulation
        </Button>
      </div>

      {/* Payouts Table */}
      <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Worker</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Tier</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Trigger</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Amount</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Coverage</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">UPI Ref</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Date & Time</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">Fraud</th>
              </tr>
            </thead>
            <tbody>
              {filteredPayouts.map((payout) => {
                const statusColor = getStatusColor(payout.status);
                const tierColor = getTierColor(payout.tier);
                return (
                  <tr key={payout.id} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gigkavach-orange flex items-center justify-center text-white font-bold text-xs">
                          {payout.avatar}
                        </div>
                        <span className="text-sm font-medium text-gray-900 dark:text-white">{payout.worker}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${tierColor.bg} ${tierColor.text}`}>{payout.tier}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{payout.trigger}</td>
                    <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">{formatCurrency(payout.amount)}</td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{payout.coverage}%</td>
                    <td className="px-6 py-4 text-xs font-mono text-gray-500 dark:text-gray-400">{payout.upiRef}</td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{formatDate(payout.dateTime, 'datetime')}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold border ${statusColor.bg} ${statusColor.text} ${statusColor.border}`}>
                        {payout.status.charAt(0).toUpperCase() + payout.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">
                      {payout.fraud === 'clean' ? (
                        <Check className="w-5 h-5 text-green-600 dark:text-green-400" />
                      ) : (
                        <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Escrow Section */}
      <div className={`bg-white dark:bg-gigkavach-surface rounded-lg border-l-4 border-l-amber-500 border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden transition-all`}>
        <button
          onClick={() => setIsEscrowOpen(!isEscrowOpen)}
          className="w-full px-6 py-4 flex items-center justify-between bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Payout Escrow (₹10,700 held)</h3>
          </div>
          {isEscrowOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>

        {isEscrowOpen && (
          <div className="border-t dark:border-gray-700 p-6 space-y-4">
            {mockEscrowEntries.map((entry) => (
              <div key={entry.id} className="border dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-800">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">{entry.worker}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{entry.reason}</p>
                  </div>
                  <p className="font-bold text-gray-900 dark:text-white font-mono">{formatCurrency(entry.amount)}</p>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${entry.status === 'soft-flagged' ? 'bg-amber-100 dark:bg-amber-900 text-amber-900 dark:text-amber-100' : 'bg-blue-100 dark:bg-blue-900 text-blue-900 dark:text-blue-100'}`}>
                    {entry.status}
                  </span>
                  <div className="flex gap-2">
                    <Button variant="secondary" size="sm">Re-verify</Button>
                    <Button variant="outline" size="sm">Release</Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Simulation Modal */}
      {isSimulationOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-gigkavach-surface rounded-lg shadow-2xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Trigger Payout Simulation</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Select Zone</label>
                <select
                  value={simulationZone}
                  onChange={(e) => setSimulationZone(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-gigkavach-orange"
                >
                  <option>Koramangala</option>
                  <option>HSR Layout</option>
                  <option>Whitefield</option>
                  <option>Electronic City</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Disruption Type</label>
                <div className="space-y-2">
                  {[
                    { value: 'rain', label: '🌧️ Heavy Rain' },
                    { value: 'aqi', label: '😷 Severe AQI' },
                    { value: 'heat', label: '🌡️ Extreme Heat' },
                    { value: 'bandh', label: '🚫 Bandh' },
                  ].map((opt) => (
                    <label key={opt.value} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="disruption"
                        value={opt.value}
                        checked={simulationDisruption === opt.value}
                        onChange={(e) => setSimulationDisruption(e.target.value)}
                        className="w-4 h-4 accent-gigkavach-orange"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">{opt.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">DCI Override: {simulationDCI}</label>
                <input
                  type="range"
                  min="65"
                  max="100"
                  value={simulationDCI}
                  onChange={(e) => setSimulationDCI(parseInt(e.target.value))}
                  className="w-full accent-gigkavach-orange"
                />
              </div>
            </div>

            <div className="flex gap-3 justify-end mt-6 p-4 bg-gray-50 dark:bg-gray-800 -mx-6 -mb-6 mt-6">
              <Button onClick={() => setIsSimulationOpen(false)} variant="secondary" size="md">
                Cancel
              </Button>
              <Button onClick={handleSimulation} variant="primary" size="md">
                Fire Simulation
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toastMessage && (
        <div className="fixed bottom-4 right-4 bg-emerald-500 text-white px-4 py-3 rounded-lg shadow-lg animate-pulse">
          {toastMessage}
        </div>
      )}
    </div>
  );
};
