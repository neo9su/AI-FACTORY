'use client'

interface EngagementBarProps {
  label: string
  value: number // raw count
  maxValue: number // for width normalization
  colorClass?: string
  icon?: string
}

export function EngagementBar({
  label,
  value,
  maxValue,
  colorClass = 'bg-indigo-500',
  icon = '',
}: EngagementBarProps) {
  const pct = maxValue > 0 ? Math.min(100, Math.round((value / maxValue) * 100)) : 0
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-white/60">
        <span>
          {icon && <span className="mr-1">{icon}</span>}
          {label}
        </span>
        <span className="font-semibold text-white">{value.toLocaleString()}</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-white/10">
        <div
          className={`h-1.5 rounded-full transition-all duration-500 ${colorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
