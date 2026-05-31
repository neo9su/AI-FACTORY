'use client';

import { useState } from 'react';
import type { ContentProduct } from '@/types/neurotrend';
import api from '@/lib/api';

interface Props {
  product: ContentProduct;
  onClose: () => void;
}

const PLATFORMS = [
  { id: 'douyin', label: '🎵 抖音', color: 'hover:border-black/40' },
  { id: 'xiaohongshu', label: '📕 小红书', color: 'hover:border-red-400/40' },
  { id: 'tiktok', label: '🌐 TikTok', color: 'hover:border-gray-400/40' },
];

// ─── 网站部署表单 ────────────────────────────────────────────────────────

interface DeployForm {
  host: string;
  port: string;
  username: string;
  password: string;
  web_root: string;
}

function WebsiteDeployTab({ product, onDeployed }: { product: ContentProduct; onDeployed: (msg: string) => void }) {
  const [form, setForm] = useState<DeployForm>({
    host: '',
    port: '22',
    username: 'root',
    password: '',
    web_root: '/var/www/html',
  });
  const [deploying, setDeploying] = useState(false);

  const handleDeploy = async () => {
    if (!form.host || !form.password) {
      onDeployed('❌ 请填写服务器 IP 和密码');
      return;
    }
    setDeploying(true);
    try {
      const res = await api.post('/deploy/product', {
        product_id: product.id,
        server: {
          host: form.host,
          port: parseInt(form.port) || 22,
          username: form.username,
          password: form.password,
          web_root: form.web_root,
        },
      });
      const data = res.data;
      if (data.status === 'deploying') {
        onDeployed(`✅ 部署任务已提交！${data.message ?? ''}`);
      } else {
        onDeployed(`⚠️ ${data.message ?? '部署返回未知状态'}`);
      }
    } catch (err) {
      onDeployed(`❌ 部署失败: ${err instanceof Error ? err.message : '请求错误'}`);
    } finally {
      setDeploying(false);
    }
  };

  const field = (label: string, key: keyof DeployForm, placeholder: string, type = 'text') => (
    <div>
      <label className="block text-xs text-gray-400 mb-1">{label}</label>
      <input
        type={type}
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        placeholder={placeholder}
        className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/20 text-sm text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none transition-colors"
      />
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-xl p-3">
        <p className="text-xs text-cyan-300 font-semibold mb-1">💡 推荐使用以下服务商</p>
        <ul className="text-xs text-gray-400 space-y-1">
          <li>• <strong className="text-white">阿里云 ECS</strong> — 新人 ¥9/月，国内访问快 → <a href="https://www.aliyun.com" target="_blank" rel="noopener" className="text-cyan-400 hover:underline">aliyun.com</a></li>
          <li>• <strong className="text-white">腾讯云轻量服务器</strong> — ¥10/月起 → <a href="https://cloud.tencent.com" target="_blank" rel="noopener" className="text-cyan-400 hover:underline">cloud.tencent.com</a></li>
          <li>• <strong className="text-white">Vultr</strong> — $6/月，日本/新加坡节点可免备案 → <a href="https://www.vultr.com" target="_blank" rel="noopener" className="text-cyan-400 hover:underline">vultr.com</a></li>
          <li>• <strong className="text-white">Cloudflare Pages</strong> — 免费托管静态 HTML 页面 → <a href="https://pages.cloudflare.com" target="_blank" rel="noopener" className="text-cyan-400 hover:underline">pages.cloudflare.com</a></li>
        </ul>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {field('服务器 IP 地址', 'host', '例如 123.45.67.89')}
        {field('SSH 端口', 'port', '22', 'number')}
      </div>

      <div className="grid grid-cols-2 gap-3">
        {field('SSH 用户名', 'username', 'root')}
        {field('SSH 密码', 'password', '', 'password')}
      </div>

      {field('网站根目录', 'web_root', '/var/www/html')}

      <button
        onClick={handleDeploy}
        disabled={deploying}
        className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-60 text-sm font-semibold text-white transition-all"
      >
        {deploying ? '⏳ 部署中…' : '🚀 部署到服务器'}
      </button>
    </div>
  );
}

// ─── Main component ──────────────────────────────────────────────────────

export default function PublishDialog({ product, onClose }: Props) {
  const [tab, setTab] = useState<'social' | 'website'>('social');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [publishing, setPublishing] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const togglePlatform = (id: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    );
  };

  const handlePublish = async () => {
    if (selectedPlatforms.length === 0) {
      setStatus('❌ 请至少选择一个平台');
      return;
    }
    setPublishing(true);
    setStatus(null);
    try {
      const res = await api.post('/publish/trigger', {
        product_id: product.id,
        platforms: selectedPlatforms,
      });
      const data = res.data;
      if (data.jobs_created > 0) {
        setStatus(`✅ 已提交 ${data.jobs_created} 个发布任务（${selectedPlatforms.join(', ')}）`);
      } else {
        setStatus('⚠️ 这些平台已有进行中的发布任务，无需重复提交');
      }
    } catch (err) {
      setStatus(`❌ 发布失败: ${err instanceof Error ? err.message : '请求错误'}`);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      <div
        className="relative w-full max-w-lg bg-slate-800 border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 pt-5 pb-3 flex items-center justify-between border-b border-white/10">
          <div>
            <h2 className="text-lg font-bold text-white">🚀 发布产品</h2>
            <p className="text-xs text-gray-400 mt-0.5">{product.title ?? product.product_type}</p>
          </div>
          <button onClick={onClose} className="text-white/40 hover:text-white/80 text-lg">
            ✕
          </button>
        </div>

        {/* Tab selector */}
        <div className="flex border-b border-white/10">
          <button
            onClick={() => setTab('social')}
            className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
              tab === 'social'
                ? 'text-indigo-300 border-b-2 border-indigo-500'
                : 'text-white/40 hover:text-white/70'
            }`}
          >
            📱 社交媒体发布
          </button>
          <button
            onClick={() => setTab('website')}
            className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
              tab === 'website'
                ? 'text-indigo-300 border-b-2 border-indigo-500'
                : 'text-white/40 hover:text-white/70'
            }`}
          >
            🌐 部署到网站
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 max-h-[60vh] overflow-y-auto">
          {tab === 'social' ? (
            <div className="space-y-4">
              <p className="text-sm text-gray-200">
                选择要发布的平台。系统会为你生成适配各平台的营销图文。
              </p>

              <div className="space-y-2">
                {PLATFORMS.map((p) => (
                  <label
                    key={p.id}
                    className={`flex items-center gap-3 cursor-pointer select-none px-4 py-3 rounded-xl border transition-colors ${
                      selectedPlatforms.includes(p.id)
                        ? 'border-indigo-500 bg-indigo-500/20'
                        : 'border-white/10 hover:border-white/30'
                    } ${p.color}`}
                  >
                    <input
                      type="checkbox"
                      className="w-4 h-4 rounded accent-indigo-500"
                      checked={selectedPlatforms.includes(p.id)}
                      onChange={() => togglePlatform(p.id)}
                    />
                    <span className="text-sm font-medium">{p.label}</span>
                  </label>
                ))}
              </div>

              <button
                onClick={handlePublish}
                disabled={publishing}
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-60 text-sm font-semibold text-white transition-all"
              >
                {publishing ? '⏳ 提交中…' : '📤 提交发布'}
              </button>

              {status && (
                <div className={`text-sm px-3 py-2 rounded-lg ${
                  status.startsWith('✅') ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                    : status.startsWith('❌') ? 'bg-red-500/10 text-red-300 border border-red-500/20'
                    : 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
                }`}>
                  {status}
                </div>
              )}
            </div>
          ) : (
            <WebsiteDeployTab product={product} onDeployed={setStatus} />
          )}

          {status && tab === 'website' && (
            <div className={`mt-4 text-sm px-3 py-2 rounded-lg ${
              status.startsWith('✅') ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                : status.startsWith('❌') ? 'bg-red-500/10 text-red-300 border border-red-500/20'
                : 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
            }`}>
              {status}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
