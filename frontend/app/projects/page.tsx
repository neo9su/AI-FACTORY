'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { projectsApi, type Project } from '@/lib/api';
import { StatusBadge } from '@/components/status-badge';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProjects = async (): Promise<void> => {
      try {
        const data = await projectsApi.list();
        setProjects(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load projects');
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading projects...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Error: {error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-4xl font-bold text-gray-900">Projects</h1>
          <Link
            href="/projects/new"
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-semibold"
          >
            + Create Project
          </Link>
        </div>

        {projects.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-xl shadow-sm">
            <p className="text-gray-500 text-lg mb-6">No projects yet</p>
            <Link
              href="/projects/new"
              className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Create Your First Project
            </Link>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.id}`}
                className="block bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow p-6"
              >
                <div className="flex items-start justify-between mb-4">
                  <h2 className="text-xl font-semibold text-gray-900 flex-1">
                    {project.name}
                  </h2>
                  <StatusBadge status={project.status} />
                </div>
                <p className="text-gray-600 text-sm mb-4 line-clamp-3">
                  {project.user_requirement}
                </p>
                {project.tech_stack && (
                  <div className="mb-4">
                    <span className="text-xs text-gray-500 font-semibold">
                      Tech Stack:
                    </span>
                    <p className="text-sm text-gray-700">{project.tech_stack}</p>
                  </div>
                )}
                <div className="flex items-center justify-between text-xs text-gray-500 pt-4 border-t border-gray-100">
                  <span>
                    Created: {new Date(project.created_at).toLocaleDateString()}
                  </span>
                  <span className="text-blue-600 hover:text-blue-700 font-medium">
                    View Details →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
