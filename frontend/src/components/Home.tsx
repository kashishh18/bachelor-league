import React, { useState, useEffect } from 'react';
import { Heart, Trophy, Users, Star, Crown, TrendingUp, Play, Calendar, MapPin } from 'lucide-react';

const Home: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check backend health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('https://bachelor-league-production.up.railway.app/health');
        const data = await response.json();
        setHealthStatus(data);
      } catch (error) {
        console.error('Backend health check failed:', error);
        setHealthStatus(null);
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 to-red-50">
      {/* Header */}
      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-6">
            <Heart className="w-16 h-16 text-pink-500 mr-4 animate-pulse" />
            <h1 className="text-6xl font-bold text-gray-800">Bachelor League</h1>
          </div>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed">
            The ultimate fantasy experience for Bachelor Nation! 🌹 Draft contestants, 
            predict eliminations, and compete with friends in real-time.
          </p>
        </div>

        {/* Backend Status */}
        <div className="max-w-4xl mx-auto mb-12">
          <div className="bg-white rounded-2xl shadow-xl p-8 border border-pink-100">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-gray-800">System Status</h2>
              <div className={`flex items-center px-4 py-2 rounded-full ${
                healthStatus ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}>
                <div className={`w-3 h-3 rounded-full mr-2 ${
                  healthStatus ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                }`}></div>
                <span className="font-semibold">
                  {loading ? 'Checking...' : healthStatus ? 'Online' : 'Offline'}
                </span>
              </div>
            </div>
            
            {healthStatus && (
              <div className="grid md:grid-cols-3 gap-6">
                <div className="text-center p-4 bg-green-50 rounded-xl">
                  <Trophy className="w-8 h-8 text-green-500 mx-auto mb-2" />
                  <h3 className="font-semibold text-gray-800">API Status</h3>
                  <p className="text-green-600 font-medium">✅ Connected</p>
                </div>
                
                <div className="text-center p-4 bg-blue-50 rounded-xl">
                  <Users className="w-8 h-8 text-blue-500 mx-auto mb-2" />
                  <h3 className="font-semibold text-gray-800">Database</h3>
                  <p className="text-blue-600 font-medium">✅ {healthStatus.services?.database || 'Ready'}</p>
                </div>
                
                <div className="text-center p-4 bg-purple-50 rounded-xl">
                  <Star className="w-8 h-8 text-purple-500 mx-auto mb-2" />
                  <h3 className="font-semibold text-gray-800">ML Engine</h3>
                  <p className="text-purple-600 font-medium">✅ {healthStatus.services?.ml_engine || 'Active'}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Current Season */}
        <div className="max-w-4xl mx-auto mb-12">
          <div className="bg-white rounded-2xl shadow-xl p-8 border border-pink-100">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-gray-800">Current Season</h2>
              <div className="flex items-center bg-red-100 text-red-800 px-4 py-2 rounded-full">
                <Play className="w-4 h-4 mr-2" />
                <span className="font-semibold">LIVE</span>
              </div>
            </div>
            
            <div className="grid md:grid-cols-3 gap-6">
              <div className="text-center p-6 bg-gradient-to-br from-pink-50 to-rose-50 rounded-xl border border-pink-200">
                <Crown className="w-10 h-10 text-pink-500 mx-auto mb-3" />
                <h3 className="text-xl font-bold text-gray-800">The Bachelor</h3>
                <p className="text-gray-600 mb-2">Season 28</p>
                <p className="text-lg font-semibold text-pink-600">Joey Graziadei</p>
              </div>
              
              <div className="text-center p-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-200">
                <Calendar className="w-10 h-10 text-blue-500 mx-auto mb-3" />
                <h3 className="text-xl font-bold text-gray-800">Episode 8</h3>
                <p className="text-gray-600 mb-2">of 12 Episodes</p>
                <p className="text-lg font-semibold text-blue-600">66% Complete</p>
              </div>
              
              <div className="text-center p-6 bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl border border-green-200">
                <MapPin className="w-10 h-10 text-green-500 mx-auto mb-3" />
                <h3 className="text-xl font-bold text-gray-800">Malta</h3>
                <p className="text-gray-600 mb-2">Current Location</p>
                <p className="text-lg font-semibold text-green-600">Mediterranean</p>
              </div>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="max-w-6xl mx-auto mb-12">
          <h2 className="text-3xl font-bold text-center text-gray-800 mb-8">
            What Makes Us Special
          </h2>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: Heart,
                title: "Fantasy Teams",
                description: "Draft your favorite contestants and compete with friends",
                color: "pink"
              },
              {
                icon: TrendingUp,
                title: "AI Predictions",
                description: "Machine learning powered elimination and winner predictions",
                color: "blue"
              },
              {
                icon: Trophy,
                title: "Live Scoring",
                description: "Real-time points during episodes via WebSocket updates",
                color: "yellow"
              },
              {
                icon: Users,
                title: "Social Features",
                description: "Friend leagues, activity feeds, and live chat",
                color: "green"
              }
            ].map((feature, index) => (
              <div key={index} className="bg-white rounded-xl shadow-lg p-6 border border-gray-100 hover:shadow-xl transition-shadow">
                <div className={`w-12 h-12 bg-${feature.color}-100 rounded-lg flex items-center justify-center mb-4`}>
                  <feature.icon className={`w-6 h-6 text-${feature.color}-600`} />
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">{feature.title}</h3>
                <p className="text-gray-600 text-sm leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Stats */}
        <div className="max-w-4xl mx-auto mb-12">
          <div className="bg-gradient-to-r from-pink-500 to-red-500 rounded-2xl shadow-xl p-8 text-white">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold mb-2">Platform Statistics</h2>
              <p className="text-pink-100">Join thousands of Bachelor fans competing in real-time!</p>
            </div>
            
            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="text-4xl font-bold mb-2">1,247</div>
                <div className="text-pink-200">Active Players</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold mb-2">89</div>
                <div className="text-pink-200">Active Leagues</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold mb-2">25</div>
                <div className="text-pink-200">Contestants Left</div>
              </div>
            </div>
          </div>
        </div>

        {/* Call to Action */}
        <div className="text-center max-w-2xl mx-auto">
          <div className="bg-white rounded-2xl shadow-xl p-8 border border-pink-100">
            <h2 className="text-3xl font-bold text-gray-800 mb-4">Ready to Join?</h2>
            <p className="text-gray-600 mb-6 leading-relaxed">
              Experience the most exciting way to watch The Bachelor! Create your fantasy team, 
              make predictions, and compete with friends in real-time.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button className="bg-pink-500 hover:bg-pink-600 text-white px-8 py-4 rounded-xl font-semibold text-lg transition-colors shadow-lg hover:shadow-xl">
                🌹 Create Your Team
              </button>
              <button className="border-2 border-pink-500 text-pink-500 hover:bg-pink-50 px-8 py-4 rounded-xl font-semibold text-lg transition-colors">
                📊 View Leaderboard
              </button>
            </div>
            
            <div className="mt-6 text-sm text-gray-500">
              <p>✅ Free to play • ✅ Real-time updates • ✅ AI-powered predictions</p>
            </div>
          </div>
        </div>

        {/* Footer Links */}
        <div className="mt-16 text-center">
          <div className="flex flex-wrap justify-center gap-6 text-gray-600">
            <a href="https://bachelor-league-production.up.railway.app/docs" target="_blank" rel="noopener noreferrer" className="hover:text-pink-600 transition-colors">
              📚 API Documentation
            </a>
            <a href="https://bachelor-league-production.up.railway.app/health" target="_blank" rel="noopener noreferrer" className="hover:text-pink-600 transition-colors">
              ❤️ Health Check
            </a>
            <a href="/dashboard" className="hover:text-pink-600 transition-colors">
              🏠 Dashboard
            </a>
          </div>
          
          <div className="mt-8 text-gray-500 text-sm">
            <p>Built with ❤️ for Bachelor Nation • FastAPI + React + PostgreSQL + AI</p>
            <p className="mt-2">
              Backend: <span className="font-mono text-xs">railway.app</span> • 
              Frontend: <span className="font-mono text-xs">vercel.app</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
