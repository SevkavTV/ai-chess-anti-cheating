import asyncio
from playwright.async_api import async_playwright, Page, Browser
from typing import List, Dict
from datetime import datetime


async def extract_games_history(username: str):
    async with async_playwright() as p:
        # Launch the browser in headful mode
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        username = username.lower()
        await page.goto(f'https://www.chess.com/games/archive/{username}')
        await page.wait_for_timeout(1000)
        await close_popup_if_present(page)
        await set_filters(page)

        games_metadata = await extract_metadata(page, username)
        await page.close()  # Close the initial page

        games_full = await extract_moves_and_openings(browser, games_metadata)
        games_full_sorted = sorted(games_full, key=lambda game: game['date'], reverse=True)

        await browser.close()  # Close the browser
        return games_full_sorted


async def close_popup_if_present(page: Page):
    # Check for the presence of a button with aria-label="Close"
    close_buttons = await page.query_selector_all('button[aria-label="Close"]')
    if close_buttons:
        # Click the first close button found
        await close_buttons[0].click()


async def set_filters(page: Page, years=0, months=1):
    # Select 'live' in the game type dropdown
    await page.select_option('select[name="gameType"]', 'live')

    # Click on the "allLiveType" checkbox
    await page.click('input#allLiveType')

    # Click on the "bullet" and "blitz" checkboxes
    await page.click('input#bullet')
    await page.click('input#blitz')


    # Click on the startDate input field to open the datepicker
    await page.click('input[name="startDate[date]"]')

    # Click on the header to navigate to the month selection
    await page.click('button[data-datepicker-header]')

    # Click on the header again to navigate to the year selection
    await page.click('button[data-datepicker-header]')

    # Calculate the previous year
    year = datetime.now().year - years

    # Click on the div for the previous year
    await page.click(f'div[data-datepicker-year="{year}"]')
    # Calculate the current month
    month = datetime.now().month - months

    # Click on the div for the current month
    await page.click(f'div[datepicker-month="{month-1}"]')

    day = datetime.now().day
    date_string = f"{year}-{month}-{day}"

    print(date_string)
    selector = f'time[datetime="{date_string}"]'
    await page.click(selector)

    await page.click("div.games-search-sidebar-range-field button[type='submit']")


async def extract_metadata(page: Page, username: str):
    game_data = []

    while True:
        await page.wait_for_timeout(1000)
        game_rows = await page.query_selector_all('tr[data-board-popover]')
        for row in game_rows:
            # Extract game URL
            link_element = await row.query_selector('a.archive-games-background-link')
            game_url = await link_element.get_attribute('href') if link_element else None

            # Extract the game type (Bullet or Blitz)
            bullet_element = await row.query_selector('.icon-font-chess.archive-games-game-icon.bullet')
            blitz_element = await row.query_selector('.icon-font-chess.archive-games-game-icon.blitz')
            game_type = 'Bullet' if bullet_element else ('Blitz' if blitz_element else 'Unknown')

            # Extract game date
            date_element = await row.query_selector('.archive-games-date-cell')
            date_string = await date_element.inner_text() if date_element else None
            game_date = datetime.strptime(date_string, '%b %d, %Y').date() if date_string else None

            # Extract player information
            player_infos = await row.query_selector_all('.user-tagline-component.archive-games-user-info')
            if player_infos:
                white_player_element = await player_infos[0].query_selector('.user-tagline-username')
                white_player_username = (await white_player_element.inner_text()).lower()

                white_rating_element = await player_infos[0].query_selector('.user-tagline-rating')
                white_player_rating = (await white_rating_element.inner_text()).strip('()')

                black_player_element = await player_infos[1].query_selector('.user-tagline-username')
                black_player_username = (await black_player_element.inner_text()).lower()

                black_rating_element = await player_infos[1].query_selector('.user-tagline-rating')
                black_player_rating = (await black_rating_element.inner_text()).strip('()')

                if username == white_player_username:
                    player_color = 'White'
                    player_rating = white_player_rating
                    opponent_name = black_player_username
                    opponent_rating = black_player_rating
                else:
                    player_color = 'Black'
                    player_rating = black_player_rating
                    opponent_name = white_player_username
                    opponent_rating = white_player_rating

            # Extract game result
            result_icon = await row.query_selector('.archive-games-result-icon')
            game_result = 'No Result'
            if result_icon:
                class_list = await result_icon.get_attribute('class')
                if 'archive-games-result-lost' in class_list:
                    game_result = 'Lost'
                elif 'archive-games-result-won' in class_list:
                    game_result = 'Won'
                elif 'archive-games-result-draw' in class_list:
                    game_result = 'Draw'

            # Store the extracted data
            game_data.append({
                'url': game_url,
                'date': game_date,
                'result': game_result,
                'player_color': player_color,
                'player_rating': player_rating,
                'opponent_name': opponent_name,
                'opponent_rating': opponent_rating,
                'type': game_type
            })

        # Move to next page if possible
        next_page_button = await page.query_selector('button[aria-label="Next Page"]')
        if next_page_button and not await next_page_button.is_disabled():
            await next_page_button.click()
            await page.wait_for_load_state("networkidle")
        else:
            break

    return game_data


async def extract_moves_and_openings(browser: Browser, games: List[Dict]):
    num_tasks = 4  # Maximum number of concurrent tasks
    games_per_task = len(games) // num_tasks

    tasks = []
    for i in range(num_tasks):
        start_index = i * games_per_task
        # For the last task, include any remaining games
        end_index = None if i == num_tasks - 1 else (i + 1) * games_per_task
        chunk = games[start_index:end_index]
        task = asyncio.create_task(process_games_chunk(browser, chunk, i+1))
        tasks.append(task)

    # Wait for all tasks to complete and collect their results
    processed_chunks = await asyncio.gather(*tasks)

    # Concatenate all chunks into a single list
    combined_games = [game for chunk in processed_chunks for game in chunk]

    return combined_games


async def process_games_chunk(browser: Browser, games_chunk: List[Dict], chunk_num: int):
    chunk_size = 20  # Maximum number of games per browser context
    for batch_start in range(0, len(games_chunk), chunk_size):
        context = await browser.new_context()
        async with context:
            for ind in range(batch_start, min(batch_start + chunk_size, len(games_chunk))):
                try:
                    game = games_chunk[ind]
                    page = await context.new_page()
                    async with page:
                        await page.goto(game['url'])
                        await page.wait_for_timeout(5000)

                        moves_data = []
                        move_elements = await page.query_selector_all('.move')
                        for move_element in move_elements:
                            move_number = await move_element.get_attribute('data-whole-move-number')
                            
                            white_move_element = await move_element.query_selector('.white.node')
                            white_time_element = await move_element.query_selector('.time-white')             
                            if white_move_element and white_time_element:
                                white_move_text = await white_move_element.inner_text()
                                white_time_text = await white_time_element.inner_text()
                                moves_data.append({
                                    'move_number': move_number,
                                    'color': 'White',
                                    'move': white_move_text,
                                    'time': white_time_text
                                })

                            black_move_element = await move_element.query_selector('.black.node')
                            black_time_element = await move_element.query_selector('.time-black')
                            if black_move_element and black_time_element:
                                black_move_text = await black_move_element.inner_text()
                                black_time_text = await black_time_element.inner_text()
                                moves_data.append({
                                    'move_number': move_number,
                                    'color': 'Black',
                                    'move': black_move_text,
                                    'time': black_time_text
                                })

                        
                        if len(moves_data) < 2:  # Less than 1 move for each player
                            print(f"Skipping game with less than 2 moves: {game['url']}")
                            games_chunk.remove(game)
                            continue
                        else:
                            opening_name = "Starting Position"
                            while opening_name == "Starting Position":
                                opening_name_element = await page.query_selector("span.eco-opening-name") 
                                if opening_name_element:
                                    opening_name = await opening_name_element.inner_text()
                                await page.wait_for_timeout(500)

                            game['moves'] = moves_data
                            game['opening'] = opening_name
                except Exception as e:
                    print(f"There was an error processing game with url: {game['url']}: {e}")
                    continue

                print(f'Chunk {chunk_num}: Already processed {ind+1} from {len(games_chunk)} games!')

    return games_chunk
