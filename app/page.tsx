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

interface StatsData {
  roundNumber: number
  seasonNumber: number
  generatedAt: string
  overview: {
    totalGames: number
    totalMoves: number
    averageGameLength: number
    longestGame: {
      moves: number
      white: string
      black: string
      result: string
      gameId: string | null
    }
    shortestGame: {
      moves: number
      white: string
      black: string
      result: string
      gameId: string | null
    }
  }
  gamePhases: {
    averageOpening: number
    averageMiddlegame: number
    averageEndgame: number
    longestWaitTillCapture: {
      moves: number
      white: string
      black: string
      game: string
      gameId: string | null
    }
    longestMiddlegame: {
      moves: number
      white: string
      black: string
      game: string
      gameId: string | null
    }
    longestEndgame: {
      moves: number
      white: string
      black: string
      game: string
      gameId: string | null
    }
  }
  results: {
    whiteWins: number
    blackWins: number
    draws: number
    whiteWinPercentage: number
    blackWinPercentage: number
    drawPercentage: number
  }
  openings: {
    firstMoves: Record<string, {
      count: number
      percentage: number
      winRate: number
    }>
    popularSequences: Array<{
      moves: string
      count: number
      eco: string | null
      name: string | null
    }>
  }
  tactics: {
    totalCaptures: number
    enPassantGames: Array<{
      white: string
      black: string
      count: number
    }>
    promotions: number
    castling: {
      kingside: number
      queenside: number
    }
    bloodiestGame: {
      captures: number
      gameIndex: number
      white: string
      black: string
    }
    quietestGame: {
      captures: number
      gameIndex: number
      white: string
      black: string
    }
    longestNonCaptureStreak: {
      moves: number
      gameIndex: number
      gameId: string | null
      white: string
      black: string
    }
    totalUnderpromotions: number
    underpromotions: Array<{
      gameIndex: number
      moveNumber: number
      promotedTo: string
      color: string
      san: string
      white: string
      black: string
    }>
  }
  pieces: {
    activity: {
      pawns: number
      knights: number
      bishops: number
      rooks: number
      queens: number
      kings: number
    }
    captured: {
      pawns: number
      knights: number
      bishops: number
      rooks: number
      queens: number
    }
    survivalRate: {
      rooks: number
      queens: number
      bishops: number
      knights: number
    }
  }
  checkmates: {
    byPiece: Record<string, number>
    fastest: {
      moves: number
      gameIndex: number
      gameId: string | null
      white: string
      black: string
      winner: string
    } | null
  }
  boardHeatmap: {
    bloodiestSquare: {
      square: string
      captures: number
      description: string
    }
    mostPopularSquare: {
      square: string
      visits: number
      description: string
    }
    leastPopularSquare: {
      square: string
      visits: number
      description: string
    }
    quietestSquares: string[]
    top5Bloodiest: Array<{
      square: string
      captures: number
    }>
    top5Popular: Array<{
      square: string
      visits: number
    }>
  }
  awards: {
    bloodbath: {
      white: string
      black: string
      captures: number
      gameId: string | null
    }
    pacifist: {
      white: string
      black: string
      captures: number
      gameId: string | null
    }
    speedDemon: {
      white: string
      black: string
      moves: number
      winner: string
      gameId: string | null
    } | null
    endgameWizard: {
      white: string
      black: string
      endgameMoves: number
      gameId: string | null
    }
    openingSprinter: {
      white: string
      black: string
      openingMoves: number
      gameId: string | null
    } | null
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  funStats?: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  analysis?: any
}

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
