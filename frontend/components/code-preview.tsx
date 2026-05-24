'use client';

import { useEffect, useState } from 'react';
import { projectsApi, type WorkspaceFile, type FileContent } from '@/lib/api';

interface CodePreviewProps {
  projectId: string;
}

export function CodePreview({ projectId }: CodePreviewProps) {
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<FileContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [contentLoading, setContentLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchFiles = async (): Promise<void> => {
      try {
        const data = await projectsApi.getFiles(projectId);
        setFiles(data);
        setError(null);
      } catch {
        setError('No workspace files found');
      } finally {
        setLoading(false);
      }
    };
    fetchFiles();
  }, [projectId]);

  const handleFileSelect = async (filePath: string): Promise<void> => {
    setSelectedFile(filePath);
    setContentLoading(true);
    try {
      const content = await projectsApi.getFileContent(projectId, filePath);
      setFileContent(content);
    } catch {
      setFileContent(null);
    } finally {
      setContentLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-4 text-gray-500">Loading files...</div>;
  }

  if (error || files.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        No generated files yet.
      </div>
    );
  }

  const getFileIcon = (ext: string): string => {
    const icons: Record<string, string> = {
      '.py': '🐍',
      '.ts': '📘',
      '.tsx': '⚛️',
      '.js': '📒',
      '.json': '📋',
      '.toml': '⚙️',
      '.yaml': '⚙️',
      '.yml': '⚙️',
      '.md': '📝',
      '.txt': '📄',
      '.go': '🐹',
      '.rs': '🦀',
    };
    return icons[ext] || '📄';
  };

  return (
    <div className="flex flex-col md:flex-row gap-4">
      {/* File Tree */}
      <div className="md:w-64 flex-shrink-0 border border-gray-200 rounded-lg overflow-hidden">
        <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
          <h4 className="text-sm font-semibold text-gray-700">
            Files ({files.length})
          </h4>
        </div>
        <div className="max-h-96 overflow-y-auto">
          {files.map((file) => (
            <button
              key={file.path}
              onClick={() => handleFileSelect(file.path)}
              className={`w-full text-left px-4 py-2 text-sm hover:bg-blue-50 transition-colors flex items-center space-x-2 ${
                selectedFile === file.path
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-700'
              }`}
            >
              <span>{getFileIcon(file.extension)}</span>
              <span className="truncate">{file.path}</span>
              <span className="text-xs text-gray-400 ml-auto flex-shrink-0">
                {file.size < 1024
                  ? `${file.size}B`
                  : `${(file.size / 1024).toFixed(1)}KB`}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Code Content */}
      <div className="flex-1 border border-gray-200 rounded-lg overflow-hidden">
        {!selectedFile ? (
          <div className="flex items-center justify-center h-64 text-gray-400">
            Select a file to preview
          </div>
        ) : contentLoading ? (
          <div className="flex items-center justify-center h-64 text-gray-400">
            Loading...
          </div>
        ) : fileContent ? (
          <div>
            <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
              <span className="text-sm font-mono text-gray-700">
                {fileContent.path}
              </span>
              <span className="text-xs text-gray-500">
                {fileContent.lines} lines
              </span>
            </div>
            <pre className="p-4 text-sm font-mono overflow-x-auto max-h-[500px] overflow-y-auto bg-gray-900 text-gray-100">
              <code>{fileContent.content}</code>
            </pre>
          </div>
        ) : (
          <div className="flex items-center justify-center h-64 text-red-400">
            Failed to load file
          </div>
        )}
      </div>
    </div>
  );
}
