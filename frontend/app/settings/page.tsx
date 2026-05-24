'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface FactorySettings {
  llm_model: string;
  llm_fallback_model: string;
  llm_base_url: string;
  pipeline_timeout: number;
  stage_timeout: number;
  max_retry_count: number;
  git_auto_push: boolean;
  webhook_url: string;
  webhook_events: string;
}

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  description: string;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<FactorySettings | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Form state
  const [form, setForm] = useState<Partial<FactorySettings>>({});

  useEffect(() => {
    async function fetchAll() {
      try {
        const [settingsRes, modelsRes] = await Promise.all([
          fetch(`${API_BASE}/settings`),
          fetch(`${API_BASE}/settings/models`),
        ]);
        if (settingsRes.ok) {
          const data = await settingsRes.json();
          setSettings(data);
          setForm(data);
        }
        if (modelsRes.ok) {
          setModels(await modelsRes.json());
        }
      } catch {
        setMessage({ type: 'error', text: 'Failed to load settings. Is the backend running?' });
      } finally {
        setLoading(false);
      }
    }
    fetchAll();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);

    try {
      const res = await fetch(`${API_BASE}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      if (res.ok) {
        const result = await res.json();
        setMessage({ type: 'success', text: `✅ ${result.message}` });
        // Refresh settings
        const refreshRes = await fetch(`${API_BASE}/settings`);
        if (refreshRes.ok) {
          const data = await refreshRes.json();
          setSettings(data);
          setForm(data);
        }
      } else {
        setMessage({ type: 'error', text: 'Failed to save settings' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Network error' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="mb-6">
          <Link href="/" className="text-blue-600 hover:text-blue-700 font-medium">
            ← Home
          </Link>
        </div>

        <h1 className="text-3xl font-bold text-gray-900 mb-8">Factory Settings</h1>

        {message && (
          <div
            className={`mb-6 p-4 rounded-lg border ${
              message.type === 'success'
                ? 'bg-green-50 border-green-200 text-green-800'
                : 'bg-red-50 border-red-200 text-red-800'
            }`}
          >
            {message.text}
          </div>
        )}

        <div className="space-y-8">
          {/* LLM Configuration */}
          <section className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              🤖 LLM Configuration
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Primary Model */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Primary Model
                </label>
                <select
                  value={form.llm_model || ''}
                  onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.provider})
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">Used for code generation</p>
              </div>

              {/* Fallback Model */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Fallback Model
                </label>
                <select
                  value={form.llm_fallback_model || ''}
                  onChange={(e) => setForm({ ...form, llm_fallback_model: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.provider})
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">Used when primary model fails</p>
              </div>

              {/* API Base URL */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  API Base URL
                </label>
                <input
                  type="text"
                  value={form.llm_base_url || ''}
                  onChange={(e) => setForm({ ...form, llm_base_url: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                  placeholder="http://10.190.0.214:8080/v1"
                />
              </div>
            </div>
          </section>

          {/* Pipeline Configuration */}
          <section className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              ⚙️ Pipeline Configuration
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Pipeline Timeout (s)
                </label>
                <input
                  type="number"
                  min="60"
                  max="3600"
                  value={form.pipeline_timeout || 600}
                  onChange={(e) => setForm({ ...form, pipeline_timeout: parseInt(e.target.value) })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">Max total pipeline time</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Stage Timeout (s)
                </label>
                <input
                  type="number"
                  min="30"
                  max="600"
                  value={form.stage_timeout || 180}
                  onChange={(e) => setForm({ ...form, stage_timeout: parseInt(e.target.value) })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">Max time per stage</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Retries
                </label>
                <input
                  type="number"
                  min="0"
                  max="10"
                  value={form.max_retry_count || 3}
                  onChange={(e) => setForm({ ...form, max_retry_count: parseInt(e.target.value) })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">Failed task retry limit</p>
              </div>
            </div>
          </section>

          {/* Integrations */}
          <section className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              🔗 Integrations
            </h2>

            <div className="space-y-6">
              {/* Git */}
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <h3 className="font-medium text-gray-900">Git Auto-Push</h3>
                  <p className="text-sm text-gray-500">Automatically push code to GitHub after delivery</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.git_auto_push || false}
                    onChange={(e) => setForm({ ...form, git_auto_push: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>

              {/* Webhook */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Webhook URL
                </label>
                <input
                  type="url"
                  value={form.webhook_url || ''}
                  onChange={(e) => setForm({ ...form, webhook_url: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                  placeholder="https://your-server.com/webhook"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Receives POST notifications for pipeline events (started, completed, failed)
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Webhook Events
                </label>
                <input
                  type="text"
                  value={form.webhook_events || ''}
                  onChange={(e) => setForm({ ...form, webhook_events: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                  placeholder="pipeline.completed, pipeline.failed (leave empty for all)"
                />
              </div>
            </div>
          </section>

          {/* Save Button */}
          <div className="flex items-center justify-between pt-4">
            <p className="text-sm text-gray-500">
              Changes take effect immediately for new pipelines.
            </p>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving...' : '💾 Save Settings'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
