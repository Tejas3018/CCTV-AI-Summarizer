import React, { useState, useEffect } from 'react';
import { eventsAPI } from '../services/api';
import { Clock, User, Car, Dog, RefreshCw } from 'lucide-react';
import { format } from 'date-fns';
import VideoPlayer from './VideoPlayer';
import PeopleBreakdownCard from './PeopleBreakdownCard';

const Dashboard = () => {
  const [events, setEvents] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [visibleCount, setVisibleCount] = useState(10);

  const fetchData = async () => {
    try {
      const [eventsRes, statsRes] = await Promise.all([
        eventsAPI.getToday(),
        eventsAPI.getTodayStats(),
      ]);
      setEvents(eventsRes.data.events);
      setStats(statsRes.data);
      setVisibleCount(10);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    // Auto-refresh every 5 seconds
    let interval;
    if (autoRefresh) {
      interval = setInterval(fetchData, 5000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const getIconForType = (type) => {
    const t = type.toLowerCase();
    switch (t) {
      case 'person':
      case 'male':
      case 'female':
      case 'kid':
        return <User className="w-5 h-5" />;
      case 'car':
      case 'truck':
      case 'bus':
        return <Car className="w-5 h-5" />;
      case 'dog':
      case 'cat':
        return <Dog className="w-5 h-5" />;
      default:
        return <div className="w-5 h-5 bg-gray-400 rounded-full" />;
    }
  };

  const getColorForType = (type) => {
    const t = type.toLowerCase();
    switch (t) {
      case 'person':
        return 'bg-blue-100 text-blue-800';
      case 'male':
        return 'bg-sky-100 text-sky-800';
      case 'female':
        return 'bg-pink-100 text-pink-800';
      case 'kid':
        return 'bg-amber-100 text-amber-800';
      case 'car':
      case 'truck':
      case 'bus':
        return 'bg-green-100 text-green-800';
      case 'dog':
      case 'cat':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Events</p>
              <p className="text-3xl font-bold text-gray-900">{stats?.total || 0}</p>
            </div>
            <div className="bg-blue-100 p-3 rounded-lg">
              <Clock className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">People</p>
              <p className="text-3xl font-bold text-gray-900">
                {stats?.people_breakdown?.total ?? stats?.by_type?.person ?? 0}
              </p>
            </div>
            <div className="bg-green-100 p-3 rounded-lg">
              <User className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <PeopleBreakdownCard className="rounded-lg shadow" />

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Vehicles</p>
              <p className="text-3xl font-bold text-gray-900">
                {(stats?.by_type?.car || 0)
                  + (stats?.by_type?.truck || 0)
                  + (stats?.by_type?.motorcycle || 0)
                  + (stats?.by_type?.bus || 0)}
              </p>
            </div>
            <div className="bg-purple-100 p-3 rounded-lg">
              <Car className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Auto Refresh</p>
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`mt-2 px-4 py-2 rounded-lg font-medium ${
                  autoRefresh
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-200 text-gray-700'
                }`}
              >
                {autoRefresh ? 'ON' : 'OFF'}
              </button>
            </div>
            <RefreshCw className={`w-6 h-6 text-gray-600 ${autoRefresh ? 'animate-spin' : ''}`} />
          </div>
        </div>
      </div>

      {/* Events List */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Today's Events</h2>
            <p className="text-xs text-gray-500">Click an event to view the recorded clip</p>
          </div>
          <button
            onClick={fetchData}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RefreshCw className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        <div className="divide-y divide-gray-200">
          {events.length === 0 ? (
            <div className="px-6 py-12 text-center text-gray-500">
              No events detected today
            </div>
          ) : (
            events.slice(0, visibleCount).map((event) => (
              <div
                key={event.id}
                onClick={() => setSelectedEvent(event)}
                className="px-6 py-4 hover:bg-blue-50 cursor-pointer transition-colors border-l-4 border-transparent hover:border-blue-400"
              >
                <div className="flex items-center space-x-4">
                  {/* Thumbnail */}
                  {event.thumbnail_url && (
                    <img
                      src={event.thumbnail_url}
                      alt={event.detection_type}
                      className="w-24 h-16 object-cover rounded-lg"
                    />
                  )}

                  {/* Event Info */}
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <span className={`inline-flex items-center space-x-1 px-3 py-1 rounded-full text-sm font-medium ${getColorForType(event.detection_type)}`}>
                        {getIconForType(event.detection_type)}
                        <span className="capitalize">{event.detection_type}</span>
                      </span>
                      <span className="text-sm text-gray-500">
                        {format(new Date(event.timestamp), 'h:mm:ss a')}
                      </span>
                      <span className="text-xs text-gray-400">
                        {(event.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-gray-600">
                      {format(new Date(event.timestamp), 'MMMM d, yyyy')}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {events.length > visibleCount && (
          <div className="px-6 py-4 border-t border-gray-200 text-center">
            <button
              onClick={() => setVisibleCount((prev) => prev + 10)}
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg"
            >
              Load more
            </button>
          </div>
        )}
      </div>

      {/* Video Player Modal */}
      {selectedEvent && (
        <VideoPlayer
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </div>
  );
};

export default Dashboard;
