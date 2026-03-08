import React, { useState, useEffect } from 'react';
import { eventsAPI } from '../services/api';
import { Calendar, Clock, Filter, X } from 'lucide-react';
import { format, startOfDay, endOfDay } from 'date-fns';
import VideoPlayer from './VideoPlayer';

const Timeline = () => {
  const [events, setEvents] = useState([]);
  const [selectedDate, setSelectedDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [filterType, setFilterType] = useState('all');
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [loading, setLoading] = useState(false);
  const [visibleCount, setVisibleCount] = useState(20);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const start = startOfDay(new Date(selectedDate)).toISOString();
      const end = endOfDay(new Date(selectedDate)).toISOString();
      
      const response = await eventsAPI.getByRange(start, end);
      const sorted = [...response.data.events].sort(
        (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
      );
      setEvents(sorted);
      setVisibleCount(20);
    } catch (error) {
      console.error('Failed to fetch events:', error);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchEvents();
  }, [selectedDate]);

  const filteredEvents = filterType === 'all'
    ? events
    : events.filter(e => e.detection_type === filterType);

  const visibleEvents = filteredEvents.slice(0, visibleCount);

  const eventTypes = [...new Set(events.map(e => e.detection_type))];

  // Group events by hour
  const groupedEvents = visibleEvents.reduce((acc, event) => {
    const hour = new Date(event.timestamp).getHours();
    if (!acc[hour]) acc[hour] = [];
    acc[hour].push(event);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Date Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Calendar className="w-4 h-4 inline mr-2" />
              Select Date
            </label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Type Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Filter className="w-4 h-4 inline mr-2" />
              Filter by Type
            </label>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Types</option>
              {eventTypes.map(type => (
                <option key={type} value={type} className="capitalize">
                  {type}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Showing {visibleEvents.length} of {filteredEvents.length} events
          </p>
          {filterType !== 'all' && (
            <button
              onClick={() => setFilterType('all')}
              className="text-sm text-blue-600 hover:text-blue-800 flex items-center"
            >
              <X className="w-4 h-4 mr-1" />
              Clear filter
            </button>
          )}
        </div>
      </div>

      {/* Timeline */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-6">
          Timeline for {format(new Date(selectedDate), 'MMMM d, yyyy')}
        </h2>

        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading...</div>
        ) : filteredEvents.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No events found for this date
          </div>
        ) : (
          <>
          <div className="space-y-8">
            {Object.keys(groupedEvents).sort((a, b) => b - a).map(hour => (
              <div key={hour} className="relative">
                {/* Hour Header */}
                <div className="flex items-center mb-4">
                  <div className="bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-medium">
                    <Clock className="w-4 h-4 inline mr-1" />
                    {String(hour).padStart(2, '0')}:00
                  </div>
                  <div className="ml-3 text-sm text-gray-500">
                    {groupedEvents[hour].length} events
                  </div>
                </div>

                {/* Events Grid */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 ml-6">
                  {groupedEvents[hour].map(event => (
                    <div
                      key={event.id}
                      onClick={() => setSelectedEvent(event)}
                      className="group cursor-pointer"
                    >
                      <div className="relative overflow-hidden rounded-lg bg-gray-100 aspect-video">
                        {event.thumbnail_url ? (
                          <img
                            src={event.thumbnail_url}
                            alt={event.detection_type}
                            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-200"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center bg-gray-200">
                            <Clock className="w-8 h-8 text-gray-400" />
                          </div>
                        )}
                        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2">
                          <p className="text-white text-xs font-medium">
                            {format(new Date(event.timestamp), 'HH:mm:ss')}
                          </p>
                        </div>
                      </div>
                      <div className="mt-2">
                        <span className="inline-block px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded capitalize">
                          {event.detection_type}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          {filteredEvents.length > visibleEvents.length && (
            <div className="mt-6 text-center">
              <button
                onClick={() => setVisibleCount((prev) => prev + 20)}
                className="inline-flex items-center px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg"
              >
                Load more
              </button>
            </div>
          )}
          </>
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

export default Timeline;
