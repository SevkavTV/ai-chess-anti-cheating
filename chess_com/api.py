from chessdotcom import Client, get_player_games_by_month
import datetime

Client.request_config["headers"]["User-Agent"] = (
    "Chess Analysis (seva.archakov@gmail.com)"
)

def fetch_games(username, num_years=0, num_months=1):
    all_games = []

    # Calculate the start date
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=(365 * num_years + 30 * num_months))

    # Iterate over the months from the start date to the end date
    year = start_date.year
    month = start_date.month
    while (year < end_date.year) or (year == end_date.year and month <= end_date.month):
        # Format the month correctly
        formatted_month = f"{month:02d}"

        # Fetch games for the specific month and year
        response = get_player_games_by_month(username, year, formatted_month)
        games = response.json['games']
        all_games.extend(games)

        # Move to the next month
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1


    return all_games
