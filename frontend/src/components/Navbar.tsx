import React from 'react';

const Navbar: React.FC = () => {
  return (
    <nav className="bg-rose-600 text-white p-4">
      <div className="container mx-auto flex justify-between items-center">
        <h1 className="text-xl font-bold">🌹 Bachelor League</h1>
        <div className="space-x-4">
          <a href="/dashboard" className="hover:text-rose-200">Dashboard</a>
          <a href="/leaderboard" className="hover:text-rose-200">Leaderboard</a>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
