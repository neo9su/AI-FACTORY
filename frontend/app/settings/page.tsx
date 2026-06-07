'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface FactorySettings {
  llm_provider: string;
  llm_model: string;
  llm_fallback_model: string;
  llm_base_url: string;
  llm_api_key: string;
  llm_anthropic_key: string;
  llm_openai_key: string;
  llm_gemini_key: string;
  pipeline_timeout: number;
  stage_timeout: number;
  max_retry_count: number;
  git_auto_push: boolean;
  webhook_url: string;
  webhook_events: string;
}

interface ProviderInfo {
  id: string;
  name: string;
  description: string;
  models: { id: string; name: string; description: string }[];
}

const PROVIDER_TABS: { id: string; label: string; icon: string }[] = [
  { id: 'openai_compatible', label: 'OpenAI 兼容', icon: '🔌' },
  { id: 'anthropic', label: 'Anthropic', icon: '🟢' },
  { id: 'openai', label: 'OpenAI', icon: '⚪' },
  { id: 'gemini', label: 'Google Gemini', icon: '🔵' },
];

export default function SettingsPage() {
  const [settings, setSettings] = useState<FactorySettings | null>(null);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingModel, setTestingModel] = useState(false);
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [activeProvider, setActiveProvider] = useState('openai_compatible');

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
          setActiveProvider(data.llm_provider || 'openai_compatible');
        }
        if (modelsRes.ok) {
          const data = await modelsRes.json();
          setProviders(data.providers || []);
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
        body: JSON.stringify({
          ...form,
          llm_provider: activeProvider,
        }),
      });

      if (res.ok) {
        const result = await res.json();
        setMessage({ type: 'success', text: `✅ ${result.message}` });
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

  const handleTestConnection = async () => {
    setTestingModel(true);
    setTestResult(null);

    try {
      const currentProvider = activeProvider;
      const body: Record<string, string> = {
        provider: currentProvider,
      };

      if (currentProvider === 'openai_compatible') {
        body.base_url = form.llm_base_url || '';
        body.model = form.llm_model || '';
        body.api_key = form.llm_api_key || '';
      } else if (currentProvider === 'anthropic') {
        body.api_key = form.llm_anthropic_key || '';
        body.model = providers.find(p => p.id === 'anthropic')?.models[0]?.id || 'claude-sonnet-4-20250514';
      } else if (currentProvider === 'openai') {
        body.api_key = form.llm_openai_key || '';
        body.model = providers.find(p => p.id === 'openai')?.models[0]?.id || 'gpt-4o';
      } else if (currentProvider === 'gemini') {
        body.api_key = form.llm_gemini_key || '';
        body.model = providers.find(p => p.id === 'gemini')?.models[0]?.id || 'gemini-2.5-flash';
      }

      const res = await fetch(`${API_BASE}/settings/test-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const result = await res.json();
      setTestResult(result);
    } catch {
      setTestResult({ status: 'error', message: '❌ Network error' });
    } finally {
      setTestingModel(false);
    }
  };

  const currentProviderInfo = providers.find(p => p.id === activeProvider);
  const currentProviderIdx = PROVIDER_TABS.findIndex(t => t.id === activeProvider);
  const currentProviderTab = PROVIDER_TABS[currentProviderIdx] || PROVIDER_TABS[0];

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
          <div className={`mb-6 p-4 rounded-lg border ${
            message.type === 'success'
              ? 'bg-green-50 border-green-200 text-green-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}>
            {message.text}
          </div>
        )}

        <div className="space-y-8">
          {/* LLM Configuration */}
          <section className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              🤖 LLM Provider & Model
            </h2>

            {/* Provider Tabs */}
            <div className="flex space-x-1 bg-gray-100 rounded-lg p-1 mb-6">
              {PROVIDER_TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveProvider(tab.id)}
                  className={`flex-1 px-4 py-2.5 text-sm font-medium rounded-md transition-all ${
                    activeProvider === tab.id
                      ? 'bg-white text-blue-700 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {tab.icon} {tab.label}
                </button>
              ))}
            </div>

            {/* Provider Description */}
            {currentProviderInfo && (
              <p className="text-sm text-gray-500 mb-4">{currentProviderInfo.description}</p>
            )}

            {/* Provider-specific config */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* openai_compatible: base_url + model + key */}
              {activeProvider === 'openai_compatible' && (
                <>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">API Base URL</label>
                    <input
                      type="text"
                      value={form.llm_base_url || ''}
                      onChange={(e) => setForm({ ...form, llm_base_url: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      placeholder="http://10.190.0.214:8080/v1"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Primary Model</label>
                    <select
                      value={form.llm_model || ''}
                      onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      {currentProviderInfo?.models.map((m) => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Fallback Model</label>
                    <select
                      value={form.llm_fallback_model || ''}
                      onChange={(e) => setForm({ ...form, llm_fallback_model: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      {currentProviderInfo?.models.map((m) => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
                    <input
                      type="password"
                      value={form.llm_api_key || ''}
                      onChange={(e) => setForm({ ...form, llm_api_key: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      placeholder="sk-..."
                    />
                  </div>
                </>
              )}

              {/* anthropic: api_key + model */}
              {activeProvider === 'anthropic' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Model</label>
                    <select
                      value={form.llm_model || ''}
                      onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      {currentProviderInfo?.models.map((m) => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
                    <input
                      type="password"
                      value={form.llm_anthropic_key || ''}
                      onChange={(e) => setForm({ ...form, llm_anthropic_key: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      placeholder="sk-ant-..."
                    />
                  </div>
                </>
              )}

              {/* openai: api_key + model */}
              {activeProvider === 'openai' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Model</label>
                    <select
                      value={form.llm_model || ''}
                      onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      {currentProviderInfo?.models.map((m) => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
                    <input
                      type="password"
                      value={form.llm_openai_key || ''}
                      onChange={(e) => setForm({ ...form, llm_openai_key: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      placeholder="sk-..."
                    />
                  </div>
                </>
              )}

              {/* gemini: api_key + model */}
              {activeProvider === 'gemini' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Model</label>
                    <select
                      value={form.llm_model || ''}
                      onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      {currentProviderInfo?.models.map((m) => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
                    <input
                      type="password"
                      value={form.llm_gemini_key || ''}
                      onChange={(e) => setForm({ ...form, llm_gemini_key: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      placeholder="AIza..."
                    />
                  </div>
                </>
              )}
            </div>

            {/* Test Connection Button */}
            <div className="mt-6 flex items-center space-x-4">
              <button
                onClick={handleTestConnection}
                disabled={testingModel}
                className="px-4 py-2 border border-blue-300 text-blue-700 text-sm font-medium rounded-lg hover:bg-blue-50 disabled:opacity-50 transition-colors"
              >
                {testingModel ? '⏳ 测试中...' : '🔌 测试连接'}
              </button>
              {testResult && (
                <span className={`text-sm ${
                  testResult.status === 'ok' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {testResult.message}
                </span>
              )}
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
