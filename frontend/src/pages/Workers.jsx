import { useState, useMemo, useEffect } from 'react';
import { Search, Eye, Shield, SlidersHorizontal } from 'lucide-react';
import { formatPhoneNumber, getInitials } from '../utils/formatters';
import { workerAPI } from '../api/workers';
import { WorkerModal } from '../components/workers/WorkerModal';
/*
const [selectedWorker, setSelectedWorker] = useState(null);
const [isPopupOpen, setIsPopupOpen] = useState(false);
const [isModalOpen, setIsModalOpen] = useState(false);
const [selectedWorkerId, setSelectedWorkerId] = useState(null);
*/

/*const handleWorkerClick = (worker) => {
  setSelectedWorker(worker);
  setIsPopupOpen(true);
};*/
// Worker Profile Drawer Component



const PLAN_OPTIONS = [
  {
    value: 'all',
    label: 'All',
    sub: 'plans',
    idle: 'text-gray-600 dark:text-gray-400 hover:bg-white/80 dark:hover:bg-gray-700/60 hover:text-gray-900 dark:hover:text-white',
    active: 'bg-gradient-to-b from-gigkavach-orange to-orange-600 text-white shadow-md shadow-orange-500/25 ring-1 ring-orange-400/40',
    dot: 'bg-gray-400 dark:bg-gray-500',
  },
  {
    value: 'Shield Basic',
    label: 'Basic',
    sub: 'Shield',
    idle: 'text-gray-600 dark:text-gray-400 hover:bg-white/80 dark:hover:bg-gray-700/60 hover:text-blue-700 dark:hover:text-blue-300',
    active: 'bg-gradient-to-b from-blue-500 to-blue-600 text-white shadow-md shadow-blue-500/25 ring-1 ring-blue-400/40',
    dot: 'bg-blue-500',
  },
  {
    value: 'Shield Plus',
    label: 'Plus',
    sub: 'Shield',
    idle: 'text-gray-600 dark:text-gray-400 hover:bg-white/80 dark:hover:bg-gray-700/60 hover:text-purple-700 dark:hover:text-purple-300',
    active: 'bg-gradient-to-b from-purple-500 to-purple-600 text-white shadow-md shadow-purple-500/25 ring-1 ring-purple-400/40',
    dot: 'bg-purple-500',
  },
  {
    value: 'Shield Pro',
    label: 'Pro',
    sub: 'Shield',
    idle: 'text-gray-600 dark:text-gray-400 hover:bg-white/80 dark:hover:bg-gray-700/60 hover:text-amber-800 dark:hover:text-amber-300',
    active: 'bg-gradient-to-b from-amber-500 to-amber-600 text-white shadow-md shadow-amber-500/25 ring-1 ring-amber-400/40',
    dot: 'bg-amber-500',
  },
];

function normalizeWorkerPlan(plan) {
  if (!plan) return '';
  const p = String(plan).toLowerCase();
  if (p.includes('basic')) return 'Shield Basic';
  if (p.includes('plus')) return 'Shield Plus';
  if (p.includes('pro')) return 'Shield Pro';
  return String(plan);
}

export const Workers = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterPlan, setFilterPlan] = useState('all');
  const handleRowClick = (worker) => {
  setSelectedWorkerId(worker.id);
  setIsModalOpen(true);
};

  // Modal state
const [selectedWorkerId, setSelectedWorkerId] = useState(null);
const [isModalOpen, setIsModalOpen] = useState(false);
 // const [selectedWorker, setSelectedWorker] = useState(null);
  //const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const [workers, setWorkers] = useState([]);
  const [loading, setLoading] = useState(true);

  // ✅ pagination state (MUST be at top)
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 5;

  // ✅ FETCH ONCE
  const fetchWorkers = async () => {
    setLoading(true);
    try {
      const response = await workerAPI.getAll();

      const formatted = response.data.map((w) => ({
        id: w.id,
        name: w.name,
        phone: w.phone,
        upi: w.upi_id || 'N/A',
        zone: w.zone || 'N/A',
        status: w.status || 'inactive',
        plan: w.plan,
        premium:
          w.plan === 'Shield Basic'
            ? 69
            : w.plan === 'Shield Plus'
            ? 89
            : 99,
        coverage: w.coverage,
        coverageWindow: 'Flexible',

        last7DaysEarnings: [500, 700, 600, 800, 650, 720, 900],
        dciHistory: [],
        fraudStatus: 'clean',
        payoutHistory: [],
      }));

      setWorkers(formatted);
    } catch (err) {
      console.error('Error fetching workers:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkers();
  }, []);

  // ✅ FILTERING
  const filteredWorkers = useMemo(() => {
    let result = workers;

    if (searchQuery) {
      result = result.filter(
        (w) =>
          w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          w.phone.includes(searchQuery) ||
          w.zone.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    if (filterStatus !== 'all') {
      result = result.filter((w) => w.status === filterStatus);
    }

    if (filterPlan !== 'all') {
      result = result.filter((w) => normalizeWorkerPlan(w.plan) === filterPlan);
    }

    return result;
  }, [workers, searchQuery, filterStatus, filterPlan]);

  // ✅ RESET PAGE WHEN FILTER CHANGES
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, filterStatus, filterPlan]);

  // ✅ PAGINATION
  const totalPages = Math.ceil(filteredWorkers.length / ITEMS_PER_PAGE);

  const paginatedWorkers = filteredWorkers.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const start = (currentPage - 1) * ITEMS_PER_PAGE + 1;
  const end = Math.min(currentPage * ITEMS_PER_PAGE, filteredWorkers.length);

  // ✅ LOADING (AFTER ALL HOOKS)
  if (loading) {
    return <div className="p-6">Loading workers...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Workers</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">Manage and monitor your delivery workforce</p>
      </div>

      {/* Controls */}
      <div className="relative overflow-hidden rounded-2xl border border-gray-200/90 dark:border-gray-700/90 bg-white dark:bg-gigkavach-surface shadow-[0_1px_3px_rgba(0,0,0,0.06),0_8px_24px_-6px_rgba(15,27,45,0.08)] dark:shadow-[0_1px_3px_rgba(0,0,0,0.2),0_12px_40px_-12px_rgba(0,0,0,0.45)]">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gigkavach-orange/35 to-transparent" />
        <div className="p-5 md:p-6 space-y-6">
          <div className="flex flex-col lg:flex-row lg:items-end gap-5">
            <div className="flex-1 space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Search
              </label>
              <div className="relative">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />
                <input
                  type="text"
                  placeholder="Name, phone, or zone…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50/80 dark:bg-gray-800/50 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-500 text-sm focus:outline-none focus:ring-2 focus:ring-gigkavach-orange/80 focus:border-transparent transition-shadow"
                />
              </div>
            </div>

            <div className="w-full lg:w-52 shrink-0 space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-2">
                <SlidersHorizontal className="w-3.5 h-3.5 text-gigkavach-orange" />
                Status
              </label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50/80 dark:bg-gray-800/50 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-gigkavach-orange/80 focus:border-transparent cursor-pointer appearance-none bg-[length:1rem] bg-[right_0.75rem_center] bg-no-repeat pr-10 transition-shadow"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%239ca3af'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E")`,
                }}
              >
                <option value="all">All statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="expired">Expired</option>
              </select>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-2">
                <Shield className="w-3.5 h-3.5 text-gigkavach-orange" />
                Filter by plan
              </p>
              <span className="text-xs text-gray-500 dark:text-gray-500 tabular-nums">
                {filteredWorkers.length === workers.length
                  ? `${workers.length} workers`
                  : `${filteredWorkers.length} of ${workers.length}`}
              </span>
            </div>

            <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2 p-1.5 rounded-2xl bg-gradient-to-br from-gray-100/90 to-gray-50/50 dark:from-gray-800/80 dark:to-gray-900/40 ring-1 ring-gray-200/80 dark:ring-gray-700/80">
              {PLAN_OPTIONS.map(({ value, label, sub, idle, active, dot }) => {
                const isOn = filterPlan === value;
                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setFilterPlan(value)}
                    className={`group flex min-w-0 flex-1 sm:flex-initial items-center justify-center gap-2.5 rounded-xl px-4 py-2.5 text-left transition-all duration-200 ${
                      isOn ? `${active} scale-[1.02]` : `bg-white/70 dark:bg-gray-800/40 ${idle} ring-1 ring-transparent`
                    }`}
                  >
                    <span
                      className={`h-2 w-2 shrink-0 rounded-full ${dot} ${isOn ? 'ring-2 ring-white/40' : 'opacity-80 group-hover:opacity-100'}`}
                      aria-hidden
                    />
                    <span className="flex min-w-0 flex-col leading-tight">
                      <span className="text-sm font-semibold tracking-tight">{label}</span>
                      <span
                        className={`text-[10px] font-medium uppercase tracking-wide ${
                          isOn ? 'text-white/85' : 'text-gray-400 dark:text-gray-500 group-hover:text-gray-500 dark:group-hover:text-gray-400'
                        }`}
                      >
                        {sub}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Workers Table */}
      <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                  Worker
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                  Zone
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                  Shield Policy
                </th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {paginatedWorkers.map((worker) => (
                <tr
                  key={worker.id}
                  className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gigkavach-orange flex items-center justify-center text-white font-bold">
                          {getInitials(worker.name?.split(' ')[0] || '',worker.name?.split(' ')[1] || '')}
                      </div>
                      <div>
                        <p
  onClick={() => handleRowClick(worker)} // new function for modal
  className="font-medium text-orange-500 cursor-pointer hover:underline"
>
  {worker.name}
</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{formatPhoneNumber(worker.phone)}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{worker.zone}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${
                        worker.status === 'active'
                          ? 'bg-green-100 dark:bg-green-900 text-green-900 dark:text-green-100'
                          : worker.status === 'inactive'
                          ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-300'
                          : worker.status === 'expired'
                          ? 'bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100'
                          : 'bg-yellow-100 dark:bg-yellow-900 text-yellow-900 dark:text-yellow-100'
                      }`}
                    >
                      {worker.status
  ? worker.status.charAt(0).toUpperCase() + worker.status.slice(1)
  : 'Unknown'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-2 h-2 rounded-full ${             worker.plan === 'Shield Pro'                ? 'bg-amber-500'                : worker.plan === 'Shield Plus'                ? 'bg-blue-500'                : 'bg-green-500'            }`}
                        />
                        {worker.plan}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{worker.coverage}% coverage</p>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleRowClick(worker)}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors text-gigkavach-orange hover:text-orange-700"
                      title="View profile"
                    >
                      <Eye className="w-5 h-5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
<div className="flex items-center justify-between mt-4 px-4 pb-4">
<p className="text-sm text-gray-600 dark:text-gray-400">
  Showing {start}-{end} of {filteredWorkers.length}
</p>

  <div className="flex gap-2">
    <button
      onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
      disabled={currentPage === 1}
      className="px-3 py-1 rounded-lg border text-sm disabled:opacity-50"
    >
      Prev
    </button>

    <button
      onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
      disabled={currentPage === totalPages || totalPages === 0}
      className="px-3 py-1 rounded-lg border text-sm disabled:opacity-50"
    >
      Next
    </button>
  </div>
</div>
        {/* Empty State */}
        {workers.length === 0 && (
          <div className="p-12 text-center">
            <Search className="w-12 h-12 text-gray-400 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-gray-600 dark:text-gray-400 font-medium">No workers found</p>
            <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">Try adjusting your filters or search criteria</p>
          </div>
        )}
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">Total Workers</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white">{workers.length}</p>
        </div>
        <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">Active</p>
          <p className="text-3xl font-bold text-green-600 dark:text-green-400">{workers.filter((w) => w.status === 'active').length}</p>
        </div>
        <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">Average Coverage</p>
          <p className="text-3xl font-bold text-gigkavach-orange">
            {workers.length === 0 ? '0%' : (workers.reduce((sum, w) => sum + w.coverage, 0) / workers.length).toFixed(0) + '%'}
          </p>
        </div>
      </div>

      {/* Worker Profile Drawer */}

      <WorkerModal
        workerId={selectedWorkerId}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
};
