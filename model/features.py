import chess
import multiprocessing
import pandas as pd

def parallel_evaluate_fens(all_fens_with_index):
    """
    Evaluates all FENs using multiple processes for efficiency.
    """
    num_cores = multiprocessing.cpu_count()
    chunk_size = len(all_fens_with_index) // num_cores
    fens_chunks = [all_fens_with_index[i:i + chunk_size] for i in range(0, len(all_fens_with_index), chunk_size)]

    with multiprocessing.Pool(processes=num_cores) as pool:
        results = pool.map(evaluate_positions, fens_chunks)

    return [item for sublist in results for item in sublist]

def evaluate_positions(fens_with_index):
    """
    Evaluates a chunk of FENs using a chess engine to compute specific game metrics.
    """
    evaluations = []
    for (game_index, fen) in fens_with_index:
        board = chess.Board(fen)
        game_metrics = compile_game_metrics(board)
        evaluations.append((game_index, game_metrics))

    return evaluations

def compile_game_metrics(board):
    """
    Compiles various game metrics from the board state.
    """
    return {
        **compute_king_safety_metrics(board),
        **compute_piece_activity_metrics(board),
        **compute_material_balance_metrics(board),
        **compute_positional_features_metrics(board),
        **compute_tactical_features(board)
    }

# KING SAFETY FEATURES
def compute_king_safety_metrics(board):
    """
    Computes king safety metrics for both the player who just moved and the player who is about to move.
    """
    current_turn_king_square = board.king(not board.turn)
    next_turn_king_square = board.king(board.turn)
    adjacent_squares_current = squares_around(current_turn_king_square)
    adjacent_squares_next = squares_around(next_turn_king_square)
    
    piece_weights = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}

    # Calculate weighted threat score from attackers for the player who is about to move
    attacker_score = 0
    for square in adjacent_squares_next:
        attackers = board.attackers(not board.turn, square)  # board.turn is the current player, so attackers are from the current player
        attacker_score += sum(piece_weights.get(board.piece_at(attacker).piece_type, 0) for attacker in attackers)

    # Calculate weighted defense score from defenders for the player who just moved
    defender_score = 0
    for square in adjacent_squares_current:
        defenders = board.attackers(not board.turn, square)  # not board.turn are attackers from the next player, defending the current player
        defender_score += sum(piece_weights.get(board.piece_at(defender).piece_type, 0) for defender in defenders)

    # Calculate pawn shield strength and open files for the king of the player who just moved
    pawn_shield = compute_pawn_shield_strength(board, current_turn_king_square)
    open_files = compute_open_files_near_king(board, current_turn_king_square)

    return {
        'Attacker Score': attacker_score,
        'Defender Score': defender_score,
        'Pawn Shield': pawn_shield,
        'Open Files': open_files
    }

def squares_around(square):
    """
    Returns a list of all squares around a given square within the bounds of the board.
    """
    file = chess.square_file(square)
    rank = chess.square_rank(square)
    directions = [
        (-1, -1), (-1, 0), (-1, 1),  # squares above
        (0, -1),         (0, 1),     # squares to the left and right
        (1, -1), (1, 0), (1, 1)      # squares below
    ]
    result = []
    for df, dr in directions:
        f, r = file + df, rank + dr
        if 0 <= f < 8 and 0 <= r < 8:  # Ensure the new file and rank are on the board
            result.append(chess.square(f, r))
    return result

def compute_pawn_shield_strength(board, king_square):
    """
    Evaluates the pawn structure around the king for shielding effectiveness.
    """
    pawn_shield_strength = 0
    friendly_pawns = board.pieces(chess.PAWN, not board.turn)
    for pawn_square in friendly_pawns:
        if chess.square_distance(pawn_square, king_square) == 1:
            pawn_shield_strength += 1
    return pawn_shield_strength

def compute_open_files_near_king(board, king_square):
    """
    Counts the number of open or semi-open files adjacent to the king's file.
    """
    open_files = 0
    king_file = chess.square_file(king_square)
    for file_offset in [-1, 0, 1]:
        file = king_file + file_offset
        if 0 <= file <= 7:
            if is_file_open_or_semi_open(board, file, not board.turn):
                open_files += 1
    return open_files

def is_file_open_or_semi_open(board, file, color):
    """
    Determines if a file is open or semi-open for the given color.
    """
    for rank in range(8):
        square = chess.square(file, rank)
        piece = board.piece_at(square)
        if piece and piece.piece_type == chess.PAWN and piece.color == color:
            return False
    return True

# PIECE ACTIVITY FEATURES
def compute_piece_activity_metrics(board):
    """
    Measures the activity level of pieces on the board, focusing on mobility, comprehensive control of the center
    (including pawn influence), piece development, and strategic space control for the player who just moved.
    """
    # Temporarily switch to the player who just moved
    board.turn = not board.turn

    center_squares = [chess.E4, chess.D4, chess.E5, chess.D5]
    piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}

    mobility = sum(piece_values[board.piece_at(move.from_square).piece_type] for move in board.legal_moves)

    control_of_center = 0
    for square in center_squares:
        if board.is_attacked_by(board.turn, square):
            control_of_center += sum(piece_values.get(board.piece_at(attacker).piece_type, 0)
                                     for attacker in board.attackers(board.turn, square)
                                     if board.piece_at(attacker))
        
        piece = board.piece_at(square)
        if piece and piece.color == board.turn:
            control_of_center += piece_values.get(piece.piece_type, 0)

    advanced_pawns = sum(1 for pawn in board.pieces(chess.PAWN, board.turn) 
                         if (chess.square_rank(pawn) < 4 if board.turn == chess.BLACK else chess.square_rank(pawn) > 3))

    developed_pieces = calculate_developed_pieces(board)

    space_control = sum(1 for square in chess.SQUARES if board.is_attacked_by(board.turn, square))

    board.turn = not board.turn

    return {
        'Mobility': mobility,
        'Control of Center': control_of_center,
        'Advanced Pawns': advanced_pawns,
        'Developed Pieces': developed_pieces,
        'Space Control': space_control
    }

def calculate_developed_pieces(board):
    """
    Counts the number of pieces moved from their initial positions, suggesting piece development.
    """
    initial_positions = get_initial_positions(board.turn)
    developed_pieces = 0
    for piece_type, positions in initial_positions.items():
        for position in positions:
            if board.piece_at(position) is None or board.piece_at(position).piece_type != piece_type:
                developed_pieces += 1
    return developed_pieces

def get_initial_positions(color):
    """
    Returns the initial positions for all pieces based on color.
    """
    return {
        chess.PAWN: [chess.A2, chess.B2, chess.C2, chess.D2, chess.E2, chess.F2, chess.G2, chess.H2] if color == chess.WHITE else [chess.A7, chess.B7, chess.C7, chess.D7, chess.E7, chess.F7, chess.G7, chess.H7],
        chess.KNIGHT: [chess.B1, chess.G1] if color == chess.WHITE else [chess.B8, chess.G8],
        chess.BISHOP: [chess.C1, chess.F1] if color == chess.WHITE else [chess.C8, chess.F8],
        chess.ROOK: [chess.A1, chess.H1] if color == chess.WHITE else [chess.A8, chess.H8],
        chess.QUEEN: [chess.D1] if color == chess.WHITE else [chess.D8],
        chess.KING: [chess.E1] if color == chess.WHITE else [chess.E8]
    }

def compute_material_balance_metrics(board):
    """
    Calculates the total material and imbalance between the players, from the perspective of the player
    who just moved.
    """
    # Temporarily reverse the turn to evaluate from the perspective of the player who just moved
    board.turn = not board.turn

    # Initialize dictionaries to store piece counts
    piece_counts = {color: {piece_type: len(board.pieces(piece_type, color)) for piece_type in chess.PIECE_TYPES}
                    for color in [chess.WHITE, chess.BLACK]}

    # Assign values to pieces for total material calculation
    piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
    total_material = sum((piece_counts[board.turn][pt] - piece_counts[not board.turn][pt]) * value
                         for pt, value in piece_values.items() if pt != chess.KING)  # Kings are typically not counted

    # Restore the original turn after calculations
    board.turn = not board.turn

    return {
        'Total Material': total_material,
    }

# POSITIONAL FEATURES
def compute_positional_features_metrics(board):
    """
    Assesses various positional features including pawn structure and piece coordination.
    Calculations are done from the perspective of the player who just moved.
    """
    # Reverse turn to assess the state from the perspective of the player who just moved
    board.turn = not board.turn

    pawn_structure = compute_pawn_structure_metrics(board)
    piece_coordination = compute_piece_coordination_metrics(board)
    
    # Restore the turn to the original state after calculation
    board.turn = not board.turn

    return {
        **pawn_structure,  # Merge dictionaries directly
        'Piece Coordination': piece_coordination
    }


def compute_pawn_structure_metrics(board):
    """
    Evaluates the pawn structure for strengths and weaknesses for the player who just moved.
    """
    doubled_pawns = 0
    isolated_pawns = 0
    passed_pawns = 0
    for square in board.pieces(chess.PAWN, board.turn):
        file = chess.square_file(square)
        rank = chess.square_rank(square)

        # Check for doubled pawns
        file_pawns = [sq for sq in board.pieces(chess.PAWN, board.turn) if chess.square_file(sq) == file]
        if len(file_pawns) > 1 and square in file_pawns:
            doubled_pawns += 1

        # Check for isolated pawns
        adjacent_files = []
        if file > 0:
            adjacent_files.extend([sq for sq in board.pieces(chess.PAWN, board.turn) if chess.square_file(sq) == file - 1])
        if file < 7:
            adjacent_files.extend([sq for sq in board.pieces(chess.PAWN, board.turn) if chess.square_file(sq) == file + 1])
        if not adjacent_files:
            isolated_pawns += 1

        # Check for passed pawns
        if board.turn == chess.WHITE:
            ahead_squares = [chess.square(file, r) for r in range(rank + 1, 8)]
        else:
            ahead_squares = [chess.square(file, r) for r in range(rank - 1, -1, -1)]

        if all(board.piece_at(sq) == None or board.piece_at(sq).color == board.turn for sq in ahead_squares):
            passed_pawns += 1

    return {
        'Doubled Pawns': doubled_pawns,
        'Isolated Pawns': isolated_pawns,
        'Passed Pawns': passed_pawns
    }


def compute_piece_coordination_metrics(board):
    """
    Measures how well pieces protect each other.
    """
    piece_coordination = 0
    for square in board.piece_map():
        if board.piece_at(square).color == board.turn:  # Ensure to count coordination for the current player's pieces
            defended_pieces = sum(1 for defended_square in board.attackers(board.turn, square)
                                  if board.piece_at(defended_square).color == board.turn)
            piece_coordination += defended_pieces

    return piece_coordination

# TACTICAL FEATURES
def compute_tactical_features(board):
    """
    Computes tactical features based on the current board state for the player who just moved.
    """
    # Reverse turn to calculate for the player who just moved
    board.turn = not board.turn

    forks = compute_forks(board)
    pins, skewers = compute_pins_and_skewers(board)
    threats = compute_threats(board)

    # Restore the original turn after calculations
    board.turn = not board.turn

    return {
        'Forks': forks,
        'Pins': pins,
        'Skewers': skewers,
        'Threats': threats
    }

def compute_forks(board):
    """
    More accurately detects forks where a single piece attacks two or more high-value pieces.
    """
    forks = 0
    opponent_color = not board.turn
    value_threshold = 3 

    for move in board.legal_moves:
        board.push(move)
        moving_piece = board.piece_at(move.to_square)
        if not moving_piece:
            board.pop()
            continue

        attacked_squares = set()
        for target_square in board.attackers(board.turn, move.to_square):
            if board.piece_at(target_square) and board.color_at(target_square) == opponent_color:
                attacked_squares.add(target_square)

        if len(attacked_squares) >= 2 and any(board.piece_at(sq).piece_type >= value_threshold for sq in attacked_squares):
            forks += 1

        board.pop()
    return forks

def compute_pins_and_skewers(board):
    """
    Uses the board's pin and skewer information.
    """
    pins = 0
    skewers = 0
    for square in board.piece_map():
        if board.is_pinned(board.turn, square):
            pins += 1
        if is_potential_skewer(board, square):
            skewers += 1
    return pins, skewers

def compute_threats(board):
    """
    Counts the number of legal moves that are captures, indicating direct attacks.
    """
    threats = 0
    for move in board.legal_moves:
        if board.is_capture(move):
            threats += 1
    return threats

def is_valid_square(square):
    """
    Checks if a square index is within the valid range of a standard chess board.
    """
    return 0 <= square < 64  # Valid square indices range from 0 (a1) to 63 (h8)

def is_potential_skewer(board, square):
    piece = board.piece_at(square)
    if piece is None:
        return False

    directions = [8, -8, 1, -1, 9, 7, -7, -9]  # Directions for north, south, east, west, and diagonals
    piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}

    for direction in directions:
        first_piece_encountered = None
        current_square = square + direction
        while is_valid_square(current_square):
            encountered_piece = board.piece_at(current_square)
            if encountered_piece:
                if first_piece_encountered is None:
                    first_piece_encountered = encountered_piece
                elif encountered_piece.color == piece.color:
                    # Check if the first piece encountered is less valuable than this one
                    if piece_values[encountered_piece.piece_type] > piece_values[first_piece_encountered.piece_type]:
                        return True
                    break
                else:
                    break  # Any subsequent pieces of opposite color stop the skewer check
            current_square += direction

    return False

def encode_openings(game_opening):
    """
    Encodes the opening of a game into one-hot format based on a predefined list of openings.
    """
    openings_list = [
        "Sicilian Defense", "Italian Game", "Ruy Lopez", "French Defense", "Caro Kann Defense",
        "Queens Pawn Opening", "Kings Indian Defense", "Old Indian Defense", "Modern Defense",
        "Nimzowitsch Defense", "English Opening", "Slav Defense", "Scandinavian Defense", "Pirc Defense", 
        "Dutch Defense", "Kings Gambit", "London System", "Philidor Defense", "Benoni Defense", 
        "Alekhines Defense", "Scotch Game", "Vienna Game", "Grunfeld Defense", "Reti Opening"
    ]

    encoded = {opening: 0 for opening in openings_list + ['Other']}    
    matched_opening = 'Other'

    for opening in openings_list:
        if opening in game_opening:
            matched_opening = opening
            break

    encoded[matched_opening] = 1
    return encoded

def generate_features(games):
    """
    Generates features for each game and compiles them into a DataFrame.
    """
    all_fens_with_index = []
    for game_index, game in enumerate(games):
        all_fens_with_index.extend((game_index, fen) for fen in game['Player FENs'])

        openings = encode_openings(game['Opening'])

        for opening, value in openings.items():
            game[opening] = [value] * len(game['Player Moves'])

    features = parallel_evaluate_fens(all_fens_with_index)

    for game_index, game_metrics in features:
        game = games[game_index]
        for key, value in game_metrics.items():
            game.setdefault(f'{key}', []).append(value)

    return pd.DataFrame(games)

