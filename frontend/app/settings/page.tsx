'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { notifyApi, type NotifyConfigResponse, type NotifyTestResponse } from '@/lib/api';

type TestStatus = 'idle' | 'loading' | 'success' | 'error';

export default function SettingsPage() {
  const [config, setConfig] = useState<NotifyConfigResponse | null>(null);
  const [configLoading, setConfigLoading] = useState(true);

  // Form state
  const [webhookUrl, setWebhookUrl] = useState('');
  const [signSecret, setSignSecret] = useState('');
  const [testMessage, setTestMessage] = useState('这是一条来自 AI Software Factory 的测试通知，配置成功！🎉');

  // Test result
  const [testStatus, setTestStatus] = useState<TestStatus>('idle');
  const [testResult, setTestResult] = useState<NotifyTestResponse | null>(null);

  useEffect(() => {
    const fetchConfig = async (): Promise<void> => {
      try {
        const data = await notifyApi.getConfig();
        setConfig(data);
      } catch {
        // Config fetch failed silently — backend may be offline
      } finally {
        setConfigLoading(false);
      }
    };
    void fetchConfig();
  }, []);

  const handleTestNotification = async (): Promise<void> => {
    setTestStatus('loading');
    setTestResult(null);
    try {
      const result = await notifyApi.test({
        webhook_url: webhookUrl || undefined,
        sign_secret: signSecret || undefined,
        message: testMessage || undefined,
      });
      setTestResult(result);
      setTestStatus(result.success ? 'success' : 'error');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setTestResult({
        success: false,
        mode: 'webhook',
        status_code: 0,
        error: message,
        response_body: null,
      });
      setTestStatus('error');
    }
  };

  const modeLabel: Record<string, string> = {
    webhook: '📮 自定义 Bot Webhook',
    app_bot: '🤖 App Bot (企业应用)',
    none: '❌ 未配置',
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Nav */}
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/" className="text-xl font-bold text-indigo-600">⚙️ AI Factory</Link>
          <span className="text-slate-400">/</span>
          <span className="text-slate-600 font-medium">设置</span>
          <div className="ml-auto flex gap-3">
            <Link
              href="/projects"
              className="text-sm text-slate-600 hover:text-indigo-600 transition-colors"
            >
              ← 返回项目列表
            </Link>
          </div>
        </div>
      </nav>

      <main className="container mx-auto px-4 py-10 max-w-3xl space-y-8">

        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-slate-800">系统设置</h1>
          <p className="text-slate-500 mt-2">配置通知集成，让飞书机器人实时推送项目进度。</p>
        </div>

        {/* Current Config Status */}
        <section className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-700 mb-4 flex items-center gap-2">
            📊 当前通知配置
          </h2>
          {configLoading ? (
            <div className="text-slate-400 text-sm animate-pulse">正在读取配置...</div>
          ) : config ? (
            <div className="space-y-3">
              <ConfigRow label="激活模式" value={modeLabel[config.active_mode] ?? config.active_mode} />
              <ConfigRow label="Webhook URL" value={config.webhook_configured ? '✅ 已配置' : '❌ 未配置'} />
              <ConfigRow label="签名密钥" value={config.sign_secret_configured ? '✅ 已配置' : '⬜ 未配置（可选）'} />
              <ConfigRow label="App Bot 模式" value={config.app_bot_configured ? '✅ 已配置' : '❌ 未配置'} />
              {config.active_mode === 'none' && (
                <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm">
                  ⚠️ 未检测到飞书通知配置。请在服务器 <code className="bg-amber-100 px-1 rounded">.env</code> 文件中设置 <code className="bg-amber-100 px-1 rounded">FEISHU_WEBHOOK_URL</code>，或在下方输入 Webhook URL 测试临时发送。
                </div>
              )}
            </div>
          ) : (
            <div className="text-slate-400 text-sm">无法加载配置（后端可能未启动）</div>
          )}
        </section>

        {/* Test Notification */}
        <section className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-700 mb-1 flex items-center gap-2">
            🧪 发送测试通知
          </h2>
          <p className="text-slate-500 text-sm mb-5">
            填写 Webhook URL 后点击发送，验证飞书配置是否正确。留空则使用服务器环境变量中的配置。
          </p>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">
                Webhook URL <span className="text-slate-400 font-normal">（可选，覆盖服务器配置）</span>
              </label>
              <input
                type="text"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
                placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx..."
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">
                签名密钥 <span className="text-slate-400 font-normal">（可选）</span>
              </label>
              <input
                type="password"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
                placeholder="如果开启了安全校验，填写签名密钥"
                value={signSecret}
                onChange={(e) => setSignSecret(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">
                消息内容
              </label>
              <textarea
                rows={2}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent resize-none"
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
              />
            </div>

            <button
              onClick={() => void handleTestNotification()}
              disabled={testStatus === 'loading'}
              className={`w-full py-2.5 rounded-lg font-medium text-sm transition-all ${
                testStatus === 'loading'
                  ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm hover:shadow-md'
              }`}
            >
              {testStatus === 'loading' ? '发送中...' : '📤 发送测试通知'}
            </button>
          </div>

          {/* Test Result */}
          {testResult && (
            <div
              className={`mt-4 p-4 rounded-lg border text-sm ${
                testResult.success
                  ? 'bg-green-50 border-green-200 text-green-800'
                  : 'bg-red-50 border-red-200 text-red-800'
              }`}
            >
              <div className="font-semibold mb-1">
                {testResult.success ? '✅ 通知发送成功！' : '❌ 通知发送失败'}
              </div>
              <div className="space-y-1 text-xs opacity-80">
                <div>模式：{modeLabel[testResult.mode] ?? testResult.mode}</div>
                {testResult.status_code > 0 && (
                  <div>HTTP 状态码：{testResult.status_code}</div>
                )}
                {testResult.error && (
                  <div className="mt-1 font-mono bg-red-100 rounded p-2 break-all">
                    错误：{testResult.error}
                  </div>
                )}
                {testResult.response_body && (
                  <div className="mt-1 font-mono bg-black/5 rounded p-2 break-all">
                    响应：{testResult.response_body}
                  </div>
                )}
              </div>
            </div>
          )}
        </section>

        {/* Setup Guide */}
        <section className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-700 mb-4 flex items-center gap-2">
            📖 飞书机器人接入指南
          </h2>
          <ol className="space-y-3 text-sm text-slate-600">
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center font-semibold text-xs">1</span>
              <div>
                <strong>创建群组</strong>：在飞书中创建一个用于接收通知的群组（或使用已有群组）。
              </div>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center font-semibold text-xs">2</span>
              <div>
                <strong>添加机器人</strong>：点击群组右上角「设置 → 群机器人 → 添加机器人 → 自定义机器人」。
              </div>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center font-semibold text-xs">3</span>
              <div>
                <strong>复制 Webhook URL</strong>：机器人创建完成后复制「Webhook 地址」。
              </div>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center font-semibold text-xs">4</span>
              <div>
                <strong>配置环境变量</strong>：在服务器 <code className="bg-slate-100 px-1 rounded">.env</code> 文件中设置：
                <pre className="mt-1 bg-slate-100 rounded p-2 text-xs font-mono overflow-x-auto">
{`FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx
# 可选：开启安全校验后填写
# FEISHU_SIGN_SECRET=your-sign-secret`}
                </pre>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center font-semibold text-xs">5</span>
              <div>
                <strong>验证配置</strong>：重启服务后，在上方「发送测试通知」区域点击发送，查看飞书群组是否收到消息。
              </div>
            </li>
          </ol>
        </section>

        {/* CLI Tool */}
        <section className="bg-slate-800 rounded-2xl p-6 text-slate-200">
          <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
            💻 CLI 工具（不启动服务时使用）
          </h2>
          <pre className="text-xs font-mono bg-slate-900 rounded-lg p-4 overflow-x-auto text-green-400">
{`# 快速测试 Webhook
cd ~/autonomous-ai-factory
python3 scripts/notify_test.py --webhook https://open.feishu.cn/...

# 发送所有通知类型（stage/task/test/delivery/gate）
python3 scripts/notify_test.py --all

# 从 .env 读取配置
python3 scripts/notify_test.py`}
          </pre>
        </section>

      </main>
    </div>
  );
}

function ConfigRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-700">{value}</span>
    </div>
  );
}
