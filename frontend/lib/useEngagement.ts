'use client'

import { useCallback, useRef } from 'react'
import { analyticsApi } from '@/lib/api'

/**
 * Returns a stable `trackEvent` function that fires engagement events
 * without re-rendering the calling component.
 *
 * Usage:
 *   const { trackEvent } = useEngagement()
 *   <button onClick={() => trackEvent(productId, 'view')}>View</button>
 */
export function useEngagement() {
  // session_id: stable per-browser-tab UUID (not PII)
  const sessionRef = useRef<string>(
    typeof window !== 'undefined'
      ? (localStorage.getItem('_nt_sid') ??
          (() => {
            const id = crypto.randomUUID()
            localStorage.setItem('_nt_sid', id)
            return id
          })())
      : '',
  )

  const trackEvent = useCallback(
    (
      productId: string,
      eventType: 'view' | 'audio_play' | 'ebook_download' | 'test_complete',
      metadata?: Record<string, unknown>,
    ) => {
      void analyticsApi.logEvent(productId, eventType, sessionRef.current, metadata)
    },
    [],
  )

  const trackView = useCallback(
    (productId: string, opportunityId?: string, metadata?: Record<string, unknown>) => {
      void analyticsApi.logEvent(productId, 'view', sessionRef.current, {
        opportunity_id: opportunityId,
        ...metadata,
      })
    },
    [],
  )

  const trackPlay = useCallback(
    (productId: string, opportunityId?: string, metadata?: Record<string, unknown>) => {
      void analyticsApi.logEvent(productId, 'audio_play', sessionRef.current, {
        opportunity_id: opportunityId,
        ...metadata,
      })
    },
    [],
  )

  const trackDownload = useCallback(
    (productId: string, opportunityId?: string, metadata?: Record<string, unknown>) => {
      void analyticsApi.logEvent(productId, 'ebook_download', sessionRef.current, {
        opportunity_id: opportunityId,
        ...metadata,
      })
    },
    [],
  )

  const trackTestComplete = useCallback(
    (productId: string, opportunityId?: string, metadata?: Record<string, unknown>) => {
      void analyticsApi.logEvent(productId, 'test_complete', sessionRef.current, {
        opportunity_id: opportunityId,
        ...metadata,
      })
    },
    [],
  )

  return { trackEvent, trackView, trackPlay, trackDownload, trackTestComplete }
}
