'use client'

import { useState, useEffect } from 'react'
import { TournamentHeader } from '@/components/stats/tournament-header'
import { OverviewStats } from '@/components/stats/overview-stats'
import { ResultsBreakdown } from '@/components/stats/results-breakdown'
import { AwardsSection } from '@/components/stats/awards-section'
import { GamePhases } from '@/components/stats/game-phases'
import { TacticsSection } from '@/components/stats/tactics-section'
import { OpeningsSection } from '@/components/stats/openings-section'
import { PieceStats } from '@/components/stats/piece-stats'
import { NotableGames } from '@/components/stats/notable-games'
import { FunStats } from '@/components/stats/fun-stats'
import { CheckmatesSection } from '@/components/stats/checkmates-section'
import { BoardHeatmapSection } from '@/components/stats/board-heatmap-section'
import { AnalysisSection } from '@/components/stats/analysis-section'

// Stats data is loaded from tournament.json - child components define their own prop types
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type StatsData = Record<string, any>

export default function TournamentStatsPage() {
  const [stats, setStats] = useState<StatsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/stats/tournament.json')
        if (!response.ok) {
          throw new Error('Stats not found')
        }
        const data = await response.json()
        setStats(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load stats')
      } finally {
        setLoading(false)
      }
    }
    fetchStats()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500 dark:text-gray-400">Loading statistics...</div>
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Stats Not Available</h2>
          <p className="text-gray-600 dark:text-gray-400">{error || 'Failed to load statistics'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="space-y-8">
          <TournamentHeader
            totalGames={stats.overview.totalGames}
            generatedAt={stats.generatedAt}
          />

          <OverviewStats overview={stats.overview} />

          <ResultsBreakdown results={stats.results} />

          <AwardsSection awards={stats.awards} />

          {stats.analysis && <AnalysisSection analysis={stats.analysis} />}

          <FunStats funStats={stats.funStats} />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <GamePhases gamePhases={stats.gamePhases} />
            <TacticsSection tactics={stats.tactics} />
          </div>

          <OpeningsSection openings={stats.openings} />

          <PieceStats pieces={stats.pieces} />

          <NotableGames
            overview={stats.overview}
            longestNonCaptureStreak={stats.tactics.longestNonCaptureStreak}
          />

          <CheckmatesSection checkmates={stats.checkmates} />

          <BoardHeatmapSection boardHeatmap={stats.boardHeatmap} />
        </div>
      </div>
    </div>
  )
}
