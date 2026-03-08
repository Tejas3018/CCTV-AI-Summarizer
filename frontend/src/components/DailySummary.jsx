import React, { useState, useEffect } from 'react';
import { summaryAPI } from '../services/api';
import { FileText, Calendar, TrendingUp, RefreshCw, Sparkles } from 'lucide-react';
import { format } from 'date-fns';
import PeopleBreakdownCard from './PeopleBreakdownCard';

const DailySummary = () => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selectedDate, setSelectedDate] = useState(format(new Date(), 'yyyy-MM-dd'));

  const fetchSummary = async () => {
    setLoading(true);
    try {
      const response = await summaryAPI.getByDate(selectedDate);
      setSummary(response.data);
    } catch (error) {
      console.error('Failed to fetch summary:', error);
      setSummary(null);
    }
    setLoading(false);
  };

  const generateSummary = async () => {
    setGenerating(true);
    try {
      await summaryAPI.generateSync(selectedDate);
      await fetchSummary();
    } catch (error) {
      console.error('Failed to generate summary:', error);
      alert('Failed to generate summary. Please try again.');
    }
    setGenerating(false);
  };

  useEffect(() => {
    fetchSummary();
  }, [selectedDate]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900 flex items-center">
            <FileText className="w-6 h-6 mr-2 text-blue-600" />
            Daily Summary
          </h2>
          
          <div className="flex items-center space-x-4">
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={generateSummary}
              disabled={generating}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {generating ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  <span>Generating...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  <span>Generate Summary</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading summary...</p>
        </div>
      ) : !summary ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Summary Available</h3>
          <p className="text-gray-600 mb-4">
            No summary has been generated for {format(new Date(selectedDate), 'MMMM d, yyyy')} yet.
          </p>
          <button
            onClick={generateSummary}
            className="inline-flex items-center space-x-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Sparkles className="w-5 h-5" />
            <span>Generate Now</span>
          </button>
        </div>
      ) : (
        <>
          {/* AI Summary */}
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg shadow p-6 border border-blue-100">
            <div className="flex items-center mb-4">
              <div className="bg-blue-600 p-2 rounded-lg">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <h3 className="ml-3 text-lg font-semibold text-gray-900">AI-Generated Summary</h3>
            </div>
            <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
              {summary.summary}
            </p>
            <div className="mt-4 text-sm text-gray-500">
              Generated on {format(new Date(summary.generated_at), 'MMM d, yyyy \'at\' h:mm a')}
            </div>
          </div>

          {/* Statistics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Total Events */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-gray-600">Total Events</h3>
                <TrendingUp className="w-5 h-5 text-blue-600" />
              </div>
              <p className="text-3xl font-bold text-gray-900">{summary.events_count}</p>
            </div>

            {/* First Activity */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-gray-600">First Activity</h3>
                <Calendar className="w-5 h-5 text-green-600" />
              </div>
              <p className="text-3xl font-bold text-gray-900">
                {summary.statistics.first_activity || 'N/A'}
              </p>
            </div>

            {/* Last Activity */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-gray-600">Last Activity</h3>
                <Calendar className="w-5 h-5 text-purple-600" />
              </div>
              <p className="text-3xl font-bold text-gray-900">
                {summary.statistics.last_activity || 'N/A'}
              </p>
            </div>
          </div>

          <PeopleBreakdownCard className="mt-6" date={selectedDate} />

          {/* Detection Types */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Detections by Type</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(summary.statistics.by_type || {}).map(([type, count]) => (
                <div key={type} className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-600 capitalize">{type}</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{count}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Peak Hours */}
          {summary.statistics.peak_hours && summary.statistics.peak_hours.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Peak Activity Hours</h3>
              <div className="space-y-2">
                {summary.statistics.peak_hours.map((peak, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="font-medium text-gray-900">
                      {String(peak.hour).padStart(2, '0')}:00
                    </span>
                    <div className="flex items-center">
                      <div className="w-48 bg-gray-200 rounded-full h-2 mr-3">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{
                            width: `${(peak.count / summary.events_count) * 100}%`
                          }}
                        />
                      </div>
                      <span className="text-sm text-gray-600">{peak.count} events</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Key Events */}
          {summary.key_events && summary.key_events.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Key Events</h3>
              <div className="space-y-3">
                {summary.key_events.map((event, index) => (
                  <div key={index} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                    <div className="flex items-center space-x-3">
                      <span className="inline-block px-3 py-1 text-sm font-medium bg-blue-100 text-blue-800 rounded capitalize">
                        {event.type}
                      </span>
                      <span className="text-sm text-gray-600">
                        {format(new Date(event.timestamp), 'h:mm:ss a')}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {(event.confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default DailySummary;
