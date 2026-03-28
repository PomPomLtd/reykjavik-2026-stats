interface TournamentHeaderProps {
  totalGames: number
  generatedAt: string
}

export function TournamentHeader({ totalGames, generatedAt }: TournamentHeaderProps) {
  const formattedDate = new Date(generatedAt).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })

  return (
    <div className="text-center mb-8">
      <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-white mb-3">
        Reykjavik 2026
      </h1>
      <p className="text-lg text-gray-600 dark:text-gray-400 mb-4">
        {totalGames} games analyzed
      </p>
      <div className="flex items-center justify-center gap-4 text-sm text-gray-500 dark:text-gray-500">
        <span>Generated {formattedDate}</span>
        <span>|</span>
        <a
          href="https://lichess.org/study/lGf88qOA"
          target="_blank"
          rel="noopener noreferrer"
          className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
        >
          View games on Lichess
        </a>
      </div>
    </div>
  )
}
