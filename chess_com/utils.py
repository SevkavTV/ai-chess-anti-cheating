import csv

def save_to_csv(games, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # Header row
        writer.writerow(['URL', 'Date', 'Result', 'Player Color', 'Player Rating', 'Opponent Name', 'Opponent Rating', 'Type', 'Moves', 'Opening'])

        for game in games:
            # Format the moves
            moves = '; '.join([f"{m['move_number']}. {m['color']} {m['move']} ({m['time']}s)" for m in game['moves']])
            
            # Write each game's details
            writer.writerow([
                game['url'],
                game['date'] if isinstance(game['date'], str) else game['date'].strftime("%Y-%m-%d"),  # Format date
                game['result'],
                game['player_color'],
                game['player_rating'],
                game['opponent_name'],
                game['opponent_rating'],
                game['type'],
                moves,
                game['opening']
            ])