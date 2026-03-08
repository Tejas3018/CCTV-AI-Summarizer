import React from 'react';
import { X, Download, Clock } from 'lucide-react';
import { format } from 'date-fns';
import { eventsAPI } from '../services/api';

const VideoPlayer = ({ event, onClose }) => {
  if (!event) return null;

  const clipUrl = event.clip_url || eventsAPI.getClipUrl(event.id);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 capitalize">
              {event.detection_type} Detection
            </h3>
            <p className="text-sm text-gray-500">
              {format(new Date(event.timestamp), 'MMMM d, yyyy \'at\' h:mm:ss a')}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-gray-600" />
          </button>
        </div>

        {/* Video Player */}
        <div className="bg-black aspect-video">
          {clipUrl ? (
            <video
              src={clipUrl}
              controls
              autoPlay
              className="w-full h-full"
            >
              Your browser does not support the video tag.
            </video>
          ) : (
            <div className="w-full h-full flex items-center justify-center text-white">
              <div className="text-center">
                <Clock className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Video clip not available</p>
              </div>
            </div>
          )}
        </div>

        {/* Details */}
        <div className="p-4 bg-gray-50">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-gray-500">Detection Type</p>
              <p className="text-sm font-medium text-gray-900 capitalize">
                {event.detection_type}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Confidence</p>
              <p className="text-sm font-medium text-gray-900">
                {(event.confidence * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Time</p>
              <p className="text-sm font-medium text-gray-900">
                {format(new Date(event.timestamp), 'h:mm:ss a')}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Camera</p>
              <p className="text-sm font-medium text-gray-900">
                {event.camera_id || 'Home Camera'}
              </p>
            </div>
          </div>

          {/* Actions */}
          {clipUrl && (
            <div className="mt-4 flex space-x-3">
              <a
                href={clipUrl}
                download
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <Download className="w-4 h-4" />
                <span>Download Clip</span>
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VideoPlayer;
