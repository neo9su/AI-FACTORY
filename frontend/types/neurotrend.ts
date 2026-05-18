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
