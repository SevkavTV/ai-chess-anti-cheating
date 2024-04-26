import pandas as pd
from sklearn.model_selection import train_test_split

from chess_com.api import fetch_games
from model.preprocess import preprocess_games
from model.features import generate_features
from model.preparation import prepare_data
from model.training import train_model
from model.evaluation import evaluate_model

if __name__ == '__main__':
    players = ["sevolod", "Moussako", "DraelicGambit", "omidabke",
               "ilgong", "lavadva", "Almas1982qazaq", "Indraindrani", 
               "mycostuff", "Tugrul107", "Edmond_baruti1", "MWonga",
               "garchola", "baxtyaromer1", "SpasRT88", "rockistired"]

    analyzed_player = "sevolod"
    game_type = "blitz"
    all_games = []

    for username in players:
        filename = f'data/{username}_games.csv'

        print(f"{username}: Fetching games...")
        if username == analyzed_player:
            history = fetch_games(username, num_months=6)
        else:
            history = fetch_games(username)
        print(f"{username}: Games were successfully received!")

        print(f"{username}: Starting preprocessing games...")
        games = preprocess_games(history, game_type, username)
        print(f"{username}: Games were successfully preprocessed!")

        print(f"{username}: Starting generating features...")
        df_games = generate_features(games)
        df_games.to_csv(filename, index=False)
        print(f"{username}: Features were successfully generated!")
        
        print(f"{username}: Starting preparing data for training...")
        df_games = prepare_data(df_games)
        print(f"{username}: Data was successfully generated!")

        df_games['Label'] = 1 if username == analyzed_player else 0
        all_games.append(df_games)

    combined_data = pd.concat(all_games, ignore_index=True)
    combined_data = combined_data.sample(frac=1).reset_index(drop=True)

    analyzed_player_games = combined_data[combined_data['Label'] == 1]
    other_player_games = combined_data[combined_data['Label'] == 0]
    
    min_games = min(len(analyzed_player_games), len(other_player_games))
    balanced_analyzed_games = analyzed_player_games.sample(n=min_games, random_state=42)
    balanced_other_games = other_player_games.sample(n=min_games, random_state=42)
    
    balanced_data = pd.concat([balanced_analyzed_games, balanced_other_games], ignore_index=True)
    balanced_data = balanced_data.sample(frac=1).reset_index(drop=True)

    train_data, test_data = train_test_split(balanced_data, test_size=0.2, random_state=42)

    print(f"{analyzed_player}: Starting training the data...")
    model = train_model(train_data)
    model.save(f'data/{analyzed_player}_model.keras')
    evaluate_model(model, test_data)
    print(f"{analyzed_player}: Model training complete and saved!")
