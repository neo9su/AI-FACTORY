'use client'

import { useState, useEffect, useRef } from 'react'

interface AudioEntry {
  script_id: number
  script_title: string
  url: string
  lines_count: number
}

interface TTSPlayerProps {
  opportunityId: string
  productId: string
  initialTtsStatus?: string | null
  initialAudioUrls?: AudioEntry[] | null
}

export default function TTSPlayer({
  opportunityId,
  productId,
  initialTtsStatus,
  initialAudioUrls,
}: TTSPlayerProps) {
  const [status, setStatus] = useState(initialTtsStatus ?? null)
  const [audioUrls, setAudioUrls] = useState<AudioEntry[]>(initialAudioUrls ?? [])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<NodeJS.Timeout | null>(null)

  const BASE = `/api/v1/opportunities/${opportunityId}/products/${productId}/tts`

  // 轮询逻辑
  useEffect(() => {
    if (status === 'pending' || status === 'generating') {
      pollRef.current = setInterval(async () => {
        try {
          const res = await fetch(BASE)
          const data = await res.json()
          setStatus(data.tts_status)
          if (data.tts_audio_urls?.length) setAudioUrls(data.tts_audio_urls)
          if (data.tts_status === 'ready' || data.tts_status === 'failed') {
            clearInterval(pollRef.current!)
          }
        } catch {
          // silently ignore poll errors
        }
      }, 4000)
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [status, BASE])

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(BASE, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || 'TTS 失败')
        return
      }
      setStatus(data.status === 'queued' ? 'pending' : data.status)
      if (data.tts_audio_urls) setAudioUrls(data.tts_audio_urls)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  // 1. ready: 展示每个 script 的 <audio> 播放器
  if (status === 'ready' && audioUrls.length > 0) {
    return (
      <div className="mt-6 space-y-4">
        <h3 className="text-lg font-semibold text-indigo-300 flex items-center gap-2">
          🎵 配音已生成
        </h3>
        {audioUrls.map((entry) => (
          <div
            key={entry.script_id}
            className="bg-slate-800 rounded-xl p-4 border border-slate-700"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-200">
                🎬 脚本 {entry.script_id}: {entry.script_title}
              </span>
              <span className="text-xs text-slate-500">{entry.lines_count} 段旁白</span>
            </div>
            <audio controls src={entry.url} className="w-full h-10 accent-indigo-500" />
          </div>
        ))}
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="text-xs text-slate-500 hover:text-slate-300 underline"
        >
          重新生成
        </button>
      </div>
    )
  }

  // 2. pending/generating: 动画 spinner + 进度文字
  if (status === 'pending' || status === 'generating') {
    return (
      <div className="mt-6 flex items-center gap-3 text-orange-400">
        <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z"
          />
        </svg>
        <span className="text-sm">
          {status === 'pending'
            ? 'CosyVoice2 配音待启动...'
            : 'AI 配音生成中，预计 2-5 分钟...'}
        </span>
      </div>
    )
  }

  // 3. failed: 红色错误提示 + 重试按钮
  if (status === 'failed') {
    return (
      <div className="mt-6 space-y-2">
        <p className="text-sm text-red-400">❌ 配音生成失败</p>
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-lg"
        >
          {loading ? '生成中...' : '重试配音'}
        </button>
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>
    )
  }

  // 4. 未开始: 显示「生成配音」按钮
  return (
    <div className="mt-6">
      <button
        onClick={handleGenerate}
        disabled={loading}
        className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium rounded-xl transition-all disabled:opacity-50"
      >
        {loading ? (
          <>
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z"
              />
            </svg>
            入队中...
          </>
        ) : (
          <>✨ 生成 CosyVoice2 配音</>
        )}
      </button>
      {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
    </div>
  )
}
