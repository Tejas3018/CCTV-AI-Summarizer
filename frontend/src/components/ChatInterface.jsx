import React, { useState, useRef, useEffect } from 'react';
import { queryAPI } from '../services/api';
import { Send, Bot, User as UserIcon, Lightbulb, Video } from 'lucide-react';
import { format } from 'date-fns';
import VideoPlayer from './VideoPlayer';

const ChatInterface = () => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m your CCTV AI assistant. You can ask me questions about your surveillance footage. For example, try asking "Show me people detected after 5 PM" or "What happened this morning?"',
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [examples, setExamples] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Fetch example queries
    queryAPI.getExamples().then(res => {
      setExamples(res.data.examples);
    }).catch(err => console.error('Failed to fetch examples:', err));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await queryAPI.ask(input);
      
      const assistantMessage = {
        role: 'assistant',
        content: response.data.response,
        events: response.data.events || [],
        event_count: response.data.event_count || 0,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Query failed:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
        error: true,
      }]);
    }

    setLoading(false);
  };

  const handleExampleClick = (exampleQuery) => {
    setInput(exampleQuery);
  };

  return (
    <div className="h-[calc(100vh-16rem)] flex flex-col">
      {/* Example Queries */}
      {messages.length === 1 && (
        <div className="bg-blue-50 rounded-lg p-4 mb-4 border border-blue-200">
          <div className="flex items-center mb-3">
            <Lightbulb className="w-5 h-5 text-blue-600 mr-2" />
            <h3 className="font-semibold text-gray-900">Try these examples:</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {examples.slice(0, 4).map((example, index) => (
              <button
                key={index}
                onClick={() => handleExampleClick(example.query)}
                className="text-left p-3 bg-white rounded-lg hover:bg-blue-100 transition-colors border border-gray-200"
              >
                <p className="text-sm font-medium text-gray-900">{example.query}</p>
                <p className="text-xs text-gray-500 mt-1">{example.description}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto bg-white rounded-lg shadow">
        <div className="p-6 space-y-4">
          {messages.map((message, index) => (
            <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex max-w-3xl ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                {/* Avatar */}
                <div className={`flex-shrink-0 ${message.role === 'user' ? 'ml-3' : 'mr-3'}`}>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    message.role === 'user' ? 'bg-blue-600' : 'bg-gray-700'
                  }`}>
                    {message.role === 'user' ? (
                      <UserIcon className="w-6 h-6 text-white" />
                    ) : (
                      <Bot className="w-6 h-6 text-white" />
                    )}
                  </div>
                </div>

                {/* Message Content */}
                <div>
                  <div className={`rounded-lg p-4 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : message.error
                      ? 'bg-red-50 text-red-900 border border-red-200'
                      : 'bg-gray-100 text-gray-900'
                  }`}>
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  </div>

                  {/* Events */}
                  {message.events && message.events.length > 0 && (
                    <div className="mt-3 space-y-2">
                      <p className="text-sm text-gray-600 font-medium">
                        Found {message.event_count} event{message.event_count !== 1 ? 's' : ''}:
                      </p>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {message.events.slice(0, 6).map((event) => (
                          <div
                            key={event.id}
                            onClick={() => setSelectedEvent(event)}
                            className="cursor-pointer group"
                          >
                            <div className="relative overflow-hidden rounded-lg bg-gray-200 aspect-video">
                              {event.thumbnail_path && (
                                <img
                                  src={`/thumbnails/${event.thumbnail_path}`}
                                  alt={event.type}
                                  className="w-full h-full object-cover group-hover:scale-110 transition-transform"
                                />
                              )}
                              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-opacity flex items-center justify-center">
                                <Video className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                              </div>
                            </div>
                            <div className="mt-1 flex items-center justify-between">
                              <span className="text-xs font-medium text-gray-900 capitalize">
                                {event.type}
                              </span>
                              <span className="text-xs text-gray-500">
                                {format(new Date(event.timestamp), 'HH:mm')}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                      {message.event_count > 6 && (
                        <p className="text-xs text-gray-500 mt-2">
                          And {message.event_count - 6} more...
                        </p>
                      )}
                    </div>
                  )}

                  {/* Timestamp */}
                  <p className="text-xs text-gray-500 mt-2">
                    {format(message.timestamp, 'h:mm a')}
                  </p>
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="flex">
                <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center mr-3">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <div className="bg-gray-100 rounded-lg p-4">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="mt-4">
        <form onSubmit={handleSubmit} className="flex space-x-4">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your CCTV footage..."
            disabled={loading}
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <Send className="w-5 h-5" />
            <span>Send</span>
          </button>
        </form>
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

export default ChatInterface;
