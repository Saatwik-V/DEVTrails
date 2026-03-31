import { useEffect, useMemo, useRef, useState } from 'react';
import { payoutAPI } from '../../api/payouts';
import { formatCurrency, formatDate } from '../../utils/formatters';

const DEFAULT_POLL_MS = 5000;
const DEFAULT_LIMIT = 20;

const STATUS_BADGE = {
  triggered: { label: 'Triggered', className: 'bg-blue-100 dark:bg-blue-900 text-blue-900 dark:text-blue-100 border-blue-300 dark:border-blue-700' },
  calculating: { label: 'Calculating', className: 'bg-amber-100 dark:bg-amber-900 text-amber-900 dark:text-amber-100 border-amber-300 dark:border-amber-700' },
  fraud_check: { label: 'Fraud check', className: 'bg-purple-100 dark:bg-purple-900 text-purple-900 dark:text-purple-100 border-purple-300 dark:border-purple-700' },
  payout_sent: { label: 'Payout sent', className: 'bg-green-100 dark:bg-green-900 text-green-900 dark:text-green-100 border-green-300 dark:border-green-700' },
};

function normalizePayout(raw) {
  const workerName =
    raw.worker_name ??
    raw.workerName ??
    raw.worker?.name ??
    raw.worker ??
    '';

  const workerId = raw.worker_id ?? raw.workerId ?? raw.worker?.id ?? null;

  const amount = raw.amount ?? raw.payout_amount ?? raw.payoutAmount ?? 0;
  const dciScore = raw.dci_score ?? raw.dciScore ?? raw.dci ?? null;
  const fraudScore = raw.fraud_score ?? raw.fraudScore ?? raw.fraud ?? null;
  const status = raw.status ?? raw.stage ?? raw.state ?? 'processing';
  const timestamp = raw.timestamp ?? raw.created_at ?? raw.createdAt ?? raw.updated_at ?? raw.updatedAt ?? null;
  const id = raw.id ?? raw.payout_id ?? raw.payoutId ?? `${workerName}-${amount}-${timestamp ?? ''}-${status}`;

  return {
    id,
    worker_id: workerId,
    worker_name: workerName,
    amount,
    dci_score: dciScore,
    fraud_score: fraudScore,
    status,
    timestamp,
  };
}

function getStatusBadge(status) {
  const key = (status || '').toString().toLowerCase();
  return STATUS_BADGE[key] ?? {
    label: status ? String(status).replaceAll('_', ' ') : 'Processing',
    className: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-700',
  };
}

export function RealTimePayoutFeed({ pollMs = DEFAULT_POLL_MS, limit = DEFAULT_LIMIT, onWorkerClick }) {
  const [items, setItems] = useState([]);
  const [newIds, setNewIds] = useState(() => new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const prevIdsRef = useRef(new Set());
  const newIdsTimerRef = useRef(null);

  const rows = useMemo(() => items.slice(0, limit), [items, limit]);

  useEffect(() => {
    let isMounted = true;

    const fetchOnce = async () => {
      try {
        setError('');
        const data = await payoutAPI.getAll({ status: 'processing' });
        const list = Array.isArray(data) ? data : Array.isArray(data?.payouts) ? data.payouts : Array.isArray(data?.data) ? data.data : [];
        const normalized = list.map(normalizePayout);

        normalized.sort((a, b) => {
          const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0;
          const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0;
          return tb - ta;
        });

        const latest = normalized.slice(0, limit);

        const prev = prevIdsRef.current;
        const nextIds = new Set(latest.map((x) => x.id));

        const added = [];
        for (const x of latest) {
          if (!prev.has(x.id)) added.push(x.id);
        }

        prevIdsRef.current = nextIds;

        if (isMounted) {
          setItems(latest);
          if (added.length) {
            const addedSet = new Set(added);
            setNewIds(addedSet);
            if (newIdsTimerRef.current) clearTimeout(newIdsTimerRef.current);
            newIdsTimerRef.current = setTimeout(() => setNewIds(new Set()), 1400);
          }
        }
      } catch (e) {
        if (isMounted) {
          setError(e?.message || 'Failed to load payouts.');
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchOnce();
    const id = setInterval(fetchOnce, pollMs);
    return () => {
      isMounted = false;
      clearInterval(id);
      if (newIdsTimerRef.current) clearTimeout(newIdsTimerRef.current);
    };
  }, [pollMs, limit]);

  return (
    <div className="bg-white dark:bg-gigkavach-surface rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Processing payouts (live)</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Polling every {Math.round(pollMs / 1000)}s · Latest {limit}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1 rounded-full bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800">
            <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" />
            Live
          </span>
        </div>
      </div>

      {error ? (
        <div className="px-6 py-4 text-sm text-red-700 dark:text-red-300 bg-red-50/50 dark:bg-red-950/30">
          {error}
        </div>
      ) : null}

      <div className="max-h-[420px] overflow-y-auto">
        <div className="min-w-[860px]">
          <div className="grid grid-cols-12 gap-3 px-6 py-3 text-[11px] font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <div className="col-span-3">Worker</div>
            <div className="col-span-2">Amount</div>
            <div className="col-span-1 text-center">DCI</div>
            <div className="col-span-1 text-center">Fraud</div>
            <div className="col-span-2">Status</div>
            <div className="col-span-3">Timestamp</div>
          </div>

          {isLoading ? (
            <div className="px-6 py-6 text-sm text-gray-600 dark:text-gray-300">Loading…</div>
          ) : rows.length ? (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {rows.map((p) => {
                const badge = getStatusBadge(p.status);
                const isNew = newIds.has(p.id);
                return (
                  <div
                    key={p.id}
                    className={`grid grid-cols-12 gap-3 px-6 py-3 items-center hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${
                      isNew ? 'animate-feed-new' : ''
                    }`}
                  >
                    <div className="col-span-3">
                      {p.worker_id && onWorkerClick ? (
                        <button
                          type="button"
                          onClick={() => onWorkerClick(p.worker_id)}
                          className="text-sm font-medium text-gray-900 hover:text-blue-600 dark:text-white dark:hover:text-blue-400 hover:underline text-left truncate w-full transition-colors"
                        >
                          {p.worker_name || '—'}
                        </button>
                      ) : (
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{p.worker_name || '—'}</p>
                      )}
                    </div>
                    <div className="col-span-2 font-mono font-bold text-gray-900 dark:text-white">
                      {formatCurrency(Number(p.amount) || 0)}
                    </div>
                    <div className="col-span-1 text-center font-mono text-sm text-gray-700 dark:text-gray-200">
                      {p.dci_score === null || p.dci_score === undefined ? '—' : Number(p.dci_score).toFixed(0)}
                    </div>
                    <div className="col-span-1 text-center font-mono text-sm text-gray-700 dark:text-gray-200">
                      {p.fraud_score === null || p.fraud_score === undefined ? '—' : Number(p.fraud_score).toFixed(0)}
                    </div>
                    <div className="col-span-2">
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${badge.className}`}>
                        {badge.label}
                      </span>
                    </div>
                    <div className="col-span-3 text-sm text-gray-600 dark:text-gray-300">
                      {p.timestamp ? formatDate(p.timestamp, 'datetime') : '—'}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="px-6 py-6 text-sm text-gray-600 dark:text-gray-300">No processing payouts right now.</div>
          )}
        </div>
      </div>
    </div>
  );
}

