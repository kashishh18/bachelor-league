import React from 'react';

const PredictionAlert: React.FC = () => {
  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <div className="flex">
        <div className="flex-shrink-0">
          <span className="text-yellow-400">⚠️</span>
        </div>
        <div className="ml-3">
          <p className="text-sm text-yellow-700">
            Prediction deadline approaching! Make your picks before the episode starts.
          </p>
        </div>
      </div>
    </div>
  );
};

export default PredictionAlert;
