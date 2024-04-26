import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler

def drop_and_rename_columns(df_games):
    """ Drop unused columns and rename some for clarity. """
    columns_to_drop = ['URL', 'Color', 'Result', 'Opening', 'Player Rating', 'Opponent Rating',
                       'Move Numbers', 'Player Moves', 'Opponent Moves', 'Opponent Time Spent', 'Player FENs', 'Opponent FENs']
    
    df_games.drop(columns=columns_to_drop, inplace=True)
    df_games.rename(columns={'Player Time Spent': 'Time Spent'}, inplace=True)
    return df_games

def scale_features(df_games):
    """ Apply standardization or normalization to specific features within list structure. """
    features_standardize = ['Time Spent', 'Mobility', 'Control of Center', 'Space Control', 'Forks', 'Threats']
    features_normalize = ['Attacker Score', 'Defender Score', 'Pawn Shield', 'Open Files', 'Advanced Pawns',
                          'Developed Pieces','Total Material', 'Piece Coordination', 'Doubled Pawns', 
                          'Isolated Pawns', 'Passed Pawns', 'Pins', 'Skewers']

    scaler = StandardScaler()
    min_max_scaler = MinMaxScaler()

    for feature in features_standardize:
        combined_list = np.concatenate(df_games[feature].tolist())
        scaled_list = scaler.fit_transform(combined_list.reshape(-1, 1)).flatten()
        lengths = df_games[feature].apply(len)
        positions = np.cumsum(lengths)
        df_games[feature] = [list(scaled_list[pos-length:pos]) for pos, length in zip(positions, lengths)]

    for feature in features_normalize:
        combined_list = np.concatenate(df_games[feature].tolist())
        scaled_list = min_max_scaler.fit_transform(combined_list.reshape(-1, 1)).flatten()
        lengths = df_games[feature].apply(len)
        positions = np.cumsum(lengths)
        df_games[feature] = [list(scaled_list[pos-length:pos]) for pos, length in zip(positions, lengths)]

    return df_games

def filter_games(df_games):
    """ Filter out games with fewer than 10 moves and trim long games to 40 moves. """
    df_games = df_games[df_games['Time Spent'].apply(len) >= 10]
    df_games = df_games.apply(lambda x: x.apply(lambda y: y[:40] if len(y) > 40 else y))
    return df_games

def prepare_data(df_games):
    """ Main function to prepare data by invoking modular functions. """
    df_games = drop_and_rename_columns(df_games)
    df_games = scale_features(df_games)
    df_games = filter_games(df_games)

    return df_games
