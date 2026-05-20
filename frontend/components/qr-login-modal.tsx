"use client";

import { useState, useEffect, useCallback } from "react";

interface QRLoginModalProps {
  platform: "xiaohongshu" | "douyin";
  onClose: () => void;
  onSuccess: (platform: string, userInfo: Record<string, unknown>) => void;
}

interface StartLoginResponse {
  session_id: string;
  platform: string;
  qr_image_url: string;
  status: string;
}

interface LoginStatusResponse {
  session_id: string;
  platform: string;
  status: "pending" | "scanning" | "logged_in" | "expired" | "failed";
  user_info?: Record<string, unknown>;
  error?: string;
}

const PLATFORM_LABELS: Record<string, string> = {
  xiaohongshu: "小红书",
  douyin: "抖音",
};

export default function QRLoginModal({ platform, onClose, onSuccess }: QRLoginModalProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [qrImageUrl, setQrImageUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<LoginStatusResponse["status"]>("pending");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  const platformLabel = PLATFORM_LABELS[platform] || platform;

  const startLogin = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setQrImageUrl(null);
      setSessionId(null);
      setStatus("pending");
      const res = await fetch(`/api/platform-login/start/${platform}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: StartLoginResponse = await res.json();
      setSessionId(data.session_id);
      setQrImageUrl(data.qr_image_url);
      setLoading(false);
    } catch {
      setError("无法启动登录，请稍后重试");
      setLoading(false);
    }
  }, [platform]);

  useEffect(() => {
    startLogin();
  }, [startLogin, refreshKey]);

  useEffect(() => {
    if (!sessionId || status === "logged_in" || status === "failed") return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/platform-login/status/${sessionId}`);
        const data: LoginStatusResponse = await res.json();
        setStatus(data.status);
        if (data.status === "logged_in") {
          clearInterval(interval);
          setTimeout(() => onSuccess(platform, data.user_info || {}), 1000);
        } else if (data.status === "failed") {
          clearInterval(interval);
          setError(data.error || "登录失败");
        }
      } catch {
        // ignore poll errors
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [sessionId, status, platform, onSuccess]);

  const handleCancel = useCallback(async () => {
    if (sessionId) {
      try {
        await fetch(`/api/platform-login/session/${sessionId}`, { method: "DELETE" });
      } catch {
        // ignore
      }
    }
    onClose();
  }, [sessionId, onClose]);

  const handleRefresh = () => setRefreshKey((k) => k + 1);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-8 w-96 text-center shadow-xl">
        <h2 className="text-xl font-bold mb-2">
          {platformLabel} 扫码登录
        </h2>
        <p className="text-gray-500 text-sm mb-6">
          打开 {platformLabel} App，扫描下方二维码
        </p>

        {loading && (
          <div className="h-48 flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500" />
          </div>
        )}

        {!loading && qrImageUrl && status !== "logged_in" && (
          <div className="relative inline-block mb-4">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={qrImageUrl}
              alt="QR Code"
              className="w-48 h-48 mx-auto border rounded-lg object-contain"
            />
            {status === "scanning" && (
              <div className="absolute inset-0 bg-white/80 flex items-center justify-center rounded-lg">
                <span className="text-green-600 font-semibold">扫描成功，请确认...</span>
              </div>
            )}
          </div>
        )}

        {status === "logged_in" && (
          <div className="h-48 flex flex-col items-center justify-center gap-3">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <svg
                className="w-8 h-8 text-green-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <p className="text-green-600 font-semibold">登录成功！</p>
          </div>
        )}

        {error && !loading && (
          <p className="text-red-500 text-sm mb-4">{error}</p>
        )}

        <div className="flex gap-3 mt-4">
          <button
            onClick={handleCancel}
            className="flex-1 py-2 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 transition"
          >
            {status === "logged_in" ? "关闭" : "取消"}
          </button>
          {status !== "logged_in" && (
            <button
              onClick={handleRefresh}
              className="flex-1 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition"
            >
              刷新二维码
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
