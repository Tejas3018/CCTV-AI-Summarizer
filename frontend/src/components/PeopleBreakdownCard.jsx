import React, { useEffect, useState } from 'react';

export default function PeopleBreakdownCard({ className = '', date = null }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const url = date
          ? `/api/events/stats/day?date=${encodeURIComponent(date)}`
          : '/api/events/stats/today';
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (!cancelled) {
          setData(json.people_breakdown || { male: 0, female: 0, kid: 0, person: 0, total: 0 });
        }
      } catch (e) {
        if (!cancelled) setErr(e.message || 'Failed to load people breakdown');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [date]);

  if (loading) return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      Loading…
    </div>
  );
  if (err) return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      Error: {err}
    </div>
  );
  if (!data) return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      No data
    </div>
  );

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-sm font-medium text-gray-600">People Breakdown</p>
          <p className="text-xs text-gray-400">Today</p>
        </div>
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
          Total {data.total}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div className="space-y-1">
          <p className="text-xs text-gray-500">Male</p>
          <p className="text-xl font-semibold text-sky-700">{data.male}</p>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-gray-500">Female</p>
          <p className="text-xl font-semibold text-pink-700">{data.female}</p>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-gray-500">Kids</p>
          <p className="text-xl font-semibold text-amber-700">{data.kid}</p>
        </div>
      </div>
      <div className="mt-3 text-xs text-gray-500">
        Unlabeled persons: <span className="font-medium text-gray-700">{data.person}</span>
      </div>
    </div>
  );
}