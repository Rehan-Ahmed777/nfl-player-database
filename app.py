from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time

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
    """Scrape Fantasy Pros dynasty rankings"""
    rankings = {}
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        print("Attempting to scrape Fantasy Pros...")
        response = requests.get('https://www.fantasypros.com/nfl/rankings/dynasty-overall.php', 
                              headers=headers, timeout=20, allow_redirects=True)
        
        print(f"Fantasy Pros response status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try multiple table selectors
            table = (soup.find('table', {'id': 'ranking-table'}) or 
                    soup.find('table', {'id': 'data'}) or
                    soup.find('table', {'class': 'player-table'}) or
                    soup.find('table'))
            
            if table:
                print(f"Found table on Fantasy Pros")
                rows = table.find_all('tr')
                print(f"Found {len(rows)} rows")
                
                for row in rows[1:]:  # Skip header
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        try:
                            # Try to find rank (usually first column)
                            rank = cols[0].text.strip()
                            
                            # Try to find player name (usually second column)
                            player_cell = cols[1]
                            player_name = player_cell.find('a').text.strip() if player_cell.find('a') else player_cell.text.strip()
                            
                            # Clean player name (remove extra whitespace, team abbreviations, etc.)
                            player_name = re.sub(r'\s+', ' ', player_name).strip()
                            player_name = re.sub(r'\s*\([^)]*\)', '', player_name).strip()  # Remove (TB), (FA), etc.
                            
                            # Position rank - try different column positions
                            pos_rank = ''
                            for col in cols[2:5]:  # Check columns 2-4
                                text = col.text.strip()
                                if text and any(pos in text.upper() for pos in ['QB', 'RB', 'WR', 'TE']):
                                    pos_rank = text
                                    break
                            
                            if player_name and rank:
                                rankings[player_name.lower()] = {
                                    'overall_rank': rank,
                                    'position_rank': pos_rank
                                }
                        except Exception as e:
                            continue
                
                print(f"Scraped {len(rankings)} players from Fantasy Pros")
            else:
                print("No table found on Fantasy Pros page")
        else:
            print(f"Failed to load Fantasy Pros: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Error scraping Fantasy Pros: {e}")
        import traceback
        traceback.print_exc()
    
    return rankings

def scrape_ras_scores():
    """Scrape RAS scores from ras.football"""
    ras_scores = {}
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        print("Attempting to scrape RAS scores...")
        response = requests.get('https://ras.football/ras-information/', headers=headers, timeout=20)
        
        print(f"RAS response status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for player data - RAS.football has a complex structure
            # This is a simplified version - may need Selenium for full functionality
            tables = soup.find_all('table')
            print(f"Found {len(tables)} tables on RAS")
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= 3:
                        try:
                            # Try to extract player name and RAS score
                            text_content = ' '.join([col.text.strip() for col in cols])
                            # This needs to be refined based on actual site structure
                            # For now, we'll skip this to avoid errors
                        except:
                            continue
            
            print(f"Scraped {len(ras_scores)} RAS scores")
        else:
            print(f"Failed to load RAS: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Error scraping RAS scores: {e}")
    
    return ras_scores

def scrape_free_agency():
    """Scrape free agency data from Over The Cap"""
    free_agency = {}
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        # Get current year and next 2 years
        current_year = datetime.now().year
        years = [current_year, current_year + 1, current_year + 2]
        
        for year in years:
            try:
                print(f"Attempting to scrape Over The Cap for {year}...")
                url = f'https://overthecap.com/free-agency/{year}'
                response = requests.get(url, headers=headers, timeout=20)
                
                print(f"Over The Cap {year} response status: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
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
                                    player_name = player_cell.find('a').text.strip() if player_cell.find('a') else player_cell.text.strip()
                                    player_name = re.sub(r'\s+', ' ', player_name).strip()
                                    
                                    # Free agent type (UFA, RFA, etc.) - try different columns
                                    fa_type = ''
                                    for col in cols[1:4]:
                                        text = col.text.strip()
                                        if any(x in text.upper() for x in ['UFA', 'RFA', 'ERFA', 'VOID']):
                                            fa_type = text
                                            break
                                    
                                    if not fa_type and len(cols) > 1:
                                        fa_type = cols[1].text.strip()
                                    
                                    if player_name.lower() not in free_agency:
                                        free_agency[player_name.lower()] = []
                                    
                                    free_agency[player_name.lower()].append({
                                        'year': year,
                                        'type': fa_type
                                    })
                                    year_count += 1
                                except Exception as e:
                                    continue
                        
                        print(f"Scraped {year_count} players for {year} from Over The Cap")
                    else:
                        print(f"No table found for {year}")
                else:
                    print(f"Failed to load Over The Cap for {year}")
                    
                time.sleep(1)  # Be nice to the server
                
            except Exception as e:
                print(f"Error scraping free agency for {year}: {e}")
                continue
                
        print(f"Total free agency records: {len(free_agency)}")
        
    except Exception as e:
        print(f"Error scraping free agency: {e}")
    
    return free_agency

def scrape_draft_info():
    """Scrape NFL draft information"""
    draft_info = {}
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        # Get recent draft years
        current_year = datetime.now().year
        years = range(current_year, current_year - 10, -1)  # Last 10 years
        
        for year in years:
            try:
                print(f"Attempting to scrape Football DB draft {year}...")
                url = f'https://www.footballdb.com/draft/{year}-draft/index.html'
                response = requests.get(url, headers=headers, timeout=20)
                
                print(f"Football DB {year} response status: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find draft table
                    table = soup.find('table', {'class': 'statistics'}) or soup.find('table')
                    
                    if table:
                        rows = table.find_all('tr')[1:]  # Skip header
                        year_count = 0
                        for row in rows:
                            cols = row.find_all('td')
                            if len(cols) >= 3:
                                try:
                                    # Typical columns: Round, Pick, Player, Position, College
                                    round_num = cols[0].text.strip()
                                    pick_num = cols[1].text.strip()
                                    
                                    # Player name could be in various columns
                                    player_cell = cols[2] if len(cols) > 2 else cols[1]
                                    player_name = player_cell.find('a').text.strip() if player_cell.find('a') else player_cell.text.strip()
                                    player_name = re.sub(r'\s+', ' ', player_name).strip()
                                    
                                    if player_name and round_num:
                                        draft_info[player_name.lower()] = {
                                            'year': year,
                                            'round': round_num,
                                            'pick': pick_num
                                        }
                                        year_count += 1
                                except Exception as e:
                                    continue
                        
                        print(f"Scraped {year_count} players from {year} draft")
                    else:
                        print(f"No table found for {year} draft")
                else:
                    print(f"Failed to load Football DB for {year}")
                    
                time.sleep(1)  # Be nice to the server
                
            except Exception as e:
                print(f"Error scraping draft {year}: {e}")
                continue
        
        print(f"Total draft records: {len(draft_info)}")
        
    except Exception as e:
        print(f"Error scraping draft info: {e}")
    
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
