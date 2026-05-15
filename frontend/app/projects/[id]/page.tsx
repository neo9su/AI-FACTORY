'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  projectsApi,
  type ProjectDetail,
  type AgentRun,
  type TestRun,
} from '@/lib/api';
import { StatusBadge } from '@/components/status-badge';
import { PipelineProgress } from '@/components/pipeline-progress';
import { TaskList } from '@/components/task-list';
import { AgentLogViewer } from '@/components/agent-log-viewer';
import { useWebSocket } from '@/lib/websocket';

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([]);
  const [testRuns, setTestRuns] = useState<TestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAgentLogs, setShowAgentLogs] = useState(false);
  const [showTestResults, setShowTestResults] = useState(false);

  const { messages, isConnected } = useWebSocket(projectId);

  useEffect(() => {
    const fetchProject = async (): Promise<void> => {
      try {
        const [projectData, agentRunsData, testRunsData] = await Promise.all([
          projectsApi.get(projectId),
          projectsApi.getAgentRuns(projectId),
          projectsApi.getTestRuns(projectId),
        ]);
        setProject(projectData);
        setAgentRuns(agentRunsData);
        setTestRuns(testRunsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load project');
      } finally {
        setLoading(false);
      }
    };

    fetchProject();
  }, [projectId]);

  useEffect(() => {
    if (messages.length > 0) {
      const fetchUpdates = async (): Promise<void> => {
        try {
          const [projectData, agentRunsData, testRunsData] = await Promise.all([
            projectsApi.get(projectId),
            projectsApi.getAgentRuns(projectId),
            projectsApi.getTestRuns(projectId),
          ]);
          setProject(projectData);
          setAgentRuns(agentRunsData);
          setTestRuns(testRunsData);
        } catch (err) {
          console.error('Failed to fetch updates:', err);
        }
      };

      fetchUpdates();
    }
  }, [messages, projectId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading project...</p>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Error: {error || 'Project not found'}</p>
          <Link
            href="/projects"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Back to Projects
          </Link>
        </div>
      </div>
    );
  }

  const passedTests = testRuns.filter((t) => t.status === 'passed').length;
  const failedTests = testRuns.filter((t) => t.status === 'failed').length;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link
            href="/projects"
            className="text-blue-600 hover:text-blue-700 font-medium mb-4 inline-block"
          >
            ← Back to Projects
          </Link>
        </div>

        {/* Project Status Card */}
        <div className="bg-white rounded-xl shadow-md p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {project.name}
              </h1>
              <p className="text-gray-600">{project.user_requirement}</p>
              {project.tech_stack && (
                <p className="text-sm text-gray-500 mt-2">
                  <span className="font-semibold">Tech Stack:</span> {project.tech_stack}
                </p>
              )}
            </div>
            <div className="flex flex-col items-end space-y-2">
              <StatusBadge status={project.status} className="text-lg px-4 py-2" />
              <div className="flex items-center space-x-2 text-sm">
                <span
                  className={`w-2 h-2 rounded-full ${
                    isConnected ? 'bg-green-500' : 'bg-gray-400'
                  }`}
                />
                <span className="text-gray-600">
                  {isConnected ? 'Live' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>

          {/* Pipeline Progress */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">
              Pipeline Progress
            </h3>
            <PipelineProgress currentStage={project.status} />
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h4 className="text-sm text-gray-500 mb-1">Total Tasks</h4>
            <p className="text-2xl font-bold text-gray-900">{project.tasks.length}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h4 className="text-sm text-gray-500 mb-1">Agent Runs</h4>
            <p className="text-2xl font-bold text-gray-900">{project.agent_runs_count}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h4 className="text-sm text-gray-500 mb-1">Tests Passed</h4>
            <p className="text-2xl font-bold text-green-600">{passedTests}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h4 className="text-sm text-gray-500 mb-1">Tests Failed</h4>
            <p className="text-2xl font-bold text-red-600">{failedTests}</p>
          </div>
        </div>

        {/* Tasks Section */}
        <div className="bg-white rounded-xl shadow-md p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Tasks</h2>
          <TaskList tasks={project.tasks} />
        </div>

        {/* Agent Logs Section */}
        <div className="bg-white rounded-xl shadow-md p-6 mb-6">
          <button
            onClick={() => setShowAgentLogs(!showAgentLogs)}
            className="w-full flex items-center justify-between mb-4"
          >
            <h2 className="text-xl font-bold text-gray-900">
              Agent Runs ({agentRuns.length})
            </h2>
            <span className="text-blue-600">
              {showAgentLogs ? 'Hide' : 'Show'}
            </span>
          </button>
          {showAgentLogs && <AgentLogViewer agentRuns={agentRuns} />}
        </div>

        {/* Test Results Section */}
        <div className="bg-white rounded-xl shadow-md p-6 mb-6">
          <button
            onClick={() => setShowTestResults(!showTestResults)}
            className="w-full flex items-center justify-between mb-4"
          >
            <h2 className="text-xl font-bold text-gray-900">
              Test Results ({testRuns.length})
            </h2>
            <span className="text-blue-600">
              {showTestResults ? 'Hide' : 'Show'}
            </span>
          </button>
          {showTestResults && (
            <div className="space-y-2">
              {testRuns.length === 0 ? (
                <p className="text-center py-8 text-gray-500">No test runs yet.</p>
              ) : (
                testRuns.map((test) => (
                  <div
                    key={test.id}
                    className="border border-gray-200 rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <h4 className="font-medium text-gray-900">{test.test_type}</h4>
                        <p className="text-sm text-gray-500 font-mono">{test.command}</p>
                      </div>
                      <StatusBadge status={test.status} />
                    </div>
                    {test.error_log && (
                      <div className="mt-2 p-3 bg-red-50 rounded text-sm text-red-800 font-mono overflow-x-auto">
                        {test.error_log}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Delivery Report Link */}
        {project.status === 'delivered' && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
            <h3 className="text-xl font-bold text-green-900 mb-2">
              🎉 Project Delivered!
            </h3>
            <p className="text-green-700 mb-4">
              Your project has been successfully completed.
            </p>
            <Link
              href={`/projects/${projectId}/delivery`}
              className="inline-block px-6 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition-colors"
            >
              View Delivery Report
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
