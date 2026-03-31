# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chess tournament statistics site for the Reykjavik 2026 tournament. Generates stats from PGN files and displays them as a Next.js web app. Originally forked/migrated from a Lichess 4545 League stats platform.

## Commands

```bash
# Development
npm run dev              # Next.js dev server with Turbopack (http://localhost:3000)
npm run build            # Production build (runs generate-build-info.js as prebuild)
npm run lint             # ESLint

# Stats generation (reads PGN, outputs public/stats/tournament.json)
node scripts/generate-stats.js                          # Default: reads data/tournament.pgn
node scripts/generate-stats.js --pgn path/to/file.pgn   # Custom PGN path
node scripts/generate-stats.js --analyze                # Include Stockfish analysis (slow, needs python-chess)
```

## Architecture

### Data Pipeline

`data/tournament.pgn` -> `scripts/generate-stats.js` -> `public/stats/tournament.json` -> Next.js frontend

1. **PGN Parser** (`scripts/utils/pgn-parser.js`): Parses PGN text into structured game objects using `@mliebelt/pgn-parser` + `chess.js` for move replay
2. **Stats Calculator** (`scripts/utils/stats-calculator.js`): Orchestrates all calculators in `scripts/utils/calculators/` (overview, results, openings, tactics, pieces, heatmap, awards, checkmates, fun-stats, game-phases)
3. **Optional Python analysis**: `scripts/analyze-tactics.py` (pins/forks/skewers) and `scripts/analyze-pgn.py` (Stockfish depth analysis) - require python-chess in `venv/`

### Frontend

- **Single-page app**: `app/page.tsx` fetches `public/stats/tournament.json` at runtime (client-side)
- **Stats components**: ~20 components in `components/stats/` - each receives a slice of the tournament JSON as props
- **Shared components**: `components/navigation.tsx`, `components/footer.tsx`, `components/board-heatmap.tsx` (canvas-based chessboard visualization)
- **Stack**: Next.js 15 (App Router), React 19, TailwindCSS 4, Recharts for charts

### Fun Stats System

`scripts/utils/calculators/fun-stats/` contains ~18 individual award calculators (e.g., edge-lord, dark-lord, chicken-award, pawn-storm). Each exports a function that analyzes games and returns award data. They are aggregated by `scripts/utils/calculators/fun-stats/index.js`.

### Key Patterns

- Scripts use CommonJS (`require`/`module.exports`); frontend uses ESM/TypeScript
- Stats data is untyped on the frontend (`Record<string, any>`) - components define their own prop types
- Opening classification uses ECO code TSV files in `scripts/utils/openings-*.tsv`
