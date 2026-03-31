/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * Fun Stats Orchestrator
 *
 * Coordinates all fun stat calculators and returns combined results.
 */

const { calculateQueenTrades } = require('./queen-trades');
const { calculateCaptureSequence } = require('./capture-sequence');
const { calculateCheckSequence } = require('./check-sequence');
const { calculatePawnStorm } = require('./pawn-storm');
const { calculatePieceLoyalty } = require('./piece-loyalty');
const { calculateSquareTourist } = require('./square-tourist');
const { calculateCastlingRace } = require('./castling-race');
const { calculateOpeningHipster } = require('./opening-hipster');
const { calculateDadbodShuffler } = require('./dadbod-shuffler');
const { calculateSportyQueen } = require('./sporty-queen');
const { calculateEdgeLord } = require('./edge-lord');
const { calculateRookLift } = require('./rook-lift');
const { calculateCenterStage } = require('./center-stage');
const { calculateDarkLord } = require('./dark-lord');
const { calculateSunglasses } = require('./sunglasses');
const { calculateChickenAward } = require('./chicken-award');
const { calculateSlowestCastling } = require('./slowest-castling');
const { calculatePawnCaptures } = require('./pawn-captures');
const { calculateAntiOrthogonal } = require('./anti-orthogonal');
const { calculateComfortZone } = require('./comfort-zone');
const { filterGamesWithMoves, getGameId } = require('../helpers');

/**
 * Calculate all fun statistics
 * @param {Array} games - Array of parsed game objects
 * @param {Object} tacticalPatterns - Optional tactical patterns data from Python analysis
 * @returns {Object} All fun statistics
 */
function calculateFunStats(games, tacticalPatterns = null) {
  const gamesWithMoves = filterGamesWithMoves(games);

  // Build gameId lookup by gameIndex for enriching tacticalPatterns data
  const gameIdByIndex = {};
  gamesWithMoves.forEach((game, idx) => {
    gameIdByIndex[idx] = getGameId(game);
  });

  const queenTrades = calculateQueenTrades(gamesWithMoves);
  const pieceLoyalty = calculatePieceLoyalty(gamesWithMoves);

  const funStats = {
    fastestQueenTrade: queenTrades?.fastest || null,
    slowestQueenTrade: queenTrades?.slowest || null,
    longestCaptureSequence: calculateCaptureSequence(gamesWithMoves),
    longestCheckSequence: calculateCheckSequence(gamesWithMoves),
    pawnStorm: calculatePawnStorm(gamesWithMoves),
    pieceLoyalty: pieceLoyalty?.moves >= 30 ? pieceLoyalty : null, // Only show if 30+ moves (15 full moves)
    squareTourist: calculateSquareTourist(gamesWithMoves),
    castlingRace: calculateCastlingRace(gamesWithMoves),
    openingHipster: calculateOpeningHipster(gamesWithMoves),
    dadbodShuffler: calculateDadbodShuffler(gamesWithMoves),
    sportyQueen: calculateSportyQueen(gamesWithMoves),
    edgeLord: calculateEdgeLord(gamesWithMoves),
    rookLift: calculateRookLift(gamesWithMoves),
    centerStage: calculateCenterStage(gamesWithMoves),
    darkLord: calculateDarkLord(gamesWithMoves),
    sunglasses: calculateSunglasses(gamesWithMoves),
    chickenAward: calculateChickenAward(gamesWithMoves),
    slowestCastling: calculateSlowestCastling(gamesWithMoves),
    pawnCaptures: calculatePawnCaptures(gamesWithMoves),
    antiOrthogonal: calculateAntiOrthogonal(gamesWithMoves),
    comfortZone: calculateComfortZone(gamesWithMoves)
  };

  // Add chicken awards from tactical patterns (Python analysis)
  if (tacticalPatterns && tacticalPatterns.summary) {
    const summary = tacticalPatterns.summary;

    // Helper to enrich tactical pattern data with gameId from the lookup
    const enrichWithGameId = (data) => {
      if (!data) return null;
      return { ...data, gameId: data.gameId || gameIdByIndex[data.gameIndex] || null };
    };

    // Homebody: Least pieces in enemy territory
    if (summary.homebody) {
      const h = enrichWithGameId(summary.homebody);
      const playerName = h.player === 'white' ? h.white : h.black;
      funStats.homebody = {
        ...h,
        playerName: playerName,
        description: `${playerName} only crossed ${h.piecesInEnemy} piece(s) into opponent's half of the board`
      };
    }

    // Late Bloomer: Waited longest to invade enemy territory
    if (summary.lateBloomer) {
      const lb = enrichWithGameId(summary.lateBloomer);
      const playerName = lb.player === 'white' ? lb.white : lb.black;
      funStats.lateBloomer = {
        ...lb,
        playerName: playerName,
        description: `${playerName} waited until move ${Math.floor((lb.moveNumber + 1) / 2)} to cross into opponent's half`
      };
    }

    // Quick Draw: Invaded earliest
    if (summary.quickDraw) {
      const qd = enrichWithGameId(summary.quickDraw);
      const playerName = qd.player === 'white' ? qd.white : qd.black;
      funStats.quickDraw = {
        ...qd,
        playerName: playerName,
        description: `${playerName} crossed into opponent's half on move ${Math.floor((qd.moveNumber + 1) / 2)}`
      };
    }

    // Crosshairs: Square under most simultaneous attack in a single position
    if (summary.mostAttackedSquareGame && summary.mostAttackedSquareGame.mostAttackedSquare) {
      const game = enrichWithGameId(summary.mostAttackedSquareGame);
      const attacked = game.mostAttackedSquare;
      funStats.crosshairs = {
        white: game.white,
        black: game.black,
        gameId: game.gameId,
        square: attacked.square,
        attackers: attacked.attackers,
        whiteAttackers: attacked.whiteAttackers,
        blackAttackers: attacked.blackAttackers,
        moveNumber: attacked.moveNumber,
        move: attacked.move,
        description: `${attacked.square} under attack by ${attacked.attackers} pieces (move ${attacked.moveNumber})`
      };
    }

    // Longest Tension: Pieces that could capture each other but don't
    if (summary.longestTension) {
      const lt = enrichWithGameId(summary.longestTension);
      funStats.longestTension = {
        ...lt,
        description: `${lt.squares} pieces faced off for ${lt.moves} moves without capturing`
      };
    }

  }

  return funStats;
}

module.exports = { calculateFunStats };
