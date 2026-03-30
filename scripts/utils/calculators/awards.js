/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * Awards Calculator
 *
 * Calculates tournament awards: Bloodbath, Pacifist, Speed Demon,
 * Endgame Wizard, and Opening Sprinter.
 */

const { analyzeGamePhases } = require('../game-phases');
const { getPlayerNames, toFullMoves, filterGamesWithMoves, getGameId } = require('./helpers');
const { calculateTactics } = require('./tactics');
const { calculateCheckmates } = require('./checkmates');

/**
 * Calculate tournament awards
 * @param {Array} games - Array of parsed game objects
 * @returns {Object} Award statistics
 */
function calculateAwards(games) {
  const gamesWithMoves = filterGamesWithMoves(games);

  const tactics = calculateTactics(games);
  const checkmates = calculateCheckmates(games);
  const phases = gamesWithMoves.map(g => analyzeGamePhases(g.moveList, g.pgn));

  const longestEndgame = phases.reduce((longest, phase, idx) => {
    return phase.endgame > longest.moves ? { moves: phase.endgame, gameIndex: idx } : longest;
  }, { moves: 0, gameIndex: 0 });

  const shortestOpening = phases.reduce((shortest, phase, idx) => {
    if (phase.opening === 0) return shortest;
    return phase.opening < shortest.moves ? { moves: phase.opening, gameIndex: idx } : shortest;
  }, { moves: Infinity, gameIndex: 0 });

  // Extract gameIds for endgameWizard and openingSprinter
  const endgameGame = gamesWithMoves[longestEndgame.gameIndex];
  const endgameGameId = getGameId(endgameGame);

  const openingGameId = shortestOpening.moves !== Infinity
    ? (getGameId(gamesWithMoves[shortestOpening.gameIndex]))
    : null;

  return {
    bloodbath: {
      white: tactics.bloodiestGame.white,
      black: tactics.bloodiestGame.black,
      round: tactics.bloodiestGame.round,
      captures: tactics.bloodiestGame.captures,
      gameId: tactics.bloodiestGame.gameId
    },
    pacifist: {
      white: tactics.quietestGame.white,
      black: tactics.quietestGame.black,
      round: tactics.quietestGame.round,
      captures: tactics.quietestGame.captures,
      gameId: tactics.quietestGame.gameId
    },
    speedDemon: checkmates.fastest ? {
      white: checkmates.fastest.white,
      black: checkmates.fastest.black,
      round: checkmates.fastest.round,
      moves: checkmates.fastest.moves,
      winner: checkmates.fastest.winner,
      gameId: checkmates.fastest.gameId
    } : null,
    endgameWizard: {
      ...getPlayerNames(endgameGame),
      endgameMoves: toFullMoves(longestEndgame.moves),
      gameId: endgameGameId
    },
    openingSprinter: shortestOpening.moves !== Infinity ? {
      ...getPlayerNames(gamesWithMoves[shortestOpening.gameIndex]),
      openingMoves: toFullMoves(shortestOpening.moves),
      gameId: openingGameId
    } : null
  };
}

module.exports = { calculateAwards };
