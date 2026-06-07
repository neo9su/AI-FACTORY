'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { videoProjectsApi } from '@/lib/api';

export default function NewVideoProjectPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
  });

  const handleFileSelect = (file: File | null) => {
    if (!file) return;
    // Video file validation
    const validTypes = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm', 'video/x-matroska'];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(mp4|mov|avi|webm|mkv)$/i)) {
      setError('仅支持 MP4/MOV/AVI/WEBM/MKV 格式');
      return;
    }
    // Size check (2GB limit)
    if (file.size > 2 * 1024 * 1024 * 1024) {
      setError('文件大小超过 2GB 限制');
      return;
    }
    setSelectedFile(file);
    setError(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFileSelect(e.dataTransfer.files[0]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.title.trim()) {
      setError('请填写项目名称');
      return;
    }

    setLoading(true);

    try {
      const form = new FormData();
      form.append('title', formData.title.trim());
      if (formData.description.trim()) form.append('description', formData.description.trim());
      if (selectedFile) form.append('source', selectedFile);

      const project = await videoProjectsApi.create(form);
      router.push(`/video-projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
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
              href="/video-projects"
              className="text-blue-600 hover:text-blue-700 font-medium"
            >
              ← 返回视频项目列表
            </Link>
          </div>

          <div className="bg-white rounded-xl shadow-md p-8">
            <h1 className="text-2xl font-bold text-gray-900 mb-6">新建视频项目</h1>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  项目名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="例如：洗衣机清洁剂带货视频 #1"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 placeholder-gray-400"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  项目描述
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="可选：描述视频内容和生产要求"
                  rows={3}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 placeholder-gray-400"
                />
              </div>

              {/* File Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  源视频文件
                </label>
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                    dragOver
                      ? 'border-blue-500 bg-blue-50'
                      : selectedFile
                        ? 'border-green-400 bg-green-50'
                        : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/mp4,video/quicktime,video/webm,video/x-matroska,.mp4,.mov,.avi,.webm,.mkv"
                    className="hidden"
                    onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
                  />
                  {selectedFile ? (
                    <div>
                      <span className="text-4xl">🎬</span>
                      <p className="mt-3 font-medium text-green-700">{selectedFile.name}</p>
                      <p className="text-sm text-gray-500">
                        {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB
                      </p>
                      <p className="text-sm text-blue-600 mt-2">点击更换文件</p>
                    </div>
                  ) : (
                    <div>
                      <span className="text-4xl">📁</span>
                      <p className="mt-3 font-medium text-gray-700">
                        拖拽视频文件到此处，或点击选择
                      </p>
                      <p className="text-sm text-gray-500 mt-1">
                        支持 MP4/MOV/AVI/WEBM/MKV，最大 2GB
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Preview Pipeline */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">生产管线流程</h3>
                <div className="flex items-center justify-between">
                  {[
                    { emoji: '💧', name: '去水印' },
                    { emoji: '🎙️', name: '配音' },
                    { emoji: '🔄', name: '换脸' },
                    { emoji: '👄', name: '唇形同步' },
                    { emoji: '✨', name: '去重处理' },
                  ].map((stage, i) => (
                    <div key={stage.name} className="flex items-center">
                      <div className="text-center">
                        <div className="w-12 h-12 bg-white rounded-full shadow-sm flex items-center justify-center mx-auto">
                          <span className="text-xl">{stage.emoji}</span>
                        </div>
                        <p className="text-xs text-gray-600 mt-1">{stage.name}</p>
                      </div>
                      {i < 4 && <span className="text-gray-300 mx-2">→</span>}
                    </div>
                  ))}
                </div>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
                  {error}
                </div>
              )}

              <div className="flex items-center space-x-4">
                <button
                  type="submit"
                  disabled={loading}
                  className={`flex-1 px-6 py-3 text-white font-semibold rounded-lg transition-colors ${
                    loading
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {loading ? '创建中...' : '创建项目并开始生产'}
                </button>
                <Link
                  href="/video-projects"
                  className="px-6 py-3 text-gray-700 font-medium rounded-lg border border-gray-300 hover:bg-gray-50"
                >
                  取消
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
