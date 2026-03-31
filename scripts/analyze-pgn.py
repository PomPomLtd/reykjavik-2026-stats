#!/usr/bin/env python3
"""
Chess PGN Analysis with Stockfish
==================================

Analyzes chess games from PGN data using Stockfish engine.
Calculates accuracy, ACPL, blunders, mistakes, and inaccuracies.

Requirements:
    pip install python-chess stockfish

Usage:
    python analyze-pgn.py < games.pgn > analysis.json
    python analyze-pgn.py --depth 15 --sample 1 < games.pgn > analysis.json

Output JSON format:
    {
        "games": [
            {
                "gameIndex": 0,
                "white": "Player A",
                "black": "Player B",
                "whiteAccuracy": 85.3,
                "blackAccuracy": 78.2,
                "whiteACPL": 25,
                "blackACPL": 45,
                "whiteMoveQuality": {"blunders": 1, "mistakes": 3, ...},
                "blackMoveQuality": {"blunders": 2, "mistakes": 4, ...},
                "biggestBlunder": {...}
            }
        ],
        "summary": {
            "accuracyKing": {...},
            "biggestBlunder": {...}
        }
    }
"""

import sys
import json
import argparse
import os
import shutil
import chess
import chess.pgn
from stockfish import Stockfish

import math
import statistics

def winning_chances(cp):
    """
    Convert centipawn evaluation to winning chances [-1, +1].
    Lichess formula from lichess-org/scalachess eval.scala.
    """
    return max(-1, min(1, 2 / (1 + math.exp(-0.00368208 * cp)) - 1))

def cp_to_win_percentage(cp):
    """
    Convert centipawn evaluation to win percentage [0, 100].
    Lichess caps centipawns at ±1000 before conversion.
    """
    capped = max(-1000, min(1000, cp))
    return 50 + 50 * winning_chances(capped)

def move_accuracy(win_before, win_after):
    """
    Calculate per-move accuracy from win percentages before/after.
    Lichess formula from AccuracyPercent.scala with +1 uncertainty bonus.
    If the position improved for the player, accuracy is 100%.
    """
    if win_after >= win_before:
        return 100.0
    win_diff = win_before - win_after
    raw = 103.1668100711649 * math.exp(-0.04354415386753951 * win_diff) + (-3.166924740191411)
    return max(0, min(100, raw + 1))  # +1 uncertainty bonus per Lichess

def classify_move(cp_before, cp_after, is_white):
    """
    Classify move quality using Lichess thresholds on winning chances [-1, +1].
    From lichess-org/lila modules/tree/src/main/Advice.scala.

    Returns: (quality, win_loss) where win_loss is on the [0, 100] win% scale.
    """
    # Winning chances on [-1, +1] scale (NOT capped at ±1000 for classification)
    prev_chances = winning_chances(cp_before)
    curr_chances = winning_chances(cp_after)

    # Delta from the mover's perspective (positive = position got worse)
    delta = prev_chances - curr_chances
    if not is_white:
        delta = -delta

    # Win percentage loss for accuracy calculation (on [0, 100] scale, capped evals)
    wp_before = cp_to_win_percentage(cp_before)
    wp_after = cp_to_win_percentage(cp_after)
    if is_white:
        win_loss = max(0, wp_before - wp_after)
    else:
        win_loss = max(0, wp_after - wp_before)

    # Lichess thresholds on winning chances scale
    if delta >= 0.3:
        return 'blunders', win_loss
    elif delta >= 0.2:
        return 'mistakes', win_loss
    elif delta >= 0.1:
        return 'inaccuracies', win_loss
    elif delta >= 0.02:
        return 'good', win_loss
    else:
        return 'excellent', win_loss

def _standard_deviation(values):
    """Population standard deviation matching Lichess Maths.scala."""
    if not values:
        return 0
    m = sum(values) / len(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))

def _harmonic_mean(values):
    """Harmonic mean with floor of 1 per value, matching Lichess Maths.scala."""
    if not values:
        return 0
    return len(values) / sum(1 / max(1, v) for v in values)

def _weighted_mean(pairs):
    """Weighted mean from (value, weight) pairs."""
    if not pairs:
        return 0
    total_w = sum(w for _, w in pairs)
    if total_w == 0:
        return 0
    return sum(v * w for v, w in pairs) / total_w

def calculate_game_accuracy(all_cps):
    """
    Calculate game accuracy using Lichess's full algorithm from AccuracyPercent.scala.

    Combines volatility-weighted mean with harmonic mean of per-move accuracies.
    Uses sliding windows to weight moves by positional volatility.

    Args:
        all_cps: list of centipawn evals for each position, starting from the
                 initial position (before move 1). Length = num_moves + 1.
                 Even indices (0, 2, 4...) are positions before white moves.
                 Odd indices (1, 3, 5...) are positions before black moves.
    Returns:
        (white_accuracy, black_accuracy) as floats
    """
    if len(all_cps) < 2:
        return 100, 100

    # Convert all positions to win percentages
    all_wp = [cp_to_win_percentage(cp) for cp in all_cps]

    num_moves = len(all_cps) - 1

    # Sliding window size: clamp(num_moves / 10, 2, 8)
    window_size = max(2, min(8, num_moves // 10))

    # Build windows for volatility weighting
    # First (window_size - 2) entries reuse the first window
    first_window = all_wp[:window_size]
    num_initial = min(window_size, len(all_wp)) - 2
    windows = [first_window] * max(0, num_initial)

    # Sliding windows
    for i in range(len(all_wp) - window_size + 1):
        windows.append(all_wp[i:i + window_size])

    # Weights = standard deviation of each window, clamped to [0.5, 12]
    weights = []
    for w in windows:
        sd = _standard_deviation(w)
        weights.append(max(0.5, min(12, sd)))

    # Compute per-move accuracy with color assignment
    white_weighted = []  # (accuracy, weight)
    black_weighted = []

    for i in range(num_moves):
        prev_wp = all_wp[i]
        next_wp = all_wp[i + 1]
        weight = weights[i] if i < len(weights) else 0.5

        is_white = (i % 2 == 0)  # move 0 = white, move 1 = black, etc.

        if is_white:
            acc = move_accuracy(prev_wp, next_wp)
            white_weighted.append((acc, weight))
        else:
            # Black's perspective: invert win percentages
            acc = move_accuracy(100 - prev_wp, 100 - next_wp)
            black_weighted.append((acc, weight))

    def color_accuracy(pairs):
        if not pairs:
            return 100
        wm = _weighted_mean(pairs)
        hm = _harmonic_mean([a for a, _ in pairs])
        return round((wm + hm) / 2, 1)

    return color_accuracy(white_weighted), color_accuracy(black_weighted)

def calculate_blunder_severity(eval_before, eval_after, eval_before_type, eval_after_type, win_loss):
    """
    Calculate blunder severity considering position context and mate threats.

    A blunder from a winning position to mate is much worse than a small cp loss in a losing position.
    Returns a severity score for comparison (higher = worse blunder).
    """
    import math

    # Base severity from win percentage loss
    severity = win_loss

    # Check if blunder leads to mate (extremely severe)
    if eval_after_type == 'mate':
        mate_in = abs(eval_after)
        # Mate threats are catastrophic - add huge penalty, scaled by how soon mate arrives
        # Mate in 1-3 moves is devastating, longer mates less so
        mate_penalty = 100 / (mate_in + 1)  # M1 = 50, M2 = 33, M3 = 25, etc.
        severity += mate_penalty

    # Check if position was winning before blunder (amplify severity)
    if eval_before_type == 'cp':
        # If player was winning by 200+ cp (or equivalent for black)
        winning_margin = abs(eval_before)
        if winning_margin > 200:
            # Blundering from a winning position is worse - multiply by how much you were winning
            # Cap the multiplier at 3x for positions > 600 cp advantage
            position_multiplier = 1 + min(2, (winning_margin - 200) / 400)
            severity *= position_multiplier
    elif eval_before_type == 'mate' and eval_before > 0:
        # Was delivering mate but blundered it away - extremely severe
        severity *= 3

    return severity

def eval_to_cp(eval_result, white_to_move):
    """
    Convert a Stockfish eval result to centipawns from WHITE's perspective.

    IMPORTANT: Stockfish returns evals from the side-to-move's perspective.
    We must negate when it's black to move so all values are consistently
    from white's perspective throughout.
    """
    if eval_result['type'] == 'cp':
        raw = eval_result['value']
    elif eval_result['type'] == 'mate':
        mate_in = eval_result['value']
        if mate_in > 0:
            raw = 100000 - mate_in
        else:
            raw = -100000 - mate_in
    else:
        raw = 0

    # Negate if black to move (Stockfish gives eval from side-to-move's perspective)
    return raw if white_to_move else -raw

def analyze_game(game, stockfish, depth=15, sample_rate=1):
    """Analyze a single game with Stockfish using Lichess-style accuracy."""

    board = game.board()
    moves = list(game.mainline_moves())

    white_cp_losses = []
    black_cp_losses = []

    white_quality = {'blunders': 0, 'mistakes': 0, 'inaccuracies': 0, 'good': 0, 'excellent': 0}
    black_quality = {'blunders': 0, 'mistakes': 0, 'inaccuracies': 0, 'good': 0, 'excellent': 0}

    white_engine_moves = 0
    black_engine_moves = 0

    biggest_blunder = None
    biggest_comeback = None
    lucky_escape = None

    # Collect all position evals (from WHITE's perspective) for game-level accuracy
    # all_cps[0] = eval of starting position, all_cps[i+1] = eval after move i
    all_cps = []

    # Eval the starting position (white to move)
    stockfish.set_fen_position(board.fen())
    initial_eval = stockfish.get_evaluation()
    all_cps.append(eval_to_cp(initial_eval, white_to_move=True))

    # Track eval history for comeback detection
    eval_history = []
    prev_eval = None

    for move_num, move in enumerate(moves):
        is_white_move = move_num % 2 == 0

        # Sample every Nth move FOR EACH PLAYER to save time
        move_index_for_player = move_num // 2
        if move_index_for_player % sample_rate != 0:
            board.push(move)
            # Still need eval after this move for accuracy calculation
            # After the move, it's the OTHER side's turn
            stockfish.set_fen_position(board.fen())
            skip_eval = stockfish.get_evaluation()
            all_cps.append(eval_to_cp(skip_eval, white_to_move=not is_white_move))
            continue

        move_san = board.san(move)

        cp_before = all_cps[-1]  # Already have eval before this move

        # Make the move
        board.push(move)

        # Get evaluation after move
        # After white moves, it's black to move (so negate); after black moves, it's white to move
        stockfish.set_fen_position(board.fen())
        eval_after = stockfish.get_evaluation()
        cp_after = eval_to_cp(eval_after, white_to_move=not is_white_move)
        all_cps.append(cp_after)

        # Classify move using Lichess thresholds
        quality, win_loss = classify_move(cp_before, cp_after, is_white_move)

        if is_white_move:
            white_quality[quality] += 1
            if quality == 'excellent':
                white_engine_moves += 1

            # ACPL: use actual centipawn loss, include mate-territory moves too
            cp_loss = max(0, cp_before - cp_after)
            # Cap at 1000 to avoid mate-score distortion in ACPL
            white_cp_losses.append(min(cp_loss, 1000))

            if quality == 'blunders':
                severity = calculate_blunder_severity(
                    cp_before, cp_after,
                    'cp', eval_after['type'], win_loss
                )
                if biggest_blunder is None or severity > biggest_blunder.get('severity', 0):
                    biggest_blunder = {
                        'moveNumber': move_num // 2 + 1,
                        'player': 'white',
                        'cpLoss': int(min(cp_loss, 10000)),
                        'winLoss': win_loss,
                        'severity': severity,
                        'move': move_san,
                        'evalBefore': cp_before,
                        'evalAfter': cp_after
                    }
        else:
            black_quality[quality] += 1
            if quality == 'excellent':
                black_engine_moves += 1

            # ACPL from black's perspective
            cp_loss = max(0, cp_after - cp_before)
            black_cp_losses.append(min(cp_loss, 1000))

            if quality == 'blunders':
                severity = calculate_blunder_severity(
                    -cp_before, -cp_after,
                    'cp', eval_after['type'], win_loss
                )
                if biggest_blunder is None or severity > biggest_blunder.get('severity', 0):
                    biggest_blunder = {
                        'moveNumber': move_num // 2 + 1,
                        'player': 'black',
                        'cpLoss': int(min(cp_loss, 10000)),
                        'winLoss': win_loss,
                        'severity': severity,
                        'move': move_san,
                        'evalBefore': cp_before,
                        'evalAfter': cp_after
                    }

        # Track lucky escape
        if prev_eval is not None:
            if prev_eval < -200 and cp_after > -50:
                escape_amount = abs(prev_eval) - abs(cp_after)
                if lucky_escape is None or escape_amount > lucky_escape.get('escapeAmount', 0):
                    lucky_escape = {
                        'player': 'white',
                        'escapeAmount': escape_amount,
                        'evalBefore': prev_eval,
                        'evalAfter': cp_after,
                        'moveNumber': move_num // 2 + 1
                    }
            if prev_eval > 200 and cp_after < 50:
                escape_amount = abs(prev_eval) - abs(cp_after)
                if lucky_escape is None or escape_amount > lucky_escape.get('escapeAmount', 0):
                    lucky_escape = {
                        'player': 'black',
                        'escapeAmount': escape_amount,
                        'evalBefore': prev_eval,
                        'evalAfter': cp_after,
                        'moveNumber': move_num // 2 + 1
                    }

        prev_eval = cp_after

        # Track eval history for comeback detection
        eval_history.append({
            'cp': cp_after,
            'type': eval_after['type'],
            'mate': eval_after.get('value') if eval_after['type'] == 'mate' else None
        })
        if len(eval_history) > 10:
            eval_history.pop(0)

        if len(eval_history) >= 5:
            cp_values = [e['cp'] for e in eval_history]
            min_eval_idx = cp_values.index(min(cp_values))
            max_eval_idx = cp_values.index(max(cp_values))

            min_eval_white = eval_history[min_eval_idx]['cp']
            max_eval_white = eval_history[max_eval_idx]['cp']

            if min_eval_white < -300 and cp_after > 300:
                swing = min(cp_after - min_eval_white, 2000)
                eval_from_str = f"M{eval_history[min_eval_idx]['mate']}" if eval_history[min_eval_idx]['type'] == 'mate' else str(min_eval_white)
                eval_to_str = f"M{eval_after.get('value')}" if eval_after['type'] == 'mate' else str(cp_after)
                if biggest_comeback is None or swing > biggest_comeback.get('swing', 0):
                    biggest_comeback = {
                        'player': 'white', 'swing': swing,
                        'evalFrom': eval_from_str, 'evalTo': eval_to_str,
                        'evalFromCp': min_eval_white, 'evalToCp': cp_after,
                        'moveNumber': move_num // 2 + 1
                    }

            if max_eval_white > 300 and cp_after < -300:
                swing = min(max_eval_white - cp_after, 2000)
                eval_from_str = f"M{eval_history[max_eval_idx]['mate']}" if eval_history[max_eval_idx]['type'] == 'mate' else str(max_eval_white)
                eval_to_str = f"M{eval_after.get('value')}" if eval_after['type'] == 'mate' else str(cp_after)
                if biggest_comeback is None or swing > biggest_comeback.get('swing', 0):
                    biggest_comeback = {
                        'player': 'black', 'swing': swing,
                        'evalFrom': eval_from_str, 'evalTo': eval_to_str,
                        'evalFromCp': max_eval_white, 'evalToCp': cp_after,
                        'moveNumber': move_num // 2 + 1
                    }

    # Calculate accuracy using full Lichess algorithm (sliding windows + volatility weighting)
    white_accuracy, black_accuracy = calculate_game_accuracy(all_cps)

    # Calculate ACPL with cap at 150 per move
    MAX_CP_LOSS_FOR_ACPL = 150

    if white_cp_losses:
        capped = [min(loss, MAX_CP_LOSS_FOR_ACPL) for loss in white_cp_losses]
        white_acpl = sum(capped) / len(capped)
    else:
        white_acpl = 0

    if black_cp_losses:
        capped = [min(loss, MAX_CP_LOSS_FOR_ACPL) for loss in black_cp_losses]
        black_acpl = sum(capped) / len(capped)
    else:
        black_acpl = 0

    return {
        'whiteACPL': round(white_acpl, 1),
        'blackACPL': round(black_acpl, 1),
        'whiteAccuracy': white_accuracy,
        'blackAccuracy': black_accuracy,
        'whiteMoveQuality': white_quality,
        'blackMoveQuality': black_quality,
        'whiteEngineMoves': white_engine_moves,
        'blackEngineMoves': black_engine_moves,
        'biggestBlunder': biggest_blunder,
        'biggestComeback': biggest_comeback,
        'luckyEscape': lucky_escape
    }

def find_stockfish_path():
    """Find Stockfish binary in common locations."""
    # Try shutil.which first (searches PATH)
    path = shutil.which('stockfish')
    if path:
        return path

    # Try common installation paths
    common_paths = [
        '/opt/homebrew/bin/stockfish',  # macOS Homebrew (Apple Silicon)
        '/usr/local/bin/stockfish',      # macOS Homebrew (Intel)
        '/usr/bin/stockfish',            # Linux apt
        '/usr/games/stockfish',          # Linux apt alternative location
    ]

    for path in common_paths:
        if os.path.exists(path):
            return path

    return 'stockfish'  # Fall back to hoping it's in PATH

def main():
    parser = argparse.ArgumentParser(description='Analyze chess PGN with Stockfish')
    parser.add_argument('--depth', type=int, default=15, help='Stockfish search depth (default: 15)')
    parser.add_argument('--sample', type=int, default=1, help='Analyze every Nth move (default: 1 = all moves)')
    parser.add_argument('--stockfish-path', type=str, default=None, help='Path to Stockfish binary (auto-detected if not specified)')
    args = parser.parse_args()

    # Auto-detect Stockfish path if not specified
    if args.stockfish_path is None:
        args.stockfish_path = find_stockfish_path()

    # Initialize Stockfish
    try:
        stockfish = Stockfish(path=args.stockfish_path, depth=args.depth)
    except Exception as e:
        print(f"Error initializing Stockfish: {e}", file=sys.stderr)
        print("Install Stockfish: brew install stockfish (macOS) or apt-get install stockfish (Linux)", file=sys.stderr)
        sys.exit(1)

    # Read PGN from stdin
    pgn_text = sys.stdin.read()

    # Parse games
    games_analyzed = []
    game_index = 0

    import io
    pgn_io = io.StringIO(pgn_text)

    # First pass: count total games
    total_games = pgn_text.count('[Event ')
    print(f"\n🔬 Stockfish Analysis Starting...", file=sys.stderr)
    print(f"📊 Total games to analyze: {total_games}", file=sys.stderr)
    print(f"⚙️  Depth: {args.depth} | Sample rate: every {args.sample} move(s)", file=sys.stderr)

    # Format estimated time in human-readable form
    min_seconds = total_games * 15
    max_seconds = total_games * 30
    min_minutes = min_seconds // 60
    min_secs = min_seconds % 60
    max_minutes = max_seconds // 60
    max_secs = max_seconds % 60

    if max_minutes > 0:
        time_estimate = f"{min_minutes}:{min_secs:02d}-{max_minutes}:{max_secs:02d} minutes"
    else:
        time_estimate = f"{min_seconds}-{max_seconds} seconds"

    print(f"⏱️  Estimated time: {time_estimate}\n", file=sys.stderr)

    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break

        white = game.headers.get('White', 'Unknown')
        black = game.headers.get('Black', 'Unknown')

        # Extract gameId from headers (GameId, ChapterURL, or Site URL)
        game_id = game.headers.get('GameId')
        if not game_id:
            game_id = game.headers.get('ChapterURL')
        if not game_id:
            site = game.headers.get('Site', '')
            game_id = site.split('/')[-1] if site else None

        # Count moves in this game
        board = game.board()
        move_count = 0
        for _ in game.mainline_moves():
            move_count += 1

        # Print progress with game info (use \r to overwrite line)
        progress_pct = ((game_index + 1) / total_games) * 100
        progress_bar = '█' * int(progress_pct / 5) + '░' * (20 - int(progress_pct / 5))

        # Truncate long names to fit on one line (shorter to avoid wrapping)
        max_name_len = 20
        white_short = white[:max_name_len] + '...' if len(white) > max_name_len else white
        black_short = black[:max_name_len] + '...' if len(black) > max_name_len else black

        # Clear line with spaces, then print progress
        progress_line = f"[{progress_bar}] {progress_pct:3.0f}% | {game_index + 1}/{total_games} | {white_short} vs {black_short}"

        # Skip games with no moves (forfeits, etc.)
        if move_count == 0:
            print(f"\r{progress_line:<100} [SKIPPED - no moves]", end='', flush=True, file=sys.stderr)
            game_index += 1
            continue

        print(f"\r{progress_line:<100}", end='', flush=True, file=sys.stderr)

        analysis = analyze_game(game, stockfish, args.depth, args.sample)

        games_analyzed.append({
            'gameIndex': game_index,
            'gameId': game_id,
            'white': white,
            'black': black,
            **analysis
        })

        game_index += 1

    print(f"\n\n✅ Analysis complete! Processed {total_games} games\n", file=sys.stderr)

    # Find accuracy king, biggest blunder, ACPL extremes, comeback king, lucky escape, stockfish buddy, and inaccuracy king
    accuracy_king = None
    biggest_blunder = None
    comeback_king = None
    lucky_escape = None
    stockfish_buddy = None
    inaccuracy_king = None
    lowest_acpl = None
    highest_acpl = None
    lowest_combined_acpl = None
    highest_combined_acpl = None

    for game_data in games_analyzed:
        # Check white accuracy
        if accuracy_king is None or game_data['whiteAccuracy'] > accuracy_king['accuracy']:
            accuracy_king = {
                'player': 'white',
                'accuracy': game_data['whiteAccuracy'],
                'acpl': game_data['whiteACPL'],
                'white': game_data['white'],
                'black': game_data['black'],
                'gameIndex': game_data['gameIndex'],
                'gameId': game_data['gameId']
            }

        # Check black accuracy
        if accuracy_king is None or game_data['blackAccuracy'] > accuracy_king['accuracy']:
            accuracy_king = {
                'player': 'black',
                'accuracy': game_data['blackAccuracy'],
                'acpl': game_data['blackACPL'],
                'white': game_data['white'],
                'black': game_data['black'],
                'gameIndex': game_data['gameIndex'],
                'gameId': game_data['gameId']
            }

        # Check white lowest ACPL
        if lowest_acpl is None or game_data['whiteACPL'] < lowest_acpl['acpl']:
            lowest_acpl = {
                'player': 'white',
                'acpl': game_data['whiteACPL'],
                'accuracy': game_data['whiteAccuracy'],
                'white': game_data['white'],
                'black': game_data['black'],
                'gameIndex': game_data['gameIndex'],
                'gameId': game_data['gameId']
            }

        # Check black lowest ACPL
        if lowest_acpl is None or game_data['blackACPL'] < lowest_acpl['acpl']:
            lowest_acpl = {
                'player': 'black',
                'acpl': game_data['blackACPL'],
                'accuracy': game_data['blackAccuracy'],
                'white': game_data['white'],
                'black': game_data['black'],
                'gameIndex': game_data['gameIndex'],
                'gameId': game_data['gameId']
            }

        # Check white highest ACPL
        if highest_acpl is None or game_data['whiteACPL'] > highest_acpl['acpl']:
            highest_acpl = {
                'player': 'white',
                'acpl': game_data['whiteACPL'],
                'accuracy': game_data['whiteAccuracy'],
                'white': game_data['white'],
                'black': game_data['black'],
                'gameIndex': game_data['gameIndex'],
                'gameId': game_data['gameId']
            }

        # Check black highest ACPL
        if highest_acpl is None or game_data['blackACPL'] > highest_acpl['acpl']:
            highest_acpl = {
                'player': 'black',
                'acpl': game_data['blackACPL'],
                'accuracy': game_data['blackAccuracy'],
                'white': game_data['white'],
                'black': game_data['black'],
                'gameIndex': game_data['gameIndex'],
                'gameId': game_data['gameId']
            }

        # Check combined ACPL
        combined_acpl = game_data['whiteACPL'] + game_data['blackACPL']

        if lowest_combined_acpl is None or combined_acpl < lowest_combined_acpl['combinedACPL']:
            lowest_combined_acpl = {
                'combinedACPL': combined_acpl,
                'whiteACPL': game_data['whiteACPL'],
                'blackACPL': game_data['blackACPL'],
                'white': game_data['white'],
                'black': game_data['black'],
                'gameIndex': game_data['gameIndex'],
                'gameId': game_data['gameId']
            }

        if highest_combined_acpl is None or combined_acpl > highest_combined_acpl['combinedACPL']:
            highest_combined_acpl = {
                'combinedACPL': combined_acpl,
                'whiteACPL': game_data['whiteACPL'],
                'blackACPL': game_data['blackACPL'],
                'white': game_data['white'],
                'black': game_data['black'],
                'gameIndex': game_data['gameIndex'],
                'gameId': game_data['gameId']
            }

        # Check biggest blunder (compare by severity, not just cpLoss)
        if game_data['biggestBlunder']:
            if biggest_blunder is None or game_data['biggestBlunder']['severity'] > biggest_blunder.get('severity', 0):
                biggest_blunder = {
                    **game_data['biggestBlunder'],
                    'white': game_data['white'],
                    'black': game_data['black'],
                    'gameIndex': game_data['gameIndex'],
                    'gameId': game_data['gameId']
                }

        # Check biggest comeback
        if game_data['biggestComeback']:
            if comeback_king is None or game_data['biggestComeback']['swing'] > comeback_king.get('swing', 0):
                comeback_king = {
                    **game_data['biggestComeback'],
                    'white': game_data['white'],
                    'black': game_data['black'],
                    'gameIndex': game_data['gameIndex'],
                    'gameId': game_data['gameId']
                }

        # Check lucky escape
        if game_data['luckyEscape']:
            if lucky_escape is None or game_data['luckyEscape']['escapeAmount'] > lucky_escape.get('escapeAmount', 0):
                lucky_escape = {
                    **game_data['luckyEscape'],
                    'white': game_data['white'],
                    'black': game_data['black'],
                    'gameIndex': game_data['gameIndex'],
                    'gameId': game_data['gameId']
                }

        # Check Stockfish Buddy (most engine-level moves)
        if stockfish_buddy is None or game_data['whiteEngineMoves'] > stockfish_buddy.get('engineMoves', 0):
            stockfish_buddy = {
                'player': 'white',
                'engineMoves': game_data['whiteEngineMoves'],
                'totalMoves': sum(game_data['whiteMoveQuality'].values()),
                'percentage': round(game_data['whiteEngineMoves'] / sum(game_data['whiteMoveQuality'].values()) * 100, 1) if sum(game_data['whiteMoveQuality'].values()) > 0 else 0,
                'white': game_data['white'],
                'black': game_data['black'],
                'gameIndex': game_data['gameIndex'],
                'gameId': game_data['gameId']
            }

        if stockfish_buddy is None or game_data['blackEngineMoves'] > stockfish_buddy.get('engineMoves', 0):
            stockfish_buddy = {
                'player': 'black',
                'engineMoves': game_data['blackEngineMoves'],
                'totalMoves': sum(game_data['blackMoveQuality'].values()),
                'percentage': round(game_data['blackEngineMoves'] / sum(game_data['blackMoveQuality'].values()) * 100, 1) if sum(game_data['blackMoveQuality'].values()) > 0 else 0,
                'white': game_data['white'],
                'black': game_data['black'],
                'gameIndex': game_data['gameIndex'],
                'gameId': game_data['gameId']
            }

        # Check Inaccuracy King (most inaccuracies)
        if inaccuracy_king is None or game_data['whiteMoveQuality']['inaccuracies'] > inaccuracy_king.get('inaccuracies', 0):
            inaccuracy_king = {
                'player': 'white',
                'inaccuracies': game_data['whiteMoveQuality']['inaccuracies'],
                'totalMoves': sum(game_data['whiteMoveQuality'].values()),
                'white': game_data['white'],
                'black': game_data['black'],
                'gameIndex': game_data['gameIndex'],
                'gameId': game_data['gameId']
            }

        if inaccuracy_king is None or game_data['blackMoveQuality']['inaccuracies'] > inaccuracy_king.get('inaccuracies', 0):
            inaccuracy_king = {
                'player': 'black',
                'inaccuracies': game_data['blackMoveQuality']['inaccuracies'],
                'totalMoves': sum(game_data['blackMoveQuality'].values()),
                'white': game_data['white'],
                'black': game_data['black'],
                'gameIndex': game_data['gameIndex'],
                'gameId': game_data['gameId']
            }

    # Output JSON
    output = {
        'games': games_analyzed,
        'summary': {
            'accuracyKing': accuracy_king,
            'biggestBlunder': biggest_blunder,
            'comebackKing': comeback_king,
            'luckyEscape': lucky_escape,
            'stockfishBuddy': stockfish_buddy,
            'inaccuracyKing': inaccuracy_king,
            'lowestACPL': lowest_acpl,
            'highestACPL': highest_acpl,
            'lowestCombinedACPL': lowest_combined_acpl,
            'highestCombinedACPL': highest_combined_acpl
        }
    }

    print(json.dumps(output, indent=2))

if __name__ == '__main__':
    main()
