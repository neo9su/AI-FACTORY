'use client';

import { StatusBadge } from './status-badge';
import type { Task } from '@/lib/api';

interface TaskListProps {
  tasks: Task[];
}

const statusIcons: Record<string, string> = {
  pending: '⏳',
  running: '▶️',
  passed: '✅',
  failed: '❌',
  retrying: '🔄',
  blocked: '🚫',
  completed: '✅',
};

export function TaskList({ tasks }: TaskListProps) {
  if (tasks.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No tasks yet. Pipeline will create tasks automatically.
      </div>
    );
  }

  const sortedTasks = [...tasks].sort((a, b) => b.priority - a.priority);

  return (
    <div className="space-y-2">
      {sortedTasks.map((task) => (
        <div
          key={task.id}
          className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
        >
          <div className="flex items-center space-x-3 flex-1">
            <span className="text-2xl">
              {statusIcons[task.status.toLowerCase()] || '📋'}
            </span>
            <div className="flex-1">
              <h4 className="font-medium text-gray-900">{task.title}</h4>
              {task.role && (
                <p className="text-sm text-gray-500">Role: {task.role}</p>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className="text-sm text-gray-500 px-2 py-1 bg-gray-100 rounded">
              Priority: {task.priority}
            </span>
            <StatusBadge status={task.status} />
          </div>
        </div>
      ))}
    </div>
  );
}
