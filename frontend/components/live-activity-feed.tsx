'use client';

import { type WSEvent } from '@/lib/websocket';

interface LiveActivityFeedProps {
  events: WSEvent[];
  isConnected: boolean;
}

const EVENT_ICONS: Record<string, string> = {
  project_status: '🔄',
  task_update: '📋',
  agent_log: '🤖',
  test_result: '🧪',
  deployment_update: '🚀',
  pipeline_complete: '🎉',
};

const SEVERITY_COLORS: Record<string, string> = {
  info: 'text-blue-600 bg-blue-50',
  warning: 'text-yellow-700 bg-yellow-50',
  error: 'text-red-600 bg-red-50',
};

export function LiveActivityFeed({ events, isConnected }: LiveActivityFeedProps) {
  if (events.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        <div className="flex items-center justify-center space-x-2 mb-2">
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
            }`}
          />
          <span className="text-sm">
            {isConnected ? 'Waiting for events...' : 'Connecting...'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-96 overflow-y-auto">
      {events
        .slice()
        .reverse()
        .map((event, idx) => {
          const icon = EVENT_ICONS[event.type] || '📌';
          const level = (event.level as string) || 'info';
          const colorClass = SEVERITY_COLORS[level] || 'text-gray-700 bg-gray-50';

          return (
            <div
              key={idx}
              className={`flex items-start space-x-3 p-3 rounded-lg ${colorClass} transition-all`}
            >
              <span className="text-lg flex-shrink-0">{icon}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-semibold uppercase tracking-wide opacity-70">
                    {event.type.replace(/_/g, ' ')}
                  </span>
                  {typeof event.agent_name === 'string' && (
                    <span className="text-xs bg-white/50 px-2 py-0.5 rounded font-mono">
                      {event.agent_name}
                    </span>
                  )}
                </div>
                <p className="text-sm mt-0.5 break-words">
                  {(event.message as string) ||
                    (event.status as string) ||
                    String(event.type)}
                </p>
              </div>
            </div>
          );
        })}
    </div>
  );
}
