'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';
import { type OpportunityReport, EMOTION_COLORS } from '@/types/neurotrend';

interface OpportunityCardProps {
  opportunity: OpportunityReport;
  className?: string;
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.max(0, Math.round(value * 10)));
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-500">
        <span>{label}</span>
        <span className="font-semibold text-gray-700">{value.toFixed(1)}</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-gray-100">
        <div
          className="h-1.5 rounded-full bg-gradient-to-r from-blue-400 to-indigo-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function OpportunityCard({ opportunity, className }: OpportunityCardProps) {
  const {
    id,
    topic,
    core_emotions,
    roi_score,
    automation_score,
    best_product,
  } = opportunity;

  return (
    <div
      className={cn(
        'flex flex-col bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow border border-gray-100 p-5 gap-4',
        className,
      )}
    >
      {/* Title */}
      <div>
        <h2 className="text-lg font-bold text-gray-900 line-clamp-2 leading-snug">
          {topic}
        </h2>
      </div>

      {/* Emotion tags */}
      {core_emotions.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {core_emotions.map((emotion) => {
            const colorClass =
              EMOTION_COLORS[emotion.toLowerCase()] ?? 'bg-gray-400';
            return (
              <span
                key={emotion}
                className={cn(
                  'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium text-white',
                  colorClass,
                )}
              >
                {emotion.replace(/_/g, ' ')}
              </span>
            );
          })}
        </div>
      )}

      {/* Scores */}
      <div className="space-y-2">
        <ScoreBar label="ROI 评分" value={roi_score} />
        <ScoreBar label="自动化评分" value={automation_score} />
      </div>

      {/* Best product suggestion */}
      {best_product && (
        <div className="rounded-lg bg-indigo-50 px-3 py-2">
          <p className="text-xs text-indigo-500 font-semibold uppercase tracking-wide mb-0.5">
            最佳产品建议
          </p>
          <p className="text-sm text-indigo-800 font-medium line-clamp-1">
            {best_product}
          </p>
        </div>
      )}

      {/* CTA */}
      <div className="mt-auto pt-1">
        <Link
          href={`/opportunities/${id}`}
          className="block w-full text-center px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 active:bg-indigo-800 transition-colors"
        >
          查看详情 →
        </Link>
      </div>
    </div>
  );
}
