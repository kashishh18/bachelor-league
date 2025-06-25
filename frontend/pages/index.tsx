import React from 'react';

export default function Home() {
  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>🌹 Bachelor Fantasy League</h1>
      <p>Welcome to the Bachelor Fantasy League Platform!</p>
      <p>Backend Status: <a href="http://localhost:8000/health" target="_blank">Check API Health</a></p>
      <div style={{ marginTop: '2rem' }}>
        <h2>Coming Soon:</h2>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          <li>📊 Real-time Contestant Predictions</li>
          <li>🏆 Fantasy Team Management</li>
          <li>📡 Live Episode Scoring</li>
          <li>👥 Friend Leagues</li>
        </ul>
      </div>
    </div>
  );
}
