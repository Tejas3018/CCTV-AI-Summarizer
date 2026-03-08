import React, { useState } from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import ChatInterface from './components/ChatInterface';
import DailySummary from './components/DailySummary';
import Timeline from './components/Timeline';
import { Video, MessageSquare, BarChart3, Calendar } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const tabs = [
    { id: 'dashboard', name: 'Live Events', icon: Video },
    { id: 'timeline', name: 'Timeline', icon: Calendar },
    { id: 'summary', name: 'Daily Summary', icon: BarChart3 },
    { id: 'chat', name: 'Ask Camera', icon: MessageSquare },
  ];

  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-b from-blue-50 via-slate-50 to-slate-100">
        <header className="bg-white/80 backdrop-blur border-b border-slate-200 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              <div className="flex items-center space-x-3">
                <div className="bg-gradient-to-tr from-blue-600 to-indigo-600 p-2.5 rounded-xl shadow-sm">
                  <Video className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">CCTV AI Monitor</h1>
                  <p className="text-sm text-slate-500">Smart insights from your live surveillance feed</p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="hidden sm:flex items-center px-3 py-1.5 rounded-full bg-slate-100 text-xs font-medium text-slate-600">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse mr-2" />
                  Camera online
                </div>
              </div>
            </div>
          </div>
        </header>

        <div className="bg-white/90 backdrop-blur border-b border-slate-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <nav className="flex space-x-2 sm:space-x-4 overflow-x-auto py-1" aria-label="Tabs">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`
                      relative flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-medium transition
                      ${isActive
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                      }
                    `}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{tab.name}</span>
                    {isActive && (
                      <span className="absolute inset-x-3 -bottom-1 h-0.5 rounded-full bg-blue-300" />
                    )}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {activeTab === 'dashboard' && <Dashboard />}
          {activeTab === 'timeline' && <Timeline />}
          {activeTab === 'summary' && <DailySummary />}
          {activeTab === 'chat' && <ChatInterface />}
        </main>
      </div>
    </Router>
  );
}

export default App;
