import pandas as pd
import matplotlib.pyplot as plt
import ast
import numpy as np
from scipy.stats import normaltest

# Load the DataFrame
df_games = pd.read_csv('data/sevolod_games.csv')

def string_to_list(string_list):
    try:
        return ast.literal_eval(string_list)
    except ValueError:
        return [] 

# List of features to analyze
features_to_test = ['Player Time Spent', 'Attacker Score', 'Defender Score', 'Pawn Shield', 'Open Files',
                    'Mobility', 'Control of Center', 'Advanced Pawns', 'Developed Pieces', 'Space Control',
                    'Total Material', 'Doubled Pawns', 'Isolated Pawns', 'Passed Pawns', 'Piece Coordination',
                    'Forks', 'Pins', 'Skewers', 'Threats'] 

max_moves = 40
normality_results = {}

# Function to calculate average scores per move
def calculate_averages(feature_name):
    total_scores_per_move = {}
    count_per_move = {}
    
    for scores in df_games[feature_name]:
        for index, score in enumerate(scores):
            if index < max_moves: 
                if index in total_scores_per_move:
                    total_scores_per_move[index] += score
                    count_per_move[index] += 1
                else:
                    total_scores_per_move[index] = score
                    count_per_move[index] = 1

    return {move: total_scores_per_move[move] / count_per_move[move] for move in total_scores_per_move}

# Testing each feature for normality
for feature_name in features_to_test:
    df_games[feature_name] = df_games[feature_name].apply(string_to_list)
    average_scores_per_move = calculate_averages(feature_name)
    average_scores = list(average_scores_per_move.values())
    
    # Perform D’Agostino’s K-squared test
    stat, p_value = normaltest(average_scores)
    normality_results[feature_name] = p_value
    
    # Optionally plot the average scores per move number
    plt.figure(figsize=(12, 6))
    plt.plot(list(average_scores_per_move.keys()), average_scores, marker='o', linestyle='-', color='b')
    plt.title(f'Average Scores per Move for {feature_name} (Up to 40 Moves)')
    plt.xlabel('Move Number')
    plt.ylabel('Average Score')
    plt.grid(True)
    plt.xlim(0, max_moves)
    plt.show()

# Print the results
for feature, p_val in normality_results.items():
    print(f"{feature}: p-value = {p_val:.4f} ({'Non-Gaussian' if p_val < 0.05 else 'Gaussian'})")
