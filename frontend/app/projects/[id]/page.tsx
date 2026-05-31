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
import { LiveActivityFeed } from '@/components/live-activity-feed';
import { CodePreview } from '@/components/code-preview';
import { ReviewReportView } from '@/components/review-report';
import { useWebSocket } from '@/lib/websocket';

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([]);
  const [testRuns, setTestRuns] = useState<TestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'activity' | 'code' | 'tests' | 'review' | 'agents'>('activity');
  const [rerunning, setRerunning] = useState(false);

  const { messages, lastEvent, isConnected } = useWebSocket(projectId);

  const handleRerun = async () => {
    if (!project) return;
    if (!confirm(`Restart pipeline for "${project.name}"? This will reset the project to "created" status and start a new run.`)) return;
    setRerunning(true);
    try {
      await projectsApi.rerun(projectId);
      // Reload page to reflect new status
      window.location.reload();
    } catch (err) {
      alert('Failed to restart: ' + (err instanceof Error ? err.message : 'Unknown error'));
      setRerunning(false);
    }
  };

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

  // Re-fetch on WebSocket events
  useEffect(() => {
    if (!lastEvent) return;

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
      } catch {
        // Silent fail on update
      }
    };

    fetchUpdates();
  }, [lastEvent, projectId]);

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

  const tabs = [
    { key: 'activity', label: '🔴 Live Activity', count: messages.length },
    { key: 'code', label: '📄 Code', count: null },
    { key: 'tests', label: '🧪 Tests', count: testRuns.length },
    { key: 'review', label: '🔍 Review', count: null },
    { key: 'agents', label: '🤖 Agents', count: agentRuns.length },
  ] as const;

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
              {/* Rerun button for terminal-state projects */}
              {(project.status === 'failed' || project.status === 'delivered') && (
                <button
                  onClick={handleRerun}
                  disabled={rerunning}
                  className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-all ${
                    rerunning
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : project.status === 'failed'
                        ? 'bg-red-100 text-red-700 hover:bg-red-200 hover:text-red-800'
                        : 'bg-green-100 text-green-700 hover:bg-green-200 hover:text-green-800'
                  }`}
                >
                  {rerunning ? '⟳ Restarting...' : '🔄 Rerun Pipeline'}
                </button>
              )}
              <div className="flex items-center space-x-2 text-sm">
                <span
                  className={`w-2 h-2 rounded-full ${
                    isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
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

        {/* Tabbed Content */}
        <div className="bg-white rounded-xl shadow-md overflow-hidden mb-6">
          {/* Tab Header */}
          <div className="flex border-b border-gray-200 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-6 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab.key
                    ? 'border-b-2 border-blue-600 text-blue-600 bg-blue-50/50'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                {tab.label}
                {tab.count !== null && tab.count > 0 && (
                  <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-gray-200 text-gray-700">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === 'activity' && (
              <LiveActivityFeed events={messages} isConnected={isConnected} />
            )}
            {activeTab === 'code' && (
              <CodePreview projectId={projectId} />
            )}
            {activeTab === 'tests' && (
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
                        <div className="mt-2 p-3 bg-red-50 rounded text-sm text-red-800 font-mono overflow-x-auto whitespace-pre-wrap">
                          {test.error_log}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
            {activeTab === 'review' && (
              <ReviewReportView projectId={projectId} />
            )}
            {activeTab === 'agents' && (
              <AgentLogViewer agentRuns={agentRuns} />
            )}
          </div>
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
