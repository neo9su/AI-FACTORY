"use client";

import { useState, useEffect, useCallback } from "react";
import QRLoginModal from "./qr-login-modal";

interface PublishJob {
  publish_job_id: string;
  product_id: string;
  platform: string;
  status: string; // pending | packaging | ready | uploading | uploaded | upload_failed | published | failed
  bundle_path: string | null;
  bundle_data: Record<string, unknown> | null;
  upload_result: Record<string, unknown> | null;
  post_id: string | null;
  post_url: string | null;
  error_msg: string | null;
  created_at: string;
}

interface PublishPanelProps {
  productId: string;
  productStatus: string;
}

const PLATFORM_LABELS: Record<string, string> = {
  douyin: "🎵 抖音",
  xiaohongshu: "📕 小红书",
  tiktok: "🌐 TikTok",
};

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  packaging: "bg-blue-100 text-blue-800 animate-pulse",
  ready: "bg-green-100 text-green-800",
  uploading: "bg-blue-100 text-blue-800 animate-pulse",
  uploaded: "bg-purple-100 text-purple-800",
  upload_failed: "bg-orange-100 text-orange-800",
  published: "bg-purple-100 text-purple-800",
  failed: "bg-red-100 text-red-800",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "等待中",
  packaging: "打包中...",
  ready: "✅ 已就绪",
  uploading: "上传中...",
  uploaded: "🚀 已上传",
  upload_failed: "⚠️ 上传失败",
  published: "🎉 已发布",
  failed: "❌ 失败",
};

export default function PublishPanel({ productId, productStatus }: PublishPanelProps) {
  const [jobs, setJobs] = useState<PublishJob[]>([]);
  const [triggering, setTriggering] = useState(false);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(["douyin", "xiaohongshu"]);

  const [showQRLogin, setShowQRLogin] = useState<"xiaohongshu" | "douyin" | null>(null);
  const [loginSessions, setLoginSessions] = useState<Record<string, boolean>>({});

  const handleLoginSuccess = (platform: string) => {
    setLoginSessions((prev) => ({ ...prev, [platform]: true }));
    setShowQRLogin(null);
  };

  const canPublish = ["ready", "done", "completed"].includes(productStatus);
  const hasInProgress = jobs.some((j) =>
    ["pending", "packaging", "uploading"].includes(j.status)
  );

  const fetchJobs = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/publish/jobs/${productId}`);
      if (res.ok) {
        const data = await res.json();
        setJobs(data);
      }
    } catch {
      // silent fail
    }
  }, [productId]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // Poll while any job is in progress
  useEffect(() => {
    if (!hasInProgress) return;
    const interval = setInterval(fetchJobs, 4000);
    return () => clearInterval(interval);
  }, [hasInProgress, fetchJobs]);

  const togglePlatform = (key: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(key) ? prev.filter((p) => p !== key) : [...prev, key]
    );
  };

  const handleTrigger = async () => {
    if (!selectedPlatforms.length) return;
    setTriggering(true);
    try {
      const res = await fetch("/api/v1/publish/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, platforms: selectedPlatforms }),
      });
      if (res.ok) await fetchJobs();
    } finally {
      setTriggering(false);
    }
  };

  const handleRetryUpload = async (jobId: string) => {
    const res = await fetch(`/api/v1/publish/job/${jobId}/retry-upload`, {
      method: "POST",
    });
    if (res.ok) await fetchJobs();
  };

  const handleMarkPublished = async (jobId: string) => {
    const res = await fetch(`/api/v1/publish/job/${jobId}/mark-published`, {
      method: "POST",
    });
    if (res.ok) await fetchJobs();
  };

  const downloadBundle = (job: PublishJob) => {
    if (!job.bundle_data) return;
    const blob = new Blob([JSON.stringify(job.bundle_data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${job.platform}-bundle.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      {/* Platform Login Status Bar */}
      <div className="flex gap-3 mb-6">
        {(["xiaohongshu", "douyin"] as const).map((p) => (
          <button
            key={p}
            onClick={() => setShowQRLogin(p)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              loginSessions[p]
                ? "bg-green-100 text-green-700 border border-green-300"
                : "bg-gray-100 text-gray-600 border border-gray-300 hover:bg-gray-200"
            }`}
          >
            {loginSessions[p] ? "✅" : "🔐"}{" "}
            {p === "xiaohongshu" ? "小红书" : "抖音"}
            {loginSessions[p] ? " 已登录" : " 扫码登录"}
          </button>
        ))}
      </div>

      {/* QR Login Modal */}
      {showQRLogin && (
        <QRLoginModal
          platform={showQRLogin}
          onClose={() => setShowQRLogin(null)}
          onSuccess={handleLoginSuccess}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">📤 发布到平台</h3>
        {!canPublish && (
          <span className="text-sm text-gray-400">等待内容生成完成...</span>
        )}
      </div>

      {/* Trigger controls */}
      {canPublish && (
        <div className="space-y-3">
          {/* Platform selector */}
          <div className="flex gap-2 flex-wrap">
            {Object.entries(PLATFORM_LABELS).map(([key, label]) => (
              <button
                key={key}
                onClick={() => togglePlatform(key)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
                  selectedPlatforms.includes(key)
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "bg-white text-gray-600 border-gray-300 hover:border-indigo-400"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <button
            onClick={handleTrigger}
            disabled={triggering || !selectedPlatforms.length}
            className="w-full py-2 px-4 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors"
          >
            {triggering ? "⏳ 正在排队..." : "🚀 生成发布包"}
          </button>
        </div>
      )}

      {/* Jobs list */}
      {jobs.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">发布记录</p>
          {jobs.map((job) => (
            <div
              key={job.publish_job_id}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg gap-3"
            >
              {/* Left: platform + status */}
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-sm font-medium shrink-0">
                  {PLATFORM_LABELS[job.platform] || job.platform}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${
                    STATUS_BADGE[job.status] || "bg-gray-100 text-gray-600"
                  }`}
                >
                  {STATUS_LABEL[job.status] || job.status}
                </span>
                {/* Post URL link */}
                {job.post_url && (
                  <a
                    href={job.post_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:underline"
                  >
                    查看帖子 →
                  </a>
                )}
                {/* Upload error detail */}
                {job.status === "upload_failed" && job.upload_result && (
                  <p className="text-xs text-orange-600 mt-1">
                    {String((job.upload_result as Record<string, unknown>).error || "上传失败")}
                  </p>
                )}
                {/* Retry upload button */}
                {job.status === "upload_failed" && (
                  <button
                    onClick={() => handleRetryUpload(job.publish_job_id)}
                    className="mt-1 text-xs px-2 py-1 bg-orange-100 text-orange-700 rounded hover:bg-orange-200"
                  >
                    🔄 重试上传
                  </button>
                )}
                {job.status === "failed" && job.error_msg && (
                  <span
                    className="text-xs text-red-500 truncate"
                    title={job.error_msg}
                  >
                    {job.error_msg}
                  </span>
                )}
              </div>

              {/* Right: actions */}
              <div className="flex gap-2 shrink-0">
                {job.status === "ready" && (
                  <>
                    <button
                      onClick={() => downloadBundle(job)}
                      className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
                      title="下载发布包 JSON"
                    >
                      ⬇️ 下载包
                    </button>
                    <button
                      onClick={() => handleMarkPublished(job.publish_job_id)}
                      className="text-xs px-2 py-1 bg-purple-600 text-white rounded hover:bg-purple-700 transition-colors"
                      title="手动发布后点此标记"
                    >
                      ✔ 标记已发
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : canPublish ? (
        <p className="text-sm text-gray-400 text-center py-4">
          选择平台并点击「生成发布包」开始打包 📦
        </p>
      ) : null}
    </div>
  );
}
