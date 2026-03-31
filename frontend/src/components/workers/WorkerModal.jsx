import { useEffect, useRef, useState } from 'react';
import { X, Phone, MapPin, Clock, Zap, DollarSign, Activity } from 'lucide-react';
import { formatPhoneNumber, formatCurrency, getInitials } from '../../utils/formatters';
import { workerAPI } from '../../api/workers';

export function WorkerModal({ workerId, isOpen, onClose }) {
  const [workerData, setWorkerData] = useState(null);
  const [loading, setLoading] = useState(false);
  const modalRef = useRef(null);

  useEffect(() => {
    if (!workerId || !isOpen) {
      setWorkerData(null);
      return;
    }

    setLoading(true);
    setWorkerData(null);
    const fetchWorker = async () => {
      try {
        const data = await workerAPI.getById(workerId);

        const formatPlan = (plan) => {
          if (!plan) return 'N/A';
          if (plan.toLowerCase().includes('basic')) return 'Shield Basic';
          if (plan.toLowerCase().includes('plus')) return 'Shield Plus';
          if (plan.toLowerCase().includes('pro')) return 'Shield Pro';
          return plan;
        };

        const policyStatus = data.policy?.status || 'inactive';

        const mappedWorker = {
          id: data.worker.id,
          name: data.worker.name,
          phone: data.worker.phone,
          upi: data.worker.upi_id || 'N/A',
          zone: data.worker.pin_codes?.join(', ') || 'N/A',
          shift: data.worker.shift,
          shift_start: data.worker.shift_start,
          shift_end: data.worker.shift_end,
          language: data.worker.language,
          plan: formatPlan(data.policy?.plan || data.worker.plan),
          premium: data.policy?.weekly_premium || 0,
          coverage: data.policy?.coverage_pct || data.worker.coverage_pct || 0,
          status: policyStatus,
          payoutHistory: data.payouts || [],
          activityLog: data.activities || [],
        };

        setWorkerData(mappedWorker);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchWorker();
  }, [workerId, isOpen]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (modalRef.current && !modalRef.current.contains(e.target)) {
        onClose();
      }
    };
    if (isOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const maskedUPI = workerData?.upi
    ? workerData.upi.substring(0, 5) + '****' + workerData.upi.substring(workerData.upi.length - 4)
    : 'N/A';

  const getPlanColor = (plan) => {
    if (!plan) return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    if (plan.toLowerCase().includes('pro')) return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200';
    if (plan.toLowerCase().includes('plus')) return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
    return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
  };

  const getStatusColor = (s) => {
    if (s === 'active') return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    if (s === 'inactive') return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    if (s === 'expired') return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex justify-center items-start z-50 p-4 overflow-y-auto pt-8">
      <div
        ref={modalRef}
        className="bg-white dark:bg-gigkavach-navy rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-4 duration-300"
      >
        <div className="bg-gradient-to-r from-gigkavach-orange to-orange-600 p-6 text-white">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center text-2xl font-bold">
                {getInitials(workerData?.name?.split(' ')[0] || '', workerData?.name?.split(' ')[1] || '')}
              </div>
              <div>
                <h2 className="text-2xl font-bold">{workerData?.name || 'Loading...'}</h2>
                <div className="flex gap-2 mt-2 flex-wrap">
                  <span className={`text-xs px-3 py-1 rounded-full font-semibold ${getPlanColor(workerData?.plan)}`}>
                    {workerData?.plan || 'N/A'}
                  </span>
                  <span className={`text-xs px-3 py-1 rounded-full font-semibold ${getStatusColor(workerData?.status)}`}>
                    {workerData?.status ? workerData.status.charAt(0).toUpperCase() + workerData.status.slice(1) : 'Inactive'}
                  </span>
                </div>
              </div>
            </div>
            <button type="button" onClick={onClose} className="p-2 rounded-lg hover:bg-white/20 transition-colors">
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-pulse flex justify-center mb-4">
              <div className="w-8 h-8 border-4 border-gigkavach-orange border-t-transparent rounded-full animate-spin" />
            </div>
            <p className="text-gray-500 dark:text-gray-400">Loading worker details...</p>
          </div>
        ) : (
          <div className="p-6 space-y-6 max-h-[calc(100vh-300px)] overflow-y-auto">
            <section>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Phone className="w-4 h-4 text-gigkavach-orange" />
                Contact Information
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1 font-semibold">Phone</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{formatPhoneNumber(workerData?.phone)}</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1 font-semibold">UPI ID</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white font-mono">{maskedUPI}</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1 font-semibold">Language</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white capitalize">{workerData?.language || 'N/A'}</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-1 font-semibold">Shift Type</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white capitalize">{workerData?.shift || 'N/A'}</p>
                </div>
              </div>
            </section>

            <section>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-gigkavach-orange" />
                Service Area & Schedule
              </h3>
              <div className="space-y-3">
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-semibold">Operating Zones</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{workerData?.zone}</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-semibold flex items-center gap-2">
                    <Clock className="w-3 h-3" />
                    Shift Timings
                  </p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {workerData?.shift_start} - {workerData?.shift_end}
                  </p>
                </div>
              </div>
            </section>

            <section>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Zap className="w-4 h-4 text-gigkavach-orange" />
                Insurance Policy
              </h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-gigkavach-orange/10 to-orange-50 dark:from-gigkavach-orange/20 dark:to-gigkavach-navy p-4 rounded-lg border border-gigkavach-orange/20">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-semibold">Plan Tier</p>
                  <p className="text-lg font-bold text-gigkavach-orange">{workerData?.plan || 'N/A'}</p>
                </div>
                <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-gigkavach-navy p-4 rounded-lg border border-green-200 dark:border-green-800">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-semibold">Weekly Premium</p>
                  <p className="text-lg font-bold text-green-700 dark:text-green-400">{formatCurrency(workerData?.premium)}</p>
                </div>
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-gigkavach-navy p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-semibold">Coverage</p>
                  <p className="text-lg font-bold text-blue-700 dark:text-blue-400">{workerData?.coverage}%</p>
                </div>
              </div>
            </section>

            <section>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-gigkavach-orange" />
                Recent Payouts
              </h3>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {workerData?.payoutHistory && workerData.payoutHistory.length > 0 ? (
                  workerData.payoutHistory.slice(0, 10).map((p, idx) => (
                    <div
                      key={p.id || idx}
                      className="flex items-center justify-between bg-gray-50 dark:bg-gray-800 p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {new Date(p.triggered_at).toLocaleDateString()}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(p.triggered_at).toLocaleTimeString()}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-green-600 dark:text-green-400">
                          {formatCurrency(p.final_amount)}
                        </p>
                        <span
                          className={`text-xs px-2 py-1 rounded font-semibold ${
                            p.status === 'paid'
                              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                              : 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                          }`}
                        >
                          {String(p.status || '').charAt(0).toUpperCase() + String(p.status || '').slice(1)}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">No payouts yet</p>
                )}
              </div>
            </section>

            <section>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Activity className="w-4 h-4 text-gigkavach-orange" />
                Recent Activity
              </h3>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {workerData?.activityLog && workerData.activityLog.length > 0 ? (
                  workerData.activityLog.slice(0, 20).map((act, idx) => (
                    <div
                      key={act.id || idx}
                      className="flex gap-3 bg-gray-50 dark:bg-gray-800 p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      <div className="w-2 h-2 rounded-full bg-gigkavach-orange mt-1.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">{act.description}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(act.date).toLocaleDateString()} •{' '}
                          {new Date(act.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">No activities recorded</p>
                )}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
