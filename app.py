from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)
CORS(app)

def convert_height_to_feet_inches(height_inches):
    """Convert height from inches to feet'inches" format (e.g., 71 -> 5'11")"""
    if not height_inches or height_inches == '':
        return ''
    try:
        inches = int(height_inches)
        feet = inches // 12
        remaining_inches = inches % 12
        return f"{feet}'{remaining_inches}\""
    except:
        return height_inches  # Return original if conversion fails

def get_sleeper_players():
    """Fetch all NFL players from Sleeper API"""
    try:
        response = requests.get('https://api.sleeper.app/v1/players/nfl', timeout=30)
        response.raise_for_status()
        all_players = response.json()
        
        # Filter for QB, RB, WR, TE only and age <= 45
        filtered_players = {}
        target_positions = ['QB', 'RB', 'WR', 'TE']
        
        for player_id, player_data in all_players.items():
            position = player_data.get('position', '')
            
            if position in target_positions:
                # Calculate age if birthdate available
                age = None
                birth_date = player_data.get('birth_date')
                if birth_date:
                    try:
                        birth_year = int(birth_date.split('-')[0])
                        current_year = datetime.now().year
                        age = current_year - birth_year
                    except:
                        pass
                
                # Filter by age (<=45) if age is available
                if age is None or age <= 45:
                    filtered_players[player_id] = player_data
        
        return filtered_players
    except Exception as e:
        print(f"Error fetching Sleeper players: {e}")
        return {}

def get_selenium_driver():
    """Create and configure a headless Chrome driver for web scraping"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.page_load_strategy = 'eager'  # Don't wait for all resources
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)  # 30 second page load timeout
        return driver
    except Exception as e:
        print(f"Error creating Selenium driver: {e}")
        return None

def get_league_name(league_id):
    """Get the name of a league from Sleeper API"""
    try:
        response = requests.get(f'https://api.sleeper.app/v1/league/{league_id}', timeout=10)
        if response.status_code == 200:
            league_data = response.json()
            return league_data.get('name', f'League {league_id}')
        else:
            return f'League {league_id}'
    except Exception as e:
        print(f"Error fetching league name for {league_id}: {e}")
        return f'League {league_id}'

def get_user_roster(username, league_id):
    """Get roster information for a specific user in a league"""
    try:
        # Get user ID from username
        user_response = requests.get(f'https://api.sleeper.app/v1/user/{username}', timeout=10)
        if user_response.status_code != 200:
            print(f"Failed to fetch user {username}: HTTP {user_response.status_code}")
            return "invalid_user", None, None
        user_data = user_response.json()
        user_id = user_data.get('user_id')
        
        if not user_id:
            print(f"No user_id found for username {username}")
            return "invalid_user", None, None
        
        # Get league information to get the league name
        league_name = get_league_name(league_id)
        
        # Get all rosters for the league
        rosters_response = requests.get(f'https://api.sleeper.app/v1/league/{league_id}/rosters', timeout=10)
        if rosters_response.status_code == 404:
            print(f"League {league_id} not found - invalid league ID")
            return "invalid_league", None, None
        elif rosters_response.status_code != 200:
            print(f"Failed to fetch rosters for league {league_id}: HTTP {rosters_response.status_code}")
            return "error", None, None
        
        rosters = rosters_response.json()
        
        # Get league users to map owner_id to username
        users_response = requests.get(f'https://api.sleeper.app/v1/league/{league_id}/users', timeout=10)
        if users_response.status_code != 200:
            print(f"Failed to fetch users for league {league_id}: HTTP {users_response.status_code}")
            return "error", None, None
        league_users = users_response.json()
        
        # Create owner_id to username mapping
        owner_to_username = {user['user_id']: user.get('display_name', user.get('username', 'Unknown')) 
                            for user in league_users}
        
        # Create player_id to owner mapping
        player_ownership = {}
        user_roster = set()
        
        for roster in rosters:
            owner_id = roster.get('owner_id')
            players = roster.get('players', [])
            
            for player_id in players:
                if owner_id == user_id:
                    user_roster.add(player_id)
                player_ownership[player_id] = owner_to_username.get(owner_id, 'Unknown')
        
        return user_roster, player_ownership, league_name
    except Exception as e:
        print(f"Error fetching roster for {username} in league {league_id}: {e}")
        import traceback
        traceback.print_exc()
        return "error", None, None

def scrape_fantasy_pros():
    """Scrape Fantasy Pros dynasty rankings using Selenium"""
    rankings = {}
    driver = None
    try:
        print("Attempting to scrape Fantasy Pros with Selenium...")
        driver = get_selenium_driver()
        if not driver:
            print("Failed to create Selenium driver for Fantasy Pros")
            return rankings
        
        url = 'https://www.fantasypros.com/nfl/rankings/dynasty-overall.php'
        driver.get(url)
        
        # Wait for table to load (up to 15 seconds)
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        
        # Give extra time for JavaScript to populate data
        time.sleep(3)
        
        # Parse the rendered HTML
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Try multiple table selectors
        table = (soup.find('table', {'id': 'ranking-table'}) or 
                soup.find('table', {'id': 'data'}) or
                soup.find('table', {'class': 'player-table'}) or
                soup.find('table'))
        
        if table:
            print(f"Found table on Fantasy Pros")
            rows = table.find_all('tr')
            print(f"Found {len(rows)} rows")
            
            count = 0
            for row in rows[1:]:  # Skip header
                cols = row.find_all('td')
                if len(cols) >= 3:  # Need at least 3 columns
                    try:
                        # Rank in column 0
                        rank_text = cols[0].text.strip()
                        
                        # Player name in column 2 (col 1 is empty)
                        player_text = cols[2].text.strip()
                        
                        # Remove team in parentheses like "(CAR)"
                        player_name = re.sub(r'\s*\([^)]*\)\s*$', '', player_text).strip()
                        
                        # Position rank in column 3
                        position_rank = cols[3].text.strip() if len(cols) > 3 else ''
                        
                        # Extract rank number
                        rank_match = re.search(r'(\d+)', rank_text)
                        if player_name and rank_match:
                            overall_rank = int(rank_match.group(1))
                            
                            rankings[player_name.lower()] = {
                                'overall_rank': overall_rank,
                                'position_rank': position_rank
                            }
                            count += 1
                            
                            # Debug first 3
                            if count <= 3:
                                print(f"  #{overall_rank}: {player_name} ({position_rank})")
                    except Exception as e:
                        continue
            
            print(f"Scraped {count} Fantasy Pros rankings")
        else:
            print("No table found on Fantasy Pros page")
            
    except Exception as e:
        print(f"Error scraping Fantasy Pros: {e}")
    finally:
        if driver:
            driver.quit()
    
    return rankings

def scrape_ras_scores():
    """Scrape RAS (Relative Athletic Score) using Selenium"""
    ras_scores = {}
    driver = None
    try:
        print("Attempting to scrape RAS scores with Selenium...")
        driver = get_selenium_driver()
        if not driver:
            print("Failed to create Selenium driver for RAS")
            return ras_scores
        
        url = 'https://ras.football/ras-information/'
        driver.get(url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)  # Extra time for JavaScript
        
        # Parse the rendered HTML
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables on RAS")
        
        count = 0
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    try:
                        # Look for player name and RAS score
                        player_name = None
                        ras_score = None
                        
                        for i, col in enumerate(cols):
                            text = col.text.strip()
                            
                            # Player name usually has link or is longer text
                            if col.find('a') and not player_name:
                                player_name = col.find('a').text.strip()
                            
                            # RAS score is usually a number between 0-10
                            if not ras_score and text:
                                try:
                                    score = float(text)
                                    if 0 <= score <= 10:
                                        ras_score = text
                                except:
                                    pass
                        
                        if player_name and ras_score:
                            ras_scores[player_name.lower()] = ras_score
                            count += 1
                            
                    except Exception as e:
                        continue
        
        print(f"Scraped {count} RAS scores")
        
    except Exception as e:
        print(f"Error scraping RAS scores: {e}")
    finally:
        if driver:
            driver.quit()
    
    return ras_scores

def scrape_free_agency():
    """Scrape free agency data from Over The Cap using Selenium"""
    free_agency = {}
    driver = None
    try:
        print("Attempting to scrape free agency with Selenium...")
        driver = get_selenium_driver()
        if not driver:
            print("Failed to create Selenium driver for free agency")
            return free_agency
        
        # Get current year and next 2 years
        current_year = datetime.now().year
        years = [current_year, current_year + 1, current_year + 2]
        
        for year in years:
            try:
                print(f"Scraping Over The Cap free agency for {year}...")
                url = f'https://overthecap.com/free-agency/{year}'
                driver.get(url)
                
                # Wait for table to load
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                time.sleep(2)  # Extra time for JavaScript
                
                # Parse the rendered HTML
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Find the free agency table
                table = soup.find('table', {'class': 'sortable'}) or soup.find('table')
                
                if table:
                    rows = table.find_all('tr')[1:]  # Skip header
                    year_count = 0
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            try:
                                player_cell = cols[0]
                                player_link = player_cell.find('a')
                                if player_link:
                                    player_name = player_link.text.strip()
                                else:
                                    player_name = player_cell.text.strip()
                                
                                player_name = re.sub(r'\s+', ' ', player_name).strip()
                                
                                # Free agent type (UFA, RFA, etc.)
                                fa_type = ''
                                for col in cols[1:4]:
                                    text = col.text.strip().upper()
                                    if text in ['UFA', 'RFA', 'ERFA', 'XFA']:
                                        fa_type = text
                                        break
                                
                                if player_name:
                                    name_lower = player_name.lower()
                                    if name_lower not in free_agency:
                                        free_agency[name_lower] = []
                                    free_agency[name_lower].append({
                                        'year': year,
                                        'type': fa_type
                                    })
                                    year_count += 1
                            except Exception as e:
                                continue
                    
                    print(f"Scraped {year_count} players for {year} from Over The Cap")
                else:
                    print(f"No table found for {year}")
                    
            except Exception as e:
                print(f"Error scraping year {year}: {e}")
                continue
        
        print(f"Total free agency records: {sum(len(v) for v in free_agency.values())}")
        
    except Exception as e:
        print(f"Error in free agency scraper: {e}")
    finally:
        if driver:
            driver.quit()
    
    return free_agency

def scrape_draft_info():
    """Scrape NFL draft information using Selenium"""
    draft_info = {}
    driver = None
    try:
        print("Attempting to scrape draft info with Selenium...")
        driver = get_selenium_driver()
        if not driver:
            print("Failed to create Selenium driver for draft info")
            return draft_info
        
        # Get recent draft years
        current_year = datetime.now().year
        years = range(current_year, current_year - 10, -1)  # Last 10 years
        
        for year in years:
            try:
                print(f"Scraping Football DB draft {year}...")
                url = f'https://www.footballdb.com/draft/{year}-draft/index.html'
                driver.get(url)
                
                # Wait for table to load
                try:
                    wait = WebDriverWait(driver, 5)
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                    time.sleep(1)
                except:
                    print(f"No table found for {year}")
                    continue
                
                # Parse the rendered HTML
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                table = soup.find('table')
                if table:
                    rows = table.find_all('tr')[1:]  # Skip header
                    year_count = 0
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 4:
                            try:
                                # Column structure: Pick, Player, Position, Team, College
                                pick_cell = cols[0]
                                player_cell = cols[1]
                                
                                player_link = player_cell.find('a')
                                if player_link:
                                    player_name = player_link.text.strip()
                                else:
                                    player_name = player_cell.text.strip()
                                
                                player_name = re.sub(r'\s+', ' ', player_name).strip()
                                
                                # Extract pick number, round info
                                pick_text = pick_cell.text.strip()
                                pick_number = None
                                round_number = None
                                
                                # Parse pick like "1" or "R1P1" format
                                pick_match = re.search(r'(\d+)', pick_text)
                                if pick_match:
                                    pick_number = int(pick_match.group(1))
                                    # Estimate round (32 picks per round)
                                    round_number = (pick_number - 1) // 32 + 1
                                
                                if player_name and pick_number:
                                    draft_info[player_name.lower()] = {
                                        'year': year,
                                        'round': round_number,
                                        'pick': pick_number
                                    }
                                    year_count += 1
                            except Exception as e:
                                continue
                    
                    print(f"Scraped {year_count} draft picks for {year}")
                else:
                    print(f"No table found for {year}")
                    
            except Exception as e:
                print(f"Error scraping draft {year}: {e}")
                continue
        
        print(f"Total draft records: {len(draft_info)}")
        
    except Exception as e:
        print(f"Error in draft info scraper: {e}")
    finally:
        if driver:
            driver.quit()
    
    return draft_info

def scrape_snap_counts():
    """Scrape NFL Career Snap counts from Over The Cap
    Note: This site uses JavaScript to load data dynamically, so basic scraping may not work.
    An API or Selenium would be needed for full functionality.
    """
    snap_counts = {}
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        print("Attempting to scrape Over The Cap snap counts...")
        url = 'https://overthecap.com/snap-count-history'
        response = requests.get(url, headers=headers, timeout=20)
        
        print(f"Snap counts response status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for the snap counts table
            table = soup.find('table', {'class': 'snap-counts-table'}) or soup.find('tbody')
            
            if table:
                # If we got the whole table, find tbody; if we already have tbody, use it
                tbody = table.find('tbody') if table.name != 'tbody' else table
                if not tbody:
                    tbody = table
                    
                rows = tbody.find_all('tr')
                count = 0
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:  # Need at least: name, team, position, spacer, data
                        try:
                            # First column: player name (has <a> tag)
                            player_cell = cols[0]
                            player_link = player_cell.find('a')
                            if not player_link:
                                continue
                            player_name = player_link.text.strip()
                            
                            # Sum up all snap counts from year columns
                            # Each year column has: <span class="number">XXX</span>
                            career_snaps = 0
                            for col in cols[4:]:  # Skip name, team, position, spacer
                                # Look for <span class="number"> elements
                                number_spans = col.find_all('span', {'class': 'number'})
                                for span in number_spans:
                                    try:
                                        snap_text = span.text.strip().replace(',', '')
                                        if snap_text.isdigit():
                                            career_snaps += int(snap_text)
                                    except:
                                        continue
                            
                            if player_name and career_snaps > 0:
                                snap_counts[player_name.lower()] = career_snaps
                                count += 1
                        except Exception as e:
                            continue
                
                print(f"Scraped {count} players with snap counts")
            else:
                print("No snap counts table found (JavaScript-loaded content)")
        else:
            print(f"Failed to load snap counts: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Error scraping snap counts: {e}")
    
    return snap_counts

def deduplicate_players(players_list):
    """Remove duplicate players based on client logic:
    - If one duplicate is rostered to an NFL team and the other isn't → keep the NFL-rostered player
    - For both un-rostered, keep the one with higher experience (yrs)
    - If same experience, keep both
    """
    # Group players by (name, position, college)
    from collections import defaultdict
    player_groups = defaultdict(list)
    
    for player in players_list:
        # Handle None values safely
        name = (player.get('name') or '').lower().strip()
        position = player.get('position') or ''
        college = (player.get('college') or '').lower().strip()
        
        if not name:  # Skip players without names
            continue
            
        key = (name, position, college)
        player_groups[key].append(player)
    
    deduplicated = []
    
    for key, group in player_groups.items():
        if len(group) == 1:
            # No duplicates
            deduplicated.append(group[0])
        else:
            # Has duplicates - apply logic
            # Separate NFL-rostered from unrostered
            nfl_rostered = [p for p in group if p.get('team') and p['team'] != 'FA']
            unrostered = [p for p in group if not p.get('team') or p['team'] == 'FA']
            
            if nfl_rostered and unrostered:
                # Keep NFL-rostered players only
                deduplicated.extend(nfl_rostered)
            elif nfl_rostered:
                # All are NFL-rostered - keep all
                deduplicated.extend(nfl_rostered)
            elif unrostered:
                # All are unrostered - keep highest experience
                max_exp = max(p.get('experience', 0) or 0 for p in unrostered)
                highest_exp_players = [p for p in unrostered if (p.get('experience', 0) or 0) == max_exp]
                
                if len(highest_exp_players) == len(unrostered):
                    # All have same experience - keep all
                    deduplicated.extend(unrostered)
                else:
                    # Keep only highest experience
                    deduplicated.extend(highest_exp_players)
            else:
                # Fallback - keep all
                deduplicated.extend(group)
    
    print(f"Deduplication: {len(players_list)} -> {len(deduplicated)} players")
    return deduplicated

def match_player_name(sleeper_name, external_name):
    """Fuzzy match player names"""
    # Normalize names
    s_name = re.sub(r'[^a-z]', '', sleeper_name.lower())
    e_name = re.sub(r'[^a-z]', '', external_name.lower())
    
    # Direct match
    if s_name == e_name:
        return True
    
    # Check if one contains the other (handles Jr., Sr., etc.)
    if s_name in e_name or e_name in s_name:
        return True
    
    # Check first and last name match
    s_parts = sleeper_name.lower().split()
    e_parts = external_name.lower().split()
    
    if len(s_parts) >= 2 and len(e_parts) >= 2:
        # Compare first and last names
        if s_parts[0] == e_parts[0] and s_parts[-1] == e_parts[-1]:
            return True
    
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get-players', methods=['POST'])
def get_players():
    """Main API endpoint to fetch and aggregate all player data"""
    try:
        data = request.json
        username = data.get('username', '')
        league_ids = data.get('league_ids', [])
        
        # Fetch base player data from Sleeper
        print("Fetching Sleeper players...")
        sleeper_players = get_sleeper_players()
        
        # Fetch external data sources (run in parallel would be better, but keeping simple for now)
        print("Fetching Fantasy Pros rankings...")
        fantasy_pros = scrape_fantasy_pros()
        
        print("Fetching RAS scores...")
        ras_scores = scrape_ras_scores()
        
        print("Fetching free agency data...")
        free_agency = scrape_free_agency()
        
        print("Fetching draft info...")
        draft_info = scrape_draft_info()
        
        print("Fetching snap counts...")
        snap_counts = scrape_snap_counts()
        
        # Get roster information for each league
        league_data = {}
        league_names = {}  # Store league names for the response
        for league_id in league_ids:
            if league_id:
                print(f"Fetching roster for league {league_id}...")
                user_roster, player_ownership, league_name = get_user_roster(username, league_id)
                league_data[league_id] = {
                    'user_roster': user_roster,
                    'player_ownership': player_ownership
                }
                league_names[league_id] = league_name
        
        # Aggregate all data
        players_list = []
        
        for player_id, player_data in sleeper_players.items():
            full_name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip()
            
            # Calculate age
            age = None
            birth_date = player_data.get('birth_date', '')
            if birth_date:
                try:
                    birth_year = int(birth_date.split('-')[0])
                    age = datetime.now().year - birth_year
                except:
                    pass
            
            # Format height from inches to feet'inches\"
            height_inches = player_data.get('height', '')
            height_formatted = convert_height_to_feet_inches(height_inches)
            
            # Experience
            experience = player_data.get('years_exp', 0)
            
            # Build player row
            player_row = {
                'player_id': player_id,
                'name': full_name,
                'position': player_data.get('position', ''),
                'team': player_data.get('team', 'FA'),
                'experience': experience,
                'height': height_formatted,  # Now formatted as feet'inches\"
                'weight': player_data.get('weight', ''),
                'college': player_data.get('college', ''),
                'age': age,
                'birthdate': birth_date,
                'overall_rank': '',
                'position_rank': '',
                'ras_score': '',
                'nfl_career_snaps': '',  # New column
                'free_agency_year': '',
                'free_agency_type': '',
                'draft_year': '',
                'draft_round': '',
                'draft_pick': ''
            }
            
            # Match with Fantasy Pros
            name_lower = full_name.lower()
            for fp_name, fp_data in fantasy_pros.items():
                if match_player_name(full_name, fp_name):
                    player_row['overall_rank'] = fp_data.get('overall_rank', '')
                    player_row['position_rank'] = fp_data.get('position_rank', '')
                    break
            
            # Match with RAS scores
            if name_lower in ras_scores:
                player_row['ras_score'] = ras_scores[name_lower]
            
            # Match with snap counts
            if name_lower in snap_counts:
                player_row['nfl_career_snaps'] = snap_counts[name_lower]
            else:
                player_row['nfl_career_snaps'] = 'N/A'  # Display N/A when data not available
            
            # Match with free agency
            if name_lower in free_agency:
                fa_data = free_agency[name_lower]
                if fa_data:
                    # Get the earliest year
                    earliest = min(fa_data, key=lambda x: x['year'])
                    player_row['free_agency_year'] = earliest['year']
                    player_row['free_agency_type'] = earliest['type']
            
            # Match with draft info
            if name_lower in draft_info:
                di_data = draft_info[name_lower]
                player_row['draft_year'] = di_data.get('year', '')
                player_row['draft_round'] = di_data.get('round', '')
                player_row['draft_pick'] = di_data.get('pick', '')
            
            # Add league ownership columns
            for league_id, league_info in league_data.items():
                user_roster = league_info.get('user_roster')
                player_ownership = league_info.get('player_ownership')
                
                # Handle different error states
                if user_roster == "invalid_league":
                    player_row[f'league_{league_id}'] = 'Invalid League ID'
                elif user_roster == "invalid_user":
                    player_row[f'league_{league_id}'] = 'Invalid Username'
                elif user_roster == "error":
                    player_row[f'league_{league_id}'] = 'Error'
                elif user_roster is not None and player_ownership is not None:
                    if player_id in user_roster:
                        player_row[f'league_{league_id}'] = 'Owned'
                    elif player_id in player_ownership:
                        player_row[f'league_{league_id}'] = player_ownership[player_id]
                    else:
                        player_row[f'league_{league_id}'] = 'Available'
                else:
                    player_row[f'league_{league_id}'] = 'Error'
            
            players_list.append(player_row)
        
        # Apply deduplication logic
        players_list = deduplicate_players(players_list)
        
        return jsonify({
            'success': True,
            'players': players_list,
            'total': len(players_list),
            'league_names': league_names  # Include league names in response
        })
    
    except Exception as e:
        print(f"Error in get_players: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
