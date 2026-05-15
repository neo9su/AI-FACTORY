'use client';

import { cn } from '@/lib/utils';

interface PipelineProgressProps {
  currentStage: string;
  className?: string;
}

const stages = [
  { key: 'created', label: 'Created' },
  { key: 'requirement_analyzing', label: 'Analyzing' },
  { key: 'planning', label: 'Planning' },
  { key: 'developing', label: 'Developing' },
  { key: 'testing', label: 'Testing' },
  { key: 'reviewing', label: 'Reviewing' },
  { key: 'deploying', label: 'Deploying' },
  { key: 'delivered', label: 'Delivered' },
];

export function PipelineProgress({ currentStage, className }: PipelineProgressProps) {
  const currentIndex = stages.findIndex((s) => s.key === currentStage.toLowerCase());
  const isFailed = currentStage.toLowerCase() === 'failed';
  const isBlocked = currentStage.toLowerCase() === 'blocked_by_gate';

  return (
    <div className={cn('w-full', className)}>
      <div className="flex items-center justify-between">
        {stages.map((stage, index) => {
          const isCompleted = index < currentIndex;
          const isCurrent = index === currentIndex;
          const isPending = index > currentIndex;

          return (
            <div key={stage.key} className="flex-1 flex items-center">
              <div className="flex flex-col items-center flex-1">
                <div
                  className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-colors',
                    isCompleted && 'bg-green-500 text-white',
                    isCurrent && !isFailed && !isBlocked && 'bg-blue-500 text-white',
                    isCurrent && isFailed && 'bg-red-500 text-white',
                    isCurrent && isBlocked && 'bg-yellow-500 text-white',
                    isPending && 'bg-gray-200 text-gray-500'
                  )}
                >
                  {isCompleted ? '✓' : index + 1}
                </div>
                <span
                  className={cn(
                    'mt-2 text-xs text-center',
                    isCurrent ? 'font-semibold text-gray-900' : 'text-gray-500'
                  )}
                >
                  {stage.label}
                </span>
              </div>
              {index < stages.length - 1 && (
                <div
                  className={cn(
                    'flex-1 h-1 mx-2 transition-colors',
                    isCompleted ? 'bg-green-500' : 'bg-gray-200'
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
      {(isFailed || isBlocked) && (
        <div className="mt-4 p-3 rounded-lg bg-red-50 text-red-800 text-sm">
          {isFailed && '⚠️ Pipeline failed. Check logs for details.'}
          {isBlocked && '🚫 Pipeline blocked by gatekeeper. Manual approval required.'}
        </div>
      )}
    </div>
  );
}
