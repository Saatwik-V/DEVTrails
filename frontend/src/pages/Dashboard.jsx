import { useState, useEffect } from 'react';import { Users, Zap, IndianRupee, ShieldAlert, TrendingUp, TrendingDown, Clock, CheckCircle2, Clock3, AlertCircle, IndianRupeeIcon } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, BarChart, Bar, Cell } from 'recharts';
import { dashboardAPI } from "../api/dashboardAPI";

// DCI Live Monitor Data - last 12 time points (5-minute intervals)
const dciLiveData = [
  { time: '2:00', dci: 48, zone: 'HSR Layout', rainfall: 'LOW' },
  { time: '2:05', dci: 52, zone: 'Indiranagar', rainfall: 'LOW' },
  { time: '2:10', dci: 58, zone: 'Koramangala', rainfall: 'MODERATE' },
  { time: '2:15', dci: 65, zone: 'Koramangala', rainfall: 'HIGH' },
  { time: '2:20', dci: 72, zone: 'Koramangala', rainfall: 'HIGH' },
  { time: '2:25', dci: 68, zone: 'Marathahalli', rainfall: 'MODERATE' },
  { time: '2:30', dci: 75, zone: 'Whitefield', rainfall: 'MODERATE' },
  { time: '2:35', dci: 82, zone: 'Koramangala', rainfall: 'HIGH' },
  { time: '2:40', dci: 78, zone: 'Koramangala', rainfall: 'HIGH' },
  { time: '2:45', dci: 71, zone: 'Electronic City', rainfall: 'LOW' },
  { time: '2:50', dci: 64, zone: 'HSR Layout', rainfall: 'LOW' },
  { time: '2:55', dci: 58, zone: 'Indiranagar', rainfall: 'LOW' },
];


// Recent Activity Feed
/*const activityFeed = [
  {
    id: 1,
    type: 'trigger',
    description: 'DCI triggered in Koramangala · 48 workers notified',
    timestamp: '2 min ago',
    icon: Zap,
  },
  {
    id: 2,
    type: 'payout',
    description: 'Payout of ₹420 sent to Rajesh Kumar',
    timestamp: '5 min ago',
    icon: IndianRupee,
  },
  {
    id: 3,
    type: 'fraud',
    description: 'Fraud alert flagged · GPS vs IP mismatch in HSR Layout',
    timestamp: '8 min ago',
    icon: ShieldAlert,
  },
  {
    id: 4,
    type: 'trigger',
    description: 'Whitefield zone entered MODERATE disruption',
    timestamp: '18 min ago',
    icon: Zap,
  },
];
*/
export const Dashboard = () => {
  // Recent Payouts
const defaultSpark = [40, 60, 30, 90, 70, 110, 80];
const [recentPayouts, setRecentPayouts] = useState([]);
useEffect(() => {
  const fetchPayouts = async () => {
    try {
      const res = await dashboardAPI.getRecentPayouts();

      const formatted = res.data.payouts.map((p) => ({
        id: p.id,
        initials: p.worker_name
          ?.split(" ")
          .map((n) => n[0])
          .join("")
          .slice(0, 2)
          .toUpperCase(),
        name: p.worker_name,
        tier: "Shield Pro",
        amount: p.amount,
        status: p.status === "payout_sent" ? "sent" : "processing",
        timestamp: timeAgo(p.timestamp),
      }));

      setRecentPayouts(formatted);
    } catch (err) {
      console.error(err);
    }
  };

  fetchPayouts();
}, []);
const [activeZones, setActiveZones] = useState([]);
const [loading, setLoading] = useState(true);

useEffect(() => {
  const fetchZones = async () => {
    try {
      setLoading(true);

      const res = await dashboardAPI.getActiveZones();
      setActiveZones(res.data.alerts || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  fetchZones();
}, []);


const timeAgo = (timestamp) => {
  const now = new Date();
  const past = new Date(timestamp);
  const diff = Math.floor((now - past) / 1000);

  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`;
  return `${Math.floor(diff / 86400)} day ago`;
};
const [metrics, setMetrics] = useState({
  activeWorkers: 1248,
  dciTriggers: 34,
  payouts: 245680,
  fraudAlerts: 12,
});
const sparkline = {
  activeWorkers: [42, 48, 45, 52, 58, 55, 62],
  dciTriggers: [8, 12, 10, 18, 22, 19, 34], 
  payouts: [145000, 168000, 152000, 198000, 220000, 198000, 245680],
  fraudAlerts: [4, 6, 5, 8, 10, 11, 12],
};

const [todayPayout, setTodayPayout] = useState(0);
const [loadingPayout, setLoadingPayout] = useState(true);
const [todayDCI, setTodayDCI] = useState(0);
const [activeWorkers, setActiveWorkers] = useState(0);
useEffect(() => {
  const fetchDCI = async () => {
    try {
      const res = await dashboardAPI.getTodayDCI();
      setTodayDCI(res.data.total_dci_today ?? 0);
    } catch (err) {
      console.error(err);
      setTodayDCI(0);
    }
  };

  fetchDCI();
}, []);
useEffect(() => {
  const fetchWorkers = async () => {
    try {
      const res = await dashboardAPI.getActiveWorkersWeek();
      setActiveWorkers(res.data.active_workers_week ?? 0);
    } catch (err) {
      console.error(err);
      setActiveWorkers(0);
    }
  };

  fetchWorkers();
}, []);

const statCards = [
  {
    key: "workers",
    label: "Active Workers This Week",
    icon: Users,
    color: "blue",
    subtitle: "Enrolled in Shield Basic/Plus/Pro",
  },
  {
    key: "dci",
    label: "DCI Triggers Today",
    icon: Zap,
    color: "orange",
    subtitle: "Disruption events detected",
  },
{
  key: "payout",
  label: "Today's Payout",
  value: todayPayout,
  icon: IndianRupeeIcon,
  color: "green",
  subtitle: "Total payouts processed today"
},
  {
    key: "fraudAlerts",
    label: "Fraud Alerts Active",
    icon: ShieldAlert,
    color: "red",
    subtitle: "Pending review · 2 High Risk",
  },
];

useEffect(() => {
  const fetchPayout = async () => {
    try {
      const res = await dashboardAPI.getTodayPayout();
      setTodayPayout(res.data.total_payout_today ?? 0);
    } catch (err) {
      console.error(err);
      setTodayPayout(0);
    }
  };

  fetchPayout();
}, []);
  const getCardBgColor = (color) => {
    const colors = {
      blue: 'bg-blue-50 dark:bg-blue-950',
      orange: 'bg-orange-50 dark:bg-orange-950',
      green: 'bg-green-50 dark:bg-green-950',
      red: 'bg-red-50 dark:bg-red-950',
    };
    return colors[color];
  };

  const getIconColor = (color) => {
    const colors = {
      blue: 'text-blue-600 dark:text-blue-400',
      orange: 'text-orange-600 dark:text-orange-400',
      green: 'text-green-600 dark:text-green-400',
      red: 'text-red-600 dark:text-red-400',
    };
    return colors[color];
  };

  const getChangeColor = (change) => {
    const isPositive = change >= 0;
    return isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  };

  const getDCIColor = (dci) => {
    if (dci >= 85) return 'bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100';
    if (dci >= 65) return 'bg-orange-100 dark:bg-orange-900 text-orange-900 dark:text-orange-100';
    if (dci >= 45) return 'bg-amber-100 dark:bg-amber-900 text-amber-900 dark:text-amber-100';
    return 'bg-green-100 dark:bg-green-900 text-green-900 dark:text-green-100';
  };

  const getDCIZoneColor = (dci) => {
    if (dci >= 85) return 'border-l-4 border-l-red-600';
    if (dci >= 65) return 'border-l-4 border-l-orange-500';
    if (dci >= 45) return 'border-l-4 border-l-amber-500';
    return 'border-l-4 border-l-green-600';
  };

  const getActivityColor = (type) => {
    const colors = {
      trigger: 'border-l-orange-500 bg-orange-50/30 dark:bg-orange-950/30',
      payout: 'border-l-green-500 bg-green-50/30 dark:bg-green-950/30',
      fraud: 'border-l-red-500 bg-red-50/30 dark:bg-red-950/30',
    };
    return colors[type];
  };

  const getActivityIconColor = (type) => {
    const colors = {
      trigger: '#FF6B35',
      payout: '#22C55E',
      fraud: '#EF4444',
    };
    return colors[type];
  };

return (
  <div className="space-y-6">

    {/* STAT CARDS */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {statCards.map((card, idx) => {
        const Icon = card.icon;

      const data = sparkline[card.key] || defaultSpark;
const liveMetrics = {
  payout: todayPayout,
  dci: todayDCI,
  workers: activeWorkers,
};

const value = liveMetrics[card.key] ?? metrics[card.key] ?? 0;

        const isPositive =
          data.length > 1
            ? data[data.length - 1] >= data[0]
            : true;

 return (
  <div key={idx} className={`${getCardBgColor(card.color)} rounded-lg p-5 border border-gray-200 dark:border-gray-700 shadow-sm`}>
    {/* Header */}
    <div className="flex items-start justify-between mb-4">
      <Icon className={`w-6 h-6 ${getIconColor(card.color)}`} />
      <span className={`text-xs font-bold flex items-center gap-1 ${isPositive ? "text-green-500" : "text-red-500"}`}>
        {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
      </span>
    </div>

    {/* Value */}
    <p className="text-3xl font-black text-gray-900 dark:text-white mb-1 font-mono">
      {typeof value === "number" && value > 1000 ? value.toLocaleString() : value}
    </p>

    {/* Label */}
    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-3">{card.label}</p>

    {/* Sparkline */}
    <div className="h-10 mb-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data.map(v => ({ value: v }))}>
          <Bar dataKey="value" radius={[2, 2, 0, 0]}>
            {data.map((_, i) => (
              <Cell
                key={i}
                fill={
                  card.color === "blue" ? "#3B82F6"
                  : card.color === "orange" ? "#FF6B35"
                  : card.color === "green" ? "#22C55E"
                  : "#EF4444"
                }
                opacity={i === data.length - 1 ? 1 : 0.5}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>

    {/* Subtitle */}
    <p className="text-xs text-gray-600 dark:text-gray-400">{card.subtitle}</p>
  </div>
);
      })}
    </div>

    {/* ===== MAIN CONTENT: DCI Monitor (60%) + Right Sidebar (40%) ===== */}
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

    {/* DCI LIVE MONITOR — left 2 cols */}
<div className="lg:col-span-2 bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm flex flex-col justify-center">
  
  {/* Live Badge */}
  <div className="flex items-center gap-3 mb-6">
    <div className="flex items-center gap-2 bg-red-50 dark:bg-red-950 px-3 py-2 rounded-full border border-red-200 dark:border-red-800">
      <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse" />
      <span className="text-xs font-bold text-red-600 dark:text-red-400 uppercase">Live</span>
    </div>
    <span className="text-sm font-semibold text-gray-900 dark:text-white">
      3 Zones Above Trigger Threshold
    </span>
  </div>

  {/* Area Chart — grows to fill available space */}
  <div className="flex-1 min-h-64">
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={dciLiveData}>
        <defs>
          <linearGradient id="colorDci" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#FF6B35" stopOpacity={0.8} />
            <stop offset="95%" stopColor="#FF6B35" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="time" stroke="#9CA3AF" tick={{ fontSize: 12 }} />
        <YAxis
          domain={[0, 100]}
          stroke="#9CA3AF"
          label={{ value: 'DCI Score', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip
          contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px', color: '#fff' }}
          formatter={(value, name) => name === 'dci' ? [`${value}`, 'DCI Score'] : [value, name]}
          labelFormatter={(label) => `Time: ${label}`}
        />
        <ReferenceLine
          y={65}
          stroke="#FF6B35"
          strokeDasharray="5 5"
          label={{ value: 'Trigger Threshold (65)', position: 'insideRight', offset: -10, fill: '#FF6B35', fontSize: 11 }}
        />
        <ReferenceLine
          y={85}
          stroke="#EF4444"
          strokeDasharray="5 5"
          label={{ value: 'Catastrophic (85)', position: 'insideRight', offset: -25, fill: '#EF4444', fontSize: 11 }}
        />
        <Area type="monotone" dataKey="dci" stroke="#FF6B35" fillOpacity={1} fill="url(#colorDci)" />
      </AreaChart>
    </ResponsiveContainer>
  </div>

</div>
      {/* RIGHT SIDEBAR — 1 col, both cards stacked */}
      <div className="flex flex-col gap-6">

        {/* ACTIVE ZONE ALERTS */}
        <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Active Zone Alerts
          </h3>
          <div className="space-y-3">
            {activeZones.map((zone) => {
              const severity = zone.status;
              return (
                <div
                  key={zone.id}
                  className={`p-3 rounded-lg ${
                    severity === "catastrophic"
                      ? "bg-red-50 border border-red-200 dark:bg-red-950/20"
                      : severity === "severe"
                      ? "bg-orange-50 border border-orange-200 dark:bg-orange-950/20"
                      : "bg-yellow-50 border border-yellow-200 dark:bg-yellow-950/20"
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <p className="font-semibold text-gray-900 dark:text-white text-sm">
                      {zone.neighborhood}
                    </p>
                    <span
                      className={`text-sm font-bold px-2 py-1 rounded text-white ${
                        severity === "catastrophic" ? "bg-red-600"
                        : severity === "severe" ? "bg-orange-500"
                        : "bg-yellow-500"
                      }`}
                    >
                      {zone.dci}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">{zone.trigger}</p>
                  <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${
                        severity === "catastrophic" ? "bg-red-600"
                        : severity === "severe" ? "bg-orange-500"
                        : "bg-yellow-400"
                      }`}
                      style={{ width: `${Math.min((zone.dci / 100) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        {/* ↑ END ACTIVE ZONE ALERTS */}

        {/* PAYOUT PIPELINE */}
        <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Payout Pipeline
          </h3>
          <div className="space-y-3">
            {recentPayouts.map((payout) => (
              <div
                key={payout.id}
                className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div className="w-8 h-8 rounded-full bg-gigkavach-orange flex items-center justify-center text-white font-bold text-xs">
                  {payout.initials}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {payout.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{payout.tier}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-green-600 dark:text-green-400">
                    ₹{payout.amount}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center justify-end gap-1">
                    {payout.status === "sent" ? (
                      <>
                        <CheckCircle2 className="w-3 h-3 text-green-600" />
                        Sent
                      </>
                    ) : (
                      <>
                        <Clock3 className="w-3 h-3 text-amber-600" />
                        Paid
                      </>
                    )}
                  </p>
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 text-center">
            Timestamp varies
          </p>
        </div>
        {/* ↑ END PAYOUT PIPELINE */}

      </div>
      {/* ↑ END RIGHT SIDEBAR */}

    </div>
    {/* ↑ END MAIN GRID */}
  </div>
);
}