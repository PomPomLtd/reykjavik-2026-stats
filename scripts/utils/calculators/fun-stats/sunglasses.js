/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * Sunglasses Award (Light Square Captures)
 *
 * Tracks the player with the most captures on light squares.
 */

const { getPlayerNames } = require('../helpers');

/**
 * Check if a square is a light square
 * @param {string} square - Square notation (e.g., 'e4')
 * @returns {boolean} True if light square
 */
function isLightSquare(square) {
  const file = square.charCodeAt(0) - 'a'.charCodeAt(0); // 0-7
  const rank = parseInt(square[1]) - 1; // 0-7
  return (file + rank) % 2 === 1; // Light squares have odd sum
}

/**
 * Calculate sunglasses award (most light square captures)
 * @param {Array} games - Array of parsed game objects
 * @returns {Object} Sunglasses award stat
 */
function calculateSunglasses(games) {
  let sunglasses = { captures: 0, gameIndex: null, color: null };

  games.forEach((game, idx) => {
    let whiteLightCaptures = 0;
    let blackLightCaptures = 0;

    game.moveList.forEach((move) => {
      // Track light square captures
      if (move.captured && isLightSquare(move.to)) {
        if (move.color === 'w') {
          whiteLightCaptures++;
        } else {
          blackLightCaptures++;
        }
      }
    });

    // Check if this game has the most light square captures
    const players = getPlayerNames(game);
    const gameId = game.headers?.GameId || game.headers?.ChapterURL || game.headers?.Site?.split('/').pop() || null;
    if (whiteLightCaptures > sunglasses.captures) {
      sunglasses = {
        captures: whiteLightCaptures,
        gameIndex: idx,
        gameId,
        color: 'White',
        white: players.white,
        black: players.black
      };
    }

    if (blackLightCaptures > sunglasses.captures) {
      sunglasses = {
        captures: blackLightCaptures,
        gameIndex: idx,
        gameId,
        color: 'Black',
        white: players.white,
        black: players.black
      };
    }
  });

  return sunglasses.captures > 0 ? sunglasses : null;
}

module.exports = { calculateSunglasses };
