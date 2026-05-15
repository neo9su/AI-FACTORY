'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  projectsApi,
  type DeliveryReport,
  type Deployment,
  type TestRun,
} from '@/lib/api';

export default function DeliveryReportPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [report, setReport] = useState<DeliveryReport | null>(null);
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [testRuns, setTestRuns] = useState<TestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDeliveryData = async (): Promise<void> => {
      try {
        const [reportData, deploymentData, testRunsData] = await Promise.all([
          projectsApi.getDeliveryReport(projectId),
          projectsApi.getDeployment(projectId).catch(() => null),
          projectsApi.getTestRuns(projectId),
        ]);
        setReport(reportData);
        setDeployment(deploymentData);
        setTestRuns(testRunsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load delivery report');
      } finally {
        setLoading(false);
      }
    };

    fetchDeliveryData();
  }, [projectId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading delivery report...</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">
            Error: {error || 'Delivery report not found'}
          </p>
          <Link
            href={`/projects/${projectId}`}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Back to Project
          </Link>
        </div>
      </div>
    );
  }

  const passedTests = testRuns.filter((t) => t.status === 'passed').length;
  const failedTests = testRuns.filter((t) => t.status === 'failed').length;
  const skippedTests = testRuns.filter((t) => t.status === 'skipped').length;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link
            href={`/projects/${projectId}`}
            className="text-blue-600 hover:text-blue-700 font-medium mb-4 inline-block"
          >
            ← Back to Project
          </Link>
        </div>

        {/* Title Card */}
        <div className="bg-gradient-to-r from-green-500 to-teal-600 rounded-xl shadow-lg p-8 mb-6 text-white">
          <h1 className="text-4xl font-bold mb-2">🎉 Delivery Report</h1>
          <p className="text-green-50 text-lg">
            Project completed successfully on{' '}
            {new Date(report.created_at).toLocaleDateString()}
          </p>
          <div className="mt-4 inline-flex items-center px-4 py-2 bg-white/20 rounded-lg">
            <span className="font-semibold">Status: {report.final_status}</span>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid md:grid-cols-2 gap-4 mb-6">
          {deployment?.preview_url && (
            <a
              href={deployment.preview_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center space-x-2 p-6 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md"
            >
              <span className="text-2xl">🌐</span>
              <span className="font-semibold text-lg">Preview Deployment</span>
            </a>
          )}
          {report.deployment_url && (
            <a
              href={report.deployment_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center space-x-2 p-6 bg-gray-800 text-white rounded-lg hover:bg-gray-900 transition-colors shadow-md"
            >
              <span className="text-2xl">💻</span>
              <span className="font-semibold text-lg">View GitHub Repository</span>
            </a>
          )}
        </div>

        {/* Summary */}
        <div className="bg-white rounded-xl shadow-md p-6 mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Summary</h2>
          <div className="prose max-w-none">
            <p className="text-gray-700 whitespace-pre-wrap">{report.summary}</p>
          </div>
        </div>

        {/* Test Results */}
        <div className="bg-white rounded-xl shadow-md p-6 mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Test Results</h2>
          <div className="grid md:grid-cols-3 gap-4 mb-6">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 className="text-sm text-green-700 font-semibold mb-1">
                Passed Tests
              </h3>
              <p className="text-3xl font-bold text-green-600">{passedTests}</p>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="text-sm text-red-700 font-semibold mb-1">
                Failed Tests
              </h3>
              <p className="text-3xl font-bold text-red-600">{failedTests}</p>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <h3 className="text-sm text-gray-700 font-semibold mb-1">
                Skipped Tests
              </h3>
              <p className="text-3xl font-bold text-gray-600">{skippedTests}</p>
            </div>
          </div>

          {report.passed_tests && Object.keys(report.passed_tests).length > 0 && (
            <div className="mb-4">
              <h3 className="font-semibold text-gray-900 mb-2">
                ✅ Passed Test Suites
              </h3>
              <div className="bg-green-50 rounded-lg p-4">
                <pre className="text-sm text-gray-700 overflow-x-auto">
                  {JSON.stringify(report.passed_tests, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {report.failed_tests && Object.keys(report.failed_tests).length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">
                ❌ Failed Test Suites
              </h3>
              <div className="bg-red-50 rounded-lg p-4">
                <pre className="text-sm text-gray-700 overflow-x-auto">
                  {JSON.stringify(report.failed_tests, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Known Issues */}
        {report.known_issues && (
          <div className="bg-white rounded-xl shadow-md p-6 mb-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              ⚠️ Known Issues
            </h2>
            <div className="prose max-w-none">
              <p className="text-gray-700 whitespace-pre-wrap">{report.known_issues}</p>
            </div>
          </div>
        )}

        {/* Deployment Info */}
        {deployment && (
          <div className="bg-white rounded-xl shadow-md p-6 mb-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Deployment Information
            </h2>
            <div className="space-y-3">
              <div>
                <span className="text-sm font-semibold text-gray-700">
                  Environment:
                </span>
                <p className="text-gray-900">{deployment.environment}</p>
              </div>
              {deployment.preview_url && (
                <div>
                  <span className="text-sm font-semibold text-gray-700">
                    Preview URL:
                  </span>
                  <a
                    href={deployment.preview_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-blue-600 hover:text-blue-700 break-all"
                  >
                    {deployment.preview_url}
                  </a>
                </div>
              )}
              <div>
                <span className="text-sm font-semibold text-gray-700">Status:</span>
                <p className="text-gray-900 capitalize">{deployment.status}</p>
              </div>
              <div>
                <span className="text-sm font-semibold text-gray-700">
                  Deployed At:
                </span>
                <p className="text-gray-900">
                  {new Date(deployment.created_at).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Suggestions */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
          <h2 className="text-xl font-bold text-blue-900 mb-3">💡 Suggestions</h2>
          <ul className="space-y-2 text-blue-800">
            <li>• Review the code in the GitHub repository</li>
            <li>• Test the deployed application thoroughly</li>
            <li>• Address any known issues before production release</li>
            <li>• Set up monitoring and logging for production</li>
            <li>• Configure CI/CD pipelines for future updates</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
