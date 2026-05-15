'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { projectsApi, type ProjectCreate } from '@/lib/api';

export default function NewProjectPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<ProjectCreate & {
    acceptanceCriteria?: string;
    maxRetries?: number;
    allowAutoDeploy?: boolean;
    allowProductionRelease?: boolean;
    maxBudgetUsd?: number;
  }>({
    name: '',
    user_requirement: '',
    goal: '',
    tech_stack: '',
    acceptanceCriteria: '',
    maxRetries: 3,
    allowAutoDeploy: false,
    allowProductionRelease: false,
    maxBudgetUsd: undefined,
  });

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const project = await projectsApi.create({
        name: formData.name,
        user_requirement: formData.user_requirement,
        goal: formData.goal || undefined,
        tech_stack: formData.tech_stack || undefined,
      });

      await projectsApi.start(project.id);
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-3xl mx-auto">
          <div className="mb-6">
            <Link
              href="/projects"
              className="text-blue-600 hover:text-blue-700 font-medium"
            >
              ← Back to Projects
            </Link>
          </div>

          <div className="bg-white rounded-xl shadow-md p-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-6">
              Create New Project
            </h1>

            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Project Name */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Project Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="My Awesome Project"
                />
              </div>

              {/* Project Goal */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Project Goal <span className="text-red-500">*</span>
                </label>
                <textarea
                  required
                  value={formData.goal}
                  onChange={(e) => setFormData({ ...formData, goal: e.target.value })}
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Build a task management app for teams..."
                />
              </div>

              {/* Functional Requirements */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Functional Requirements <span className="text-red-500">*</span>
                </label>
                <textarea
                  required
                  value={formData.user_requirement}
                  onChange={(e) =>
                    setFormData({ ...formData, user_requirement: e.target.value })
                  }
                  rows={6}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="- User authentication with email/password&#10;- Create, edit, and delete tasks&#10;- Assign tasks to team members&#10;- Real-time updates..."
                />
                <p className="mt-1 text-sm text-gray-500">
                  Describe the features and functionality you need.
                </p>
              </div>

              {/* Tech Stack Preference */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Tech Stack Preference
                </label>
                <input
                  type="text"
                  value={formData.tech_stack}
                  onChange={(e) =>
                    setFormData({ ...formData, tech_stack: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="React, Node.js, PostgreSQL..."
                />
                <p className="mt-1 text-sm text-gray-500">
                  Optional. Leave blank for AI to decide.
                </p>
              </div>

              {/* Acceptance Criteria */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Acceptance Criteria
                </label>
                <textarea
                  value={formData.acceptanceCriteria}
                  onChange={(e) =>
                    setFormData({ ...formData, acceptanceCriteria: e.target.value })
                  }
                  rows={4}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="- All tests must pass&#10;- Load time < 2s&#10;- Mobile responsive..."
                />
              </div>

              {/* Max Retries */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Max Retries
                </label>
                <input
                  type="number"
                  min="0"
                  max="10"
                  value={formData.maxRetries}
                  onChange={(e) =>
                    setFormData({ ...formData, maxRetries: parseInt(e.target.value) })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p className="mt-1 text-sm text-gray-500">
                  Number of times to retry failed tasks (default: 3).
                </p>
              </div>

              {/* Max Budget */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Max Budget (USD)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.maxBudgetUsd || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      maxBudgetUsd: e.target.value ? parseFloat(e.target.value) : undefined,
                    })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="100.00"
                />
                <p className="mt-1 text-sm text-gray-500">
                  Optional. AI will stop if estimated cost exceeds this amount.
                </p>
              </div>

              {/* Checkboxes */}
              <div className="space-y-3">
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={formData.allowAutoDeploy}
                    onChange={(e) =>
                      setFormData({ ...formData, allowAutoDeploy: e.target.checked })
                    }
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">
                    Allow Auto Deploy to preview environment
                  </span>
                </label>

                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={formData.allowProductionRelease}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        allowProductionRelease: e.target.checked,
                      })
                    }
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">
                    Allow Production Release (requires manual approval)
                  </span>
                </label>
              </div>

              {/* Submit Button */}
              <div className="flex items-center space-x-4 pt-4">
                <button
                  type="submit"
                  disabled={loading}
                  className="px-8 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {loading ? 'Creating...' : 'Create Project'}
                </button>
                <Link
                  href="/projects"
                  className="px-6 py-3 bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition-colors"
                >
                  Cancel
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
