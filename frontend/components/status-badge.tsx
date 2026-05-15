import { cn } from '@/lib/utils';

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const statusColors: Record<string, string> = {
  // Project statuses
  created: 'bg-gray-100 text-gray-800',
  requirement_analyzing: 'bg-blue-100 text-blue-800',
  planning: 'bg-indigo-100 text-indigo-800',
  developing: 'bg-purple-100 text-purple-800',
  testing: 'bg-yellow-100 text-yellow-800',
  fixing: 'bg-orange-100 text-orange-800',
  reviewing: 'bg-cyan-100 text-cyan-800',
  deploying: 'bg-teal-100 text-teal-800',
  delivered: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  blocked_by_gate: 'bg-pink-100 text-pink-800',

  // Task statuses
  pending: 'bg-gray-100 text-gray-800',
  running: 'bg-blue-100 text-blue-800',
  passed: 'bg-green-100 text-green-800',
  completed: 'bg-green-100 text-green-800',
  retrying: 'bg-yellow-100 text-yellow-800',
  blocked: 'bg-red-100 text-red-800',

  // Agent/Test statuses
  success: 'bg-green-100 text-green-800',
  timeout: 'bg-orange-100 text-orange-800',
  skipped: 'bg-gray-100 text-gray-800',
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const colorClass = statusColors[status.toLowerCase()] || 'bg-gray-100 text-gray-800';
  const displayText = status.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());

  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        colorClass,
        className
      )}
    >
      {displayText}
    </span>
  );
}
