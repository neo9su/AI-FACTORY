'use client';

import { useState } from 'react';
import api from '@/lib/api';

interface ABTestPanelProps {
  productId: string;
  onTestCreated?: (testId: string) => void;
}

export default function ABTestPanel({ productId, onTestCreated }: ABTestPanelProps) {
  const [platform, setPlatform] = useState('xiaohongshu');
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<{
    ab_test_id?: string;
    variants?: Record<string, { title: string; hook: string }>;
    error?: string;
  } | null>(null);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const res = await api.post(`/optimizer/products/${productId}/ab-test`, {
        platform,
      });
      setResult(res.data);
      onTestCreated?.(res.data.ab_test_id);
    } catch (e: any) {
      setResult({ error: e.message || '创建失败' });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="rounded-2xl bg-gradient-to-br from-fuchsia-900/20 to-violet-900/20 border border-fuchsia-500/20 p-5">
      <h3 className="text-sm font-bold text-fuchsia-300 mb-4">🧪 A/B 测试</h3>

      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label className="text-xs text-gray-400 block mb-1">发布平台</label>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
          >
            <option value="xiaohongshu">📕 小红书</option>
            <option value="douyin">🎵 抖音</option>
          </select>
        </div>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="px-4 py-2 rounded-lg bg-fuchsia-600 hover:bg-fuchsia-500 disabled:opacity-50 text-white text-sm font-semibold transition-all"
        >
          {creating ? '生成中...' : '🚀 启动 A/B 测试'}
        </button>
      </div>

      {result && !result.error && (
        <div className="mt-4 space-y-2">
          <p className="text-xs text-emerald-400">
            ✅ 测试已创建（ID: {result.ab_test_id}）
          </p>
          <div className="text-xs text-gray-300">
            {result.variants &&
              Object.entries(result.variants).map(([vid, vdata]) => (
                <div
                  key={vid}
                  className="rounded-lg bg-white/5 border border-white/10 p-2 mt-2"
                >
                  <span className="font-bold text-fuchsia-300">{vid}</span>
                  <p>标题: {vdata.title || '-'}</p>
                  <p>钩子: {vdata.hook || '-'}</p>
                </div>
              ))}
          </div>
        </div>
      )}
      {result?.error && (
        <p className="mt-2 text-xs text-red-400">⚠ {result.error}</p>
      )}
    </div>
  );
}
