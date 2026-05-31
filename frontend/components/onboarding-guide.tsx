'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

// ─── Step definitions ────────────────────────────────────────────────────

interface Step {
  icon: string;
  title: string;
  content: React.ReactNode;
}

const STEPS: Step[] = [
  {
    icon: '🧠',
    title: '欢迎来到 NeuroTrend',
    content: (
      <div className="space-y-3">
        <p>
          <strong>NeuroTrend</strong> 是一个 AI 驱动的商机发现引擎。
          它自动抓取社交媒体和网络热点，分析背后的用户情绪与心理需求，
          帮你发现<strong className="text-emerald-400">高 ROI 的产品商机</strong>。
        </p>
        <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-4 space-y-2">
          <p className="text-sm text-indigo-200 font-medium">核心流程</p>
          <div className="text-sm text-gray-300 space-y-1">
            <p>🌐 热点数据 → 🧠 情绪分析 → 💡 商机发现 → 🤖 产品生成 → 📱 发布变现</p>
          </div>
        </div>
      </div>
    ),
  },
  {
    icon: '🔍',
    title: '第一步：发现商机',
    content: (
      <div className="space-y-3">
        <p>在商机列表页，你可以：</p>
        <ul className="space-y-2">
          <li className="flex items-start gap-2">
            <span className="text-indigo-400 mt-0.5">1.</span>
            <span><strong>选择数据源</strong> — 勾选 Reddit、MBTI 人格、情绪疗愈等渠道</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-400 mt-0.5">2.</span>
            <span>点击 <strong>🔍 开始扫描</strong>，系统自动抓取热点并分析商机</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-400 mt-0.5">3.</span>
            <span>用过滤按钮（ROI &gt; 8 / 电子书 / 人格测试等）快速筛选</span>
          </li>
        </ul>
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 text-sm text-amber-300">
          💡 目前系统已预置 5 组种子商机数据，可以直接体验完整流程
        </div>
      </div>
    ),
  },
  {
    icon: '🏭',
    title: '第二步：生成产品',
    content: (
      <div className="space-y-3">
        <p>进入商机详情页，点击 <strong>🚀 生成产品</strong>，目前支持三种类型：</p>
        <div className="grid gap-3 mt-3">
          <div className="bg-white/5 border border-white/10 rounded-xl p-3">
            <p className="font-bold text-sm">🧪 人格测试</p>
            <p className="text-xs text-gray-400 mt-1">
              自动生成完整的 H5 心理测试页面（7-15 道题 + 计分逻辑 + 4-6 种结果类型），
              可直接部署或分享
            </p>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-3">
            <p className="font-bold text-sm">📖 电子书</p>
            <p className="text-xs text-gray-400 mt-1">
              6 章完整电子书内容（含引言 + 章节大纲），带营销角度和销售页文案建议
            </p>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-3">
            <p className="font-bold text-sm">🎬 短视频脚本</p>
            <p className="text-xs text-gray-400 mt-1">
              5 条带钩子标题的短视频脚本（含镜头描述、旁白、情绪曲线、标签、BGM 建议），
              可直接用于拍摄或 TTS 配音
            </p>
          </div>
        </div>
      </div>
    ),
  },
  {
    icon: '👀',
    title: '第三步：查看已生成产品',
    content: (
      <div className="space-y-3">
        <p>
          生成完成后，在详情页<strong className="text-emerald-400">底部「📦 已生成产品」区域</strong>
          可以看到所有产品。
        </p>
        <ul className="space-y-2 text-sm">
          <li className="flex items-start gap-2">
            <span className="text-indigo-400">•</span>
            <span>点击 <strong>「查看内容」</strong> → 展开完整的 AI 生成内容（测试题目、电子书章节、视频脚本）</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-400">•</span>
            <span>人格测试产品可以直接 <strong>下载 HTML 文件</strong>，在浏览器中打开就是一个完整的测试页面</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-400">•</span>
            <span>电子书可以展开阅读各章全文，也可以拷贝内容自行编辑</span>
          </li>
        </ul>
      </div>
    ),
  },
  {
    icon: '🚀',
    title: '第四步：发布 & 部署',
    content: (
      <div className="space-y-3">
        <p>每个已就绪的产品旁边都有 <strong className="text-emerald-400">「🚀 发布」</strong> 按钮：</p>

        <div className="bg-white/5 border border-white/10 rounded-xl p-3">
          <p className="font-bold text-sm text-pink-300">📱 社交媒体发布</p>
          <p className="text-xs text-gray-400 mt-1">
            选择抖音 / 小红书 / TikTok → 系统自动生成适配图文和视频 → 通过扫码登录发布
          </p>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-xl p-3">
          <p className="font-bold text-sm text-cyan-300">🌐 部署到网站</p>
          <p className="text-xs text-gray-400 mt-1">
            填入服务器 IP、用户名、密码 → 系统自动将人格测试 HTML 页面部署到你的网站，
            获得独立 URL 可用于引流
          </p>
        </div>

        <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-3">
          <p className="text-xs text-green-300 font-semibold">💰 变现路径</p>
          <ul className="text-xs text-gray-400 mt-1 space-y-0.5 list-disc list-inside">
            <li>人格测试 → 引流 → 公众号变现 / 付费解锁完整报告</li>
            <li>电子书 → 小报童 / Gumroad / 知识星球出售</li>
            <li>短视频 → 抖音/小红书涨粉 → 带货 / 咨询</li>
          </ul>
        </div>
      </div>
    ),
  },
];

// ─── Component ────────────────────────────────────────────────────────────

export default function OnboardingGuide() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [dismissed, setDismissed] = useState(false);

  // Show on first visit (once per session)
  useEffect(() => {
    const seen = sessionStorage.getItem('neurotrend_onboarding_seen');
    if (!seen) {
      // Small delay so page renders first
      const t = setTimeout(() => setOpen(true), 800);
      return () => clearTimeout(t);
    }
  }, []);

  const handleClose = () => {
    sessionStorage.setItem('neurotrend_onboarding_seen', 'true');
    setOpen(false);
    setDismissed(true);
  };

  const s = STEPS[step];

  return (
    <>
      {/* Floating help button */}
      <button
        onClick={() => {
          setOpen(true);
          setStep(0);
        }}
        className={cn(
          'fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full',
          'bg-gradient-to-br from-indigo-500 to-purple-600',
          'hover:from-indigo-400 hover:to-purple-500',
          'shadow-lg shadow-indigo-900/50 hover:shadow-xl',
          'flex items-center justify-center text-xl font-bold text-white',
          'transition-all duration-200 hover:scale-110',
          'border border-white/20',
          dismissed && 'animate-bounce-subtle',
        )}
        title="使用引导"
      >
        ?
      </button>

      {/* Modal overlay */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={handleClose}
          />

          {/* Modal */}
          <div className="relative w-full max-w-lg bg-slate-800 border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="px-6 pt-6 pb-2">
              <div className="flex items-center justify-between">
                <span className="text-3xl">{s.icon}</span>
                <button
                  onClick={handleClose}
                  className="text-white/40 hover:text-white/80 text-lg"
                >
                  ✕
                </button>
              </div>
              <h2 className="text-xl font-bold text-white mt-2">{s.title}</h2>
            </div>

            {/* Body */}
            <div className="px-6 py-4 text-sm text-gray-200 leading-relaxed min-h-[200px]">
              {s.content}
            </div>

            {/* Footer */}
            <div className="px-6 pb-6 pt-2 flex items-center justify-between">
              {/* Step dots */}
              <div className="flex items-center gap-1.5">
                {STEPS.map((_, i) => (
                  <button
                    key={i}
                    onClick={() => setStep(i)}
                    className={cn(
                      'w-2 h-2 rounded-full transition-all',
                      i === step
                        ? 'bg-indigo-400 w-6'
                        : 'bg-white/20 hover:bg-white/40',
                    )}
                  />
                ))}
              </div>

              {/* Nav buttons */}
              <div className="flex gap-2">
                {step > 0 && (
                  <button
                    onClick={() => setStep(step - 1)}
                    className="px-4 py-2 rounded-lg border border-white/20 text-sm text-white/70 hover:text-white hover:border-white/40 transition-colors"
                  >
                    ← 上一步
                  </button>
                )}
                {step < STEPS.length - 1 ? (
                  <button
                    onClick={() => setStep(step + 1)}
                    className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-sm font-semibold text-white transition-colors"
                  >
                    下一步 →
                  </button>
                ) : (
                  <button
                    onClick={handleClose}
                    className="px-5 py-2 rounded-lg bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-sm font-semibold text-white transition-colors"
                  >
                    🚀 开始使用
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Inject bounce animation */}
      <style jsx global>{`
        @keyframes bounce-subtle {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-4px); }
        }
        .animate-bounce-subtle {
          animation: bounce-subtle 2s ease-in-out infinite;
        }
      `}</style>
    </>
  );
}
