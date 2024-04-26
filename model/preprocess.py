import re
import io
import chess.pgn

def identify_result(result, player_color):
    if result == '1-0':
        if player_color == "white":
            return 1
        else:
            return 0
    elif result == '0-1':
        if player_color == "white":
            return 0
        else:
            return 1
    else:
        return 0.5
    
def extract_opening_name(eco_url):
    parts = eco_url.split('/')
    if parts:
        return parts[-1].replace('-', ' ')
    return "Unknown"

def convert_pgn_clock_to_seconds(clock_str):
    h, m, s = clock_str.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

def extract_time_from_node(node):
    clock_pattern = re.compile(r'\[%clk (\d+:\d+:\d+(\.\d+)?)\]')
    match = clock_pattern.search(node.comment)
    if match:
        clock_str = match.group(1)
        return convert_pgn_clock_to_seconds(clock_str)
    return None

def has_moves(game_obj: chess.pgn.Game):
    for _ in game_obj.mainline():
        return True
    return False

def extract_moves_fens_and_times(game_obj: chess.pgn.Game, player_color):
    board = game_obj.board()
    player_moves, opponent_moves = [], []
    player_fens, opponent_fens = [], []
    player_times, opponent_times = [], []

    time_control = game_obj.headers["TimeControl"]
    if '+' in time_control:
        initial_time, increment = map(int, time_control.split("+"))
    else:
        initial_time = int(time_control)
        increment = 0

    player_last_time, opponent_last_time = initial_time, initial_time
    is_player_turn = (player_color == 'white')

    move_num = 0
    for node in game_obj.mainline():
        move = node.move
        san_move = board.san(move) 
        board.push(move)  
        fen = board.fen()

        # Extract time spent from node comment
        time_spent = extract_time_from_node(node)
        if time_spent is not None:
            if is_player_turn:
                # Player's move
                time_diff = player_last_time - time_spent + increment
                player_last_time = time_spent
                player_moves.append(san_move)
                player_fens.append(fen)
                player_times.append(round(time_diff, 1))
            else:
                # Opponent's move
                time_diff = opponent_last_time - time_spent + increment
                opponent_last_time = time_spent
                opponent_moves.append(san_move)
                opponent_fens.append(fen)
                opponent_times.append(round(time_diff, 1))

            move_num += 1
            is_player_turn = not is_player_turn

    total_moves_count = move_num // 2 + move_num % 2

    return total_moves_count, player_moves, player_times, opponent_moves, opponent_times, player_fens, opponent_fens

def preprocess_game(game, analyzed_game_type, username):
    pgn_reader = io.StringIO(game.get('pgn', ''))
    game_obj  = chess.pgn.read_game(pgn_reader)
    if not has_moves(game_obj):
        return None

    url = game_obj.headers['Link']
    game_type = game['time_class']
    if game_type != analyzed_game_type:
        return None

    player_color = 'white' if game_obj.headers['White'].lower() == username.lower() else 'black'
    result = identify_result(game_obj.headers['Result'], player_color)
    opening = extract_opening_name(game_obj.headers['ECOUrl'])
    player_rating = game_obj.headers['WhiteElo' if player_color == 'white' else 'BlackElo']
    opponent_rating = game_obj.headers['BlackElo' if player_color == 'white' else 'WhiteElo']
    
    moves_count, player_moves, player_times, opponent_moves, opponent_times, player_fens, opponent_fens = extract_moves_fens_and_times(game_obj, player_color)

    if moves_count > 2:
        return {
            'URL': url, 
            'Color': player_color,
            'Result': result, 
            'Opening': opening, 
            'Player Rating': player_rating, 
            'Opponent Rating': opponent_rating,
            'Move Numbers': moves_count, 
            'Player Moves': player_moves, 
            'Opponent Moves': opponent_moves, 
            'Player Time Spent': player_times, 
            'Opponent Time Spent': opponent_times, 
            'Player FENs': player_fens, 
            'Opponent FENs': opponent_fens
        }
    else:
        return None
        
def preprocess_games(games, analyzed_game_type, username):
    processed_games = []
    for game in games:
        processed_game = preprocess_game(game, analyzed_game_type, username)
        if processed_game:
            processed_games.append(processed_game)
    return processed_games
