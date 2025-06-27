import React from 'react';

interface Contestant {
  id: string;
  name: string;
  predictions?: {
    trend?: string;
  };
}

interface PredictionAlertProps {
  contestants: Contestant[];
}

const PredictionAlert: React.FC<PredictionAlertProps> = ({ contestants }) => {
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
          {contestants.length > 0 && (
            <p className="text-xs text-yellow-600 mt-1">
              {contestants.length} contestant(s) with trending predictions
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default PredictionAlert;
