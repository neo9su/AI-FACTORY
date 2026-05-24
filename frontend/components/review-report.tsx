'use client';

import { useEffect, useState } from 'react';
import { projectsApi, type ReviewReport } from '@/lib/api';

interface ReviewReportViewProps {
  projectId: string;
}

const SEVERITY_STYLES: Record<string, { bg: string; text: string; badge: string }> = {
  critical: { bg: 'bg-red-50', text: 'text-red-800', badge: 'bg-red-600 text-white' },
  high: { bg: 'bg-orange-50', text: 'text-orange-800', badge: 'bg-orange-500 text-white' },
  medium: { bg: 'bg-yellow-50', text: 'text-yellow-800', badge: 'bg-yellow-500 text-white' },
  low: { bg: 'bg-blue-50', text: 'text-blue-800', badge: 'bg-blue-500 text-white' },
};

export function ReviewReportView({ projectId }: ReviewReportViewProps) {
  const [report, setReport] = useState<ReviewReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReview = async (): Promise<void> => {
      try {
        const data = await projectsApi.getReview(projectId);
        setReport(data);
        setError(null);
      } catch {
        setError('No review report available');
      } finally {
        setLoading(false);
      }
    };
    fetchReview();
  }, [projectId]);

  if (loading) {
    return <div className="text-center py-4 text-gray-500">Loading review...</div>;
  }

  if (error || !report) {
    return (
      <div className="text-center py-8 text-gray-400">
        {error || 'No review report available'}
      </div>
    );
  }

  const { review } = report;
  const scoreColor =
    review.score >= 80
      ? 'text-green-600'
      : review.score >= 60
        ? 'text-yellow-600'
        : 'text-red-600';

  return (
    <div className="space-y-6">
      {/* Score Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="text-center">
            <div className={`text-4xl font-bold ${scoreColor}`}>
              {review.score}
            </div>
            <div className="text-xs text-gray-500">/ 100</div>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span
                className={`px-2 py-1 rounded text-sm font-semibold ${
                  review.passed
                    ? 'bg-green-100 text-green-700'
                    : 'bg-red-100 text-red-700'
                }`}
              >
                {review.passed ? '✅ PASSED' : '❌ ISSUES FOUND'}
              </span>
            </div>
            <p className="text-sm text-gray-600 mt-1">{review.summary}</p>
          </div>
        </div>
      </div>

      {/* Issues */}
      {review.issues.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-3">
            Issues ({review.issues.length})
          </h4>
          <div className="space-y-2">
            {review.issues.map((issue, idx) => {
              const style = SEVERITY_STYLES[issue.severity] || SEVERITY_STYLES.low;
              return (
                <div
                  key={idx}
                  className={`p-3 rounded-lg ${style.bg} border border-opacity-20`}
                >
                  <div className="flex items-start space-x-3">
                    <span
                      className={`text-xs px-2 py-0.5 rounded font-semibold uppercase ${style.badge}`}
                    >
                      {issue.severity}
                    </span>
                    <div className="flex-1">
                      <p className={`text-sm font-medium ${style.text}`}>
                        {issue.description}
                      </p>
                      <div className="flex items-center space-x-3 mt-1 text-xs text-gray-500">
                        <span className="font-mono">
                          {issue.file}
                          {issue.line ? `:${issue.line}` : ''}
                        </span>
                        <span className="bg-gray-200 px-1.5 py-0.5 rounded">
                          {issue.category}
                        </span>
                      </div>
                      {issue.suggestion && (
                        <p className="text-xs text-gray-600 mt-1 italic">
                          💡 {issue.suggestion}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Suggestions */}
      {review.suggestions.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-3">
            Suggestions
          </h4>
          <ul className="space-y-2">
            {review.suggestions.map((suggestion, idx) => (
              <li
                key={idx}
                className="flex items-start space-x-2 text-sm text-gray-700"
              >
                <span className="text-blue-500 mt-0.5">•</span>
                <span>{suggestion}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
