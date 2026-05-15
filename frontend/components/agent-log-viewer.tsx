'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { StatusBadge } from './status-badge';
import type { AgentRun } from '@/lib/api';

interface AgentLogViewerProps {
  agentRuns: AgentRun[];
}

export function AgentLogViewer({ agentRuns }: AgentLogViewerProps) {
  const [expandedRuns, setExpandedRuns] = useState<Set<string>>(new Set());

  const toggleRun = (id: string): void => {
    setExpandedRuns((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  if (agentRuns.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No agent runs yet.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {agentRuns.map((run) => {
        const isExpanded = expandedRuns.has(run.id);
        const duration = run.finished_at
          ? Math.round(
              (new Date(run.finished_at).getTime() -
                new Date(run.started_at).getTime()) /
                1000
            )
          : null;

        return (
          <div
            key={run.id}
            className="border border-gray-200 rounded-lg overflow-hidden"
          >
            <button
              onClick={() => toggleRun(run.id)}
              className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center space-x-3">
                {isExpanded ? (
                  <ChevronDown className="w-5 h-5 text-gray-500" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-gray-500" />
                )}
                <div className="text-left">
                  <h4 className="font-medium text-gray-900">{run.agent_name}</h4>
                  <p className="text-sm text-gray-500">
                    Started: {new Date(run.started_at).toLocaleString()}
                    {duration !== null && ` • Duration: ${duration}s`}
                  </p>
                </div>
              </div>
              <StatusBadge status={run.status} />
            </button>
            {isExpanded && (
              <div className="p-4 bg-white border-t border-gray-200">
                <div className="space-y-4">
                  {run.task_id && (
                    <div>
                      <h5 className="text-sm font-semibold text-gray-700 mb-1">
                        Task ID
                      </h5>
                      <p className="text-sm text-gray-600 font-mono">
                        {run.task_id}
                      </p>
                    </div>
                  )}
                  <div>
                    <h5 className="text-sm font-semibold text-gray-700 mb-1">
                      Run ID
                    </h5>
                    <p className="text-sm text-gray-600 font-mono">{run.id}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
