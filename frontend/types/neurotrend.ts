export interface ProductSuggestion {
  type: string
  title: string
  description: string
  target_user: string
  price_range: string
  roi_score: number
  automation_score: number
  viral_score: number
  time_to_build: string
  why_this_works: string
  composite_score?: number
}

export interface MonetizationStrategy {
  quick_win: string
  mid_term: string
  long_term: string
}

export interface ActionPlan {
  day1: string
  week1: string
  month1: string
}

export interface OpportunityReport {
  id: string
  topic: string
  why_viral: string
  core_emotions: string[]
  core_pain_points: string[]
  willingness_to_pay: string
  product_suggestions: ProductSuggestion[]
  best_product: string | null
  roi_score: number
  automation_score: number
  seo_value: string | null
  lifecycle: string | null
  hook_lines?: string[]
  content_angles?: string[]
  monetization_strategy?: MonetizationStrategy
  action_plan?: ActionPlan
  audience_profile?: string
}

export interface TrendScanRequest {
  sources: string[]
  limit: number
}

export interface TrendScanResponse {
  job_id?: string
  status?: string
  opportunities?: OpportunityReport[]
  message?: string
}

export interface TrendScanJob {
  job_id: string
  status: 'queued' | 'running' | 'done' | 'failed'
  sources: string[]
  scanned_count: number
  opportunities_count: number
  error_msg: string | null
  created_at: string
}

export const EMOTION_COLORS: Record<string, string> = {
  anxiety: 'bg-orange-500',
  desire: 'bg-pink-500',
  vanity: 'bg-purple-500',
  loneliness: 'bg-blue-400',
  money_desire: 'bg-green-500',
  social_approval: 'bg-yellow-500',
  escapism: 'bg-indigo-500',
  achievement: 'bg-emerald-500',
  inferiority: 'bg-gray-500',
}

// ─── Content Product Types ────────────────────────────────────────────────────

export interface EbookMeta {
  product_type: 'ebook'
  title: string
  subtitle: string
  tagline: string
  price_suggestion: string
  chapters: Array<{
    number: number
    title: string
    hook: string
    content?: string // 只有 written=true 的章节有
    written: boolean
  }>
  intro_sample: string
  marketing_angles: string[]
  sales_page_headline: string
}

export interface PersonalityTestMeta {
  product_type: 'personality_test'
  title: string
  tagline: string
  html_content: string
  test_data: {
    test_name: string
    questions: Array<{
      id: number
      text: string
      options: Array<{ id: string; text: string }>
    }>
    result_types: Array<{
      id: string
      name: string
      emoji: string
      description: string
    }>
    viral_hook: string
  }
}

export interface VideoScriptMeta {
  product_type: 'short_video_scripts'
  title: string
  series_concept: string
  scripts: Array<{
    id: number
    title: string
    hook_line: string
    duration_seconds: number
    format: string
    script: Array<{ timestamp: string; visual: string; narration: string; emotion: string }>
    caption: string
    hashtags: string[]
    viral_potential: number
    tts_suitable: boolean
    bgm_style: string
  }>
  scripts_count: number
}

export interface ContentProduct {
  id: string
  opportunity_id: string
  product_type: 'ebook' | 'personality_test' | 'short_video_scripts'
  title: string | null
  status: 'pending' | 'generating' | 'ready' | 'failed'
  content_url: string | null
  meta: EbookMeta | PersonalityTestMeta | VideoScriptMeta | null
  created_at: string
}
