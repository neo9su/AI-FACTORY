'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { projectsApi, type ProjectCreate } from '@/lib/api';

interface TemplateInfo {
  key: string;
  name: string;
  description: string;
  tech_stack: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function NewProjectPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [formData, setFormData] = useState<ProjectCreate & { template?: string }>({
    name: '',
    user_requirement: '',
    goal: '',
    tech_stack: '',
  });

  // Fetch templates on mount
  useEffect(() => {
    fetch(`${API_BASE}/templates`)
      .then((r) => r.json())
      .then((data) => setTemplates(data))
      .catch(() => {});
  }, []);

  const handleTemplateSelect = (key: string) => {
    if (selectedTemplate === key) {
      // Deselect
      setSelectedTemplate('');
      setFormData((prev) => ({ ...prev, tech_stack: '', template: undefined }));
    } else {
      setSelectedTemplate(key);
      const tpl = templates.find((t) => t.key === key);
      if (tpl) {
        setFormData((prev) => ({
          ...prev,
          tech_stack: tpl.tech_stack,
          template: key,
        }));
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    setError(null);

    if (!formData.name.trim()) {
      setError('Project name is required');
      return;
    }
    if (!formData.user_requirement.trim()) {
      setError('Requirements are required');
      return;
    }

    setLoading(true);

    try {
      const project = await projectsApi.create({
        name: formData.name.trim(),
        user_requirement: formData.user_requirement.trim(),
        goal: formData.goal?.trim() || undefined,
        tech_stack: formData.tech_stack?.trim() || undefined,
        template: selectedTemplate || undefined,
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
        <div className="max-w-4xl mx-auto">
          <div className="mb-6">
            <Link
              href="/projects"
              className="text-blue-600 hover:text-blue-700 font-medium"
            >
              ← Back to Projects
            </Link>
          </div>

          <div className="bg-white rounded-xl shadow-md p-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Create New Project
            </h1>
            <p className="text-gray-500 mb-8">
              Describe what you want to build — AI will handle the rest.
            </p>

            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-8">
              {/* Template Selection */}
              {templates.length > 0 && (
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-3">
                    🚀 Start from Template
                    <span className="text-gray-400 font-normal ml-2">(optional)</span>
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {templates.map((tpl) => (
                      <button
                        key={tpl.key}
                        type="button"
                        onClick={() => handleTemplateSelect(tpl.key)}
                        className={`p-4 rounded-lg border-2 text-left transition-all ${
                          selectedTemplate === tpl.key
                            ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                            : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        <div className="font-medium text-gray-900 text-sm mb-1">
                          {tpl.name}
                        </div>
                        <div className="text-xs text-gray-500 line-clamp-2">
                          {tpl.description}
                        </div>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {tpl.tech_stack.split(',').slice(0, 3).map((tech, i) => (
                            <span
                              key={i}
                              className="px-1.5 py-0.5 bg-gray-100 text-gray-600 text-[10px] rounded"
                            >
                              {tech.trim()}
                            </span>
                          ))}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

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
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
                  placeholder="My Awesome Project"
                />
              </div>

              {/* Requirements */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Requirements <span className="text-red-500">*</span>
                </label>
                <textarea
                  required
                  value={formData.user_requirement}
                  onChange={(e) =>
                    setFormData({ ...formData, user_requirement: e.target.value })
                  }
                  rows={6}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Describe what you want to build:&#10;&#10;- User authentication with email/password&#10;- CRUD operations for tasks&#10;- REST API with proper error handling&#10;- Comprehensive test coverage"
                />
                <p className="mt-1.5 text-sm text-gray-500">
                  The more specific you are, the better the output. Include features, constraints, and preferences.
                </p>
              </div>

              {/* Two columns: Goal + Tech Stack */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Project Goal
                  </label>
                  <textarea
                    value={formData.goal}
                    onChange={(e) => setFormData({ ...formData, goal: e.target.value })}
                    rows={3}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Build a production-ready task manager..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Tech Stack
                    {selectedTemplate && (
                      <span className="text-blue-500 font-normal ml-1">(from template)</span>
                    )}
                  </label>
                  <textarea
                    value={formData.tech_stack}
                    onChange={(e) =>
                      setFormData({ ...formData, tech_stack: e.target.value })
                    }
                    rows={3}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Python, FastAPI, pytest..."
                  />
                  <p className="mt-1.5 text-sm text-gray-500">
                    Leave blank for AI to choose.
                  </p>
                </div>
              </div>

              {/* Submit */}
              <div className="flex items-center space-x-4 pt-4 border-t border-gray-100">
                <button
                  type="submit"
                  disabled={loading}
                  className="px-8 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {loading ? (
                    <>
                      <span className="inline-block animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                      Creating...
                    </>
                  ) : (
                    '🚀 Create & Start Pipeline'
                  )}
                </button>
                <Link
                  href="/projects"
                  className="px-6 py-3 text-gray-600 font-medium hover:text-gray-800"
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
