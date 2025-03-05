import requests
import yaml
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import sys
import os

VERSION = "1.1"

# ANSI color codes
GREEN = '\033[32m'
ORANGE = '\033[33m'
BLUE = '\033[34m'
RED = '\033[31m'
RESET = '\033[0m'
BOLD = '\033[1m'

def check_for_updates():
    print(f"Checking for updates to TSSK {VERSION}...")
    
    try:
        response = requests.get(
            "https://api.github.com/repos/netplexflix/TV-show-status-for-Kometa/releases/latest",
            timeout=10
        )
        response.raise_for_status()
        
        latest_release = response.json()
        latest_version = latest_release.get("tag_name", "").lstrip("v")
        
        def parse_version(version_str):
            return tuple(map(int, version_str.split('.')))
        
        current_version_tuple = parse_version(VERSION)
        latest_version_tuple = parse_version(latest_version)
        
        if latest_version and latest_version_tuple > current_version_tuple:
            print(f"{ORANGE}A newer version of TSSK is available: {latest_version}{RESET}")
            print(f"{ORANGE}Download: {latest_release.get('html_url', '')}{RESET}")
            print(f"{ORANGE}Release notes: {latest_release.get('body', 'No release notes available')}{RESET}\n")
        else:
            print(f"{GREEN}You are running the latest version of TSSK.{RESET}\n")
    except Exception as e:
        print(f"{ORANGE}Could not check for updates: {str(e)}{RESET}\n")

def get_config_section(config, primary_key, fallback_keys=None):
    if fallback_keys is None:
        fallback_keys = []
    
    if primary_key in config:
        return config[primary_key]
    
    for key in fallback_keys:
        if key in config:
            return config[key]
    
    return {}

def load_config(file_path='config.yml'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Config file '{file_path}' not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML config file: {e}")
        sys.exit(1)

def process_sonarr_url(base_url, api_key):
    base_url = base_url.rstrip('/')
    
    if base_url.startswith('http'):
        protocol_end = base_url.find('://') + 3
        next_slash = base_url.find('/', protocol_end)
        if next_slash != -1:
            base_url = base_url[:next_slash]
    
    api_paths = [
        '/api/v3',
        '/sonarr/api/v3'
    ]
    
    for path in api_paths:
        test_url = f"{base_url}{path}"
        try:
            headers = {"X-Api-Key": api_key}
            response = requests.get(f"{test_url}/health", headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"Successfully connected to Sonarr at: {test_url}")
                return test_url
        except requests.exceptions.RequestException as e:
            print(f"{ORANGE}Testing URL {test_url} - Failed: {str(e)}{RESET}")
            continue
    
    raise ConnectionError(f"{RED}Unable to establish connection to Sonarr. Tried the following URLs:\n" + 
                        "\n".join([f"- {base_url}{path}" for path in api_paths]) + 
                        f"\nPlease verify your URL and API key and ensure Sonarr is running.{RESET}")

def get_sonarr_series(sonarr_url, api_key):
    try:
        url = f"{sonarr_url}/series"
        headers = {"X-Api-Key": api_key}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"{RED}Error connecting to Sonarr: {str(e)}{RESET}")
        sys.exit(1)

def get_sonarr_episodes(sonarr_url, api_key, series_id):
    try:
        url = f"{sonarr_url}/episode?seriesId={series_id}"
        headers = {"X-Api-Key": api_key}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"{RED}Error fetching episodes from Sonarr: {str(e)}{RESET}")
        sys.exit(1)

def find_new_season_shows(sonarr_url, api_key, future_days_new_season, skip_unmonitored=False):
    cutoff_date = datetime.now(timezone.utc) + timedelta(days=future_days_new_season)
    matched_shows = []
    skipped_shows = []
    
    all_series = get_sonarr_series(sonarr_url, api_key)
    
    for series in all_series:
        episodes = get_sonarr_episodes(sonarr_url, api_key, series['id'])
        
        future_episodes = []
        for ep in episodes:
            air_date_str = ep.get('airDateUtc')
            if not air_date_str:
                continue
            
            air_date = datetime.fromisoformat(air_date_str.replace('Z','')).replace(tzinfo=timezone.utc)
            
            if air_date > datetime.now(timezone.utc):
                future_episodes.append(ep)
        
        future_episodes.sort(key=lambda x: datetime.fromisoformat(x['airDateUtc'].replace('Z','')).replace(tzinfo=timezone.utc))
        
        if not future_episodes:
            continue
        
        next_future = future_episodes[0]
        
        air_date_next_str = next_future.get('airDateUtc')
        if not air_date_next_str:
            continue
        
        air_date_next = datetime.fromisoformat(air_date_next_str.replace('Z','')).replace(tzinfo=timezone.utc)
        
        if (
            next_future['seasonNumber'] >= 1
            and next_future['episodeNumber'] == 1
            and not next_future['hasFile']
            and air_date_next <= cutoff_date
        ):
            tvdb_id = series.get('tvdbId')
            air_date_str_yyyy_mm_dd = air_date_next.date().isoformat()

            show_dict = {
                'title': series['title'],
                'seasonNumber': next_future['seasonNumber'],
                'airDate': air_date_str_yyyy_mm_dd,
                'tvdbId': tvdb_id
            }
            
            if skip_unmonitored:
                episode_monitored = next_future.get("monitored", True)
                
                season_monitored = True
                for season_info in series.get("seasons", []):
                    if season_info.get("seasonNumber") == next_future['seasonNumber']:
                        season_monitored = season_info.get("monitored", True)
                        break
                
                if not episode_monitored or not season_monitored:
                    skipped_shows.append(show_dict)
                    continue
            
            matched_shows.append(show_dict)
    
    return matched_shows, skipped_shows

def find_upcoming_regular_episodes(sonarr_url, api_key, future_days_upcoming_episode, skip_unmonitored=False):
    """Find shows with upcoming non-premiere, non-finale episodes within the specified days"""
    cutoff_date = datetime.now(timezone.utc) + timedelta(days=future_days_upcoming_episode)
    matched_shows = []
    skipped_shows = []
    
    all_series = get_sonarr_series(sonarr_url, api_key)
    
    for series in all_series:
        episodes = get_sonarr_episodes(sonarr_url, api_key, series['id'])
        
        # Group episodes by season
        seasons = defaultdict(list)
        for ep in episodes:
            if ep.get('seasonNumber') > 0:  # Skip specials
                seasons[ep.get('seasonNumber')].append(ep)
        
        # For each season, find the max episode number to identify finales
        season_finales = {}
        for season_num, season_eps in seasons.items():
            if season_eps:
                max_ep = max(ep.get('episodeNumber', 0) for ep in season_eps)
                season_finales[season_num] = max_ep
        
        future_episodes = []
        for ep in episodes:
            air_date_str = ep.get('airDateUtc')
            if not air_date_str:
                continue
            
            air_date = datetime.fromisoformat(air_date_str.replace('Z','')).replace(tzinfo=timezone.utc)
            
            if air_date > datetime.now(timezone.utc) and air_date <= cutoff_date:
                future_episodes.append(ep)
        
        future_episodes.sort(key=lambda x: datetime.fromisoformat(x['airDateUtc'].replace('Z','')).replace(tzinfo=timezone.utc))
        
        if not future_episodes:
            continue
        
        next_future = future_episodes[0]
        season_num = next_future.get('seasonNumber')
        episode_num = next_future.get('episodeNumber')
        
        # Skip season premieres (episode 1 of any season)
        if episode_num == 1:
            continue
            
        # Skip season finales
        is_episode_finale = season_num in season_finales and episode_num == season_finales[season_num]
        if is_episode_finale:
            continue
        
        air_date_str = next_future.get('airDateUtc')
        if not air_date_str:
            continue
        
        air_date = datetime.fromisoformat(air_date_str.replace('Z','')).replace(tzinfo=timezone.utc)
        
        tvdb_id = series.get('tvdbId')
        air_date_str_yyyy_mm_dd = air_date.date().isoformat()

        show_dict = {
            'title': series['title'],
            'seasonNumber': season_num,
            'episodeNumber': episode_num,
            'airDate': air_date_str_yyyy_mm_dd,
            'tvdbId': tvdb_id
        }
        
        if skip_unmonitored:
            episode_monitored = next_future.get("monitored", True)
            
            season_monitored = True
            for season_info in series.get("seasons", []):
                if season_info.get("seasonNumber") == season_num:
                    season_monitored = season_info.get("monitored", True)
                    break
            
            if not episode_monitored or not season_monitored:
                skipped_shows.append(show_dict)
                continue
        
        matched_shows.append(show_dict)
    
    return matched_shows, skipped_shows

def find_upcoming_finales(sonarr_url, api_key, future_days_upcoming_finale, skip_unmonitored=False):
    """Find shows with upcoming season finales within the specified days"""
    cutoff_date = datetime.now(timezone.utc) + timedelta(days=future_days_upcoming_finale)
    matched_shows = []
    skipped_shows = []
    
    all_series = get_sonarr_series(sonarr_url, api_key)
    
    for series in all_series:
        episodes = get_sonarr_episodes(sonarr_url, api_key, series['id'])
        
        # Group episodes by season
        seasons = defaultdict(list)
        for ep in episodes:
            if ep.get('seasonNumber') > 0:  # Skip specials
                seasons[ep.get('seasonNumber')].append(ep)
        
        # For each season, find the max episode number to identify finales
        season_finales = {}
        for season_num, season_eps in seasons.items():
            if season_eps:
                max_ep = max(ep.get('episodeNumber', 0) for ep in season_eps)
                season_finales[season_num] = max_ep
        
        future_episodes = []
        for ep in episodes:
            air_date_str = ep.get('airDateUtc')
            if not air_date_str:
                continue
            
            air_date = datetime.fromisoformat(air_date_str.replace('Z','')).replace(tzinfo=timezone.utc)
            
            if air_date > datetime.now(timezone.utc) and air_date <= cutoff_date:
                future_episodes.append(ep)
        
        future_episodes.sort(key=lambda x: datetime.fromisoformat(x['airDateUtc'].replace('Z','')).replace(tzinfo=timezone.utc))
        
        if not future_episodes:
            continue
        
        next_future = future_episodes[0]
        season_num = next_future.get('seasonNumber')
        episode_num = next_future.get('episodeNumber')
        
        # Only include season finales
        is_episode_finale = season_num in season_finales and episode_num == season_finales[season_num]
        if not is_episode_finale:
            continue
        
        air_date_str = next_future.get('airDateUtc')
        if not air_date_str:
            continue
        
        air_date = datetime.fromisoformat(air_date_str.replace('Z','')).replace(tzinfo=timezone.utc)
        
        tvdb_id = series.get('tvdbId')
        air_date_str_yyyy_mm_dd = air_date.date().isoformat()

        show_dict = {
            'title': series['title'],
            'seasonNumber': season_num,
            'episodeNumber': episode_num,
            'airDate': air_date_str_yyyy_mm_dd,
            'tvdbId': tvdb_id
        }
        
        if skip_unmonitored:
            episode_monitored = next_future.get("monitored", True)
            
            season_monitored = True
            for season_info in series.get("seasons", []):
                if season_info.get("seasonNumber") == season_num:
                    season_monitored = season_info.get("monitored", True)
                    break
            
            if not episode_monitored or not season_monitored:
                skipped_shows.append(show_dict)
                continue
        
        matched_shows.append(show_dict)
    
    return matched_shows, skipped_shows

def find_ended_shows(sonarr_url, api_key):
    """Find shows that have ended and have no upcoming regular episodes (ignoring specials)"""
    matched_shows = []
    
    all_series = get_sonarr_series(sonarr_url, api_key)
    
    for series in all_series:
        # Check if the show has ended
        if series.get('status') == 'ended':
            episodes = get_sonarr_episodes(sonarr_url, api_key, series['id'])
            
            # Check if there are any future regular episodes (ignoring specials)
            has_future_regular_episodes = False
            for ep in episodes:
                air_date_str = ep.get('airDateUtc')
                season_number = ep.get('seasonNumber', 0)
                
                # Skip specials (season 0)
                if season_number == 0:
                    continue
                    
                if air_date_str:
                    air_date = datetime.fromisoformat(air_date_str.replace('Z','')).replace(tzinfo=timezone.utc)
                    if air_date > datetime.now(timezone.utc):
                        has_future_regular_episodes = True
                        break
            
            # Include only if there are no future regular episodes
            if not has_future_regular_episodes:
                tvdb_id = series.get('tvdbId')
                
                show_dict = {
                    'title': series['title'],
                    'tvdbId': tvdb_id
                }
                
                matched_shows.append(show_dict)
    
    return matched_shows

def find_returning_shows(sonarr_url, api_key, excluded_tvdb_ids):
    """Find shows with 'continuing' status that aren't in other categories"""
    matched_shows = []
    
    all_series = get_sonarr_series(sonarr_url, api_key)
    
    for series in all_series:
        # Check if the show has 'continuing' status
        if series.get('status') == 'continuing':
            tvdb_id = series.get('tvdbId')
            
            # Skip if this show is already in another category
            if tvdb_id in excluded_tvdb_ids:
                continue
                
            show_dict = {
                'title': series['title'],
                'tvdbId': tvdb_id
            }
            
            matched_shows.append(show_dict)
    
    return matched_shows

def find_recent_season_finales(sonarr_url, api_key, recent_days_season_finale):
    """Find shows with status 'continuing' that had a season finale air within the specified days"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=recent_days_season_finale)
    matched_shows = []
    
    all_series = get_sonarr_series(sonarr_url, api_key)
    
    for series in all_series:
        # Only include continuing shows
        if series.get('status') != 'continuing':
            continue
            
        episodes = get_sonarr_episodes(sonarr_url, api_key, series['id'])
        
        # Group episodes by season
        seasons = defaultdict(list)
        for ep in episodes:
            if ep.get('seasonNumber') > 0:  # Skip specials
                seasons[ep.get('seasonNumber')].append(ep)
        
        # For each season, find the max episode number to identify finales
        season_finales = {}
        for season_num, season_eps in seasons.items():
            if season_eps:
                max_ep = max(ep.get('episodeNumber', 0) for ep in season_eps)
                season_finales[season_num] = max_ep
        
        # Look for recently aired season finales
        for ep in episodes:
            air_date_str = ep.get('airDateUtc')
            if not air_date_str:
                continue
                
            season_num = ep.get('seasonNumber')
            episode_num = ep.get('episodeNumber')
            
            # Skip specials
            if season_num == 0:
                continue
                
            # Check if this is a finale episode
            is_finale = season_num in season_finales and episode_num == season_finales[season_num]
            if not is_finale:
                continue
                
            # Verify the episode has been downloaded
            has_file = ep.get('hasFile', False)
            if not has_file:
                continue
                
            air_date = datetime.fromisoformat(air_date_str.replace('Z','')).replace(tzinfo=timezone.utc)
            
            # Check if it aired within the recent period
            if air_date <= datetime.now(timezone.utc) and air_date >= cutoff_date:
                tvdb_id = series.get('tvdbId')
                air_date_str_yyyy_mm_dd = air_date.date().isoformat()
                
                show_dict = {
                    'title': series['title'],
                    'seasonNumber': season_num,
                    'episodeNumber': episode_num,
                    'airDate': air_date_str_yyyy_mm_dd,
                    'tvdbId': tvdb_id
                }
                
                matched_shows.append(show_dict)
                break  # Only include the most recent finale for a show
    
    return matched_shows

def find_recent_final_episodes(sonarr_url, api_key, recent_days_final_episode):
    """Find shows with status 'ended' that had their final episode air within the specified days"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=recent_days_final_episode)
    matched_shows = []
    
    all_series = get_sonarr_series(sonarr_url, api_key)
    
    for series in all_series:
        # Only include ended shows
        if series.get('status') != 'ended':
            continue
            
        episodes = get_sonarr_episodes(sonarr_url, api_key, series['id'])
        
        # Skip shows with future episodes (excluding specials)
        has_future_episodes = False
        for ep in episodes:
            air_date_str = ep.get('airDateUtc')
            season_number = ep.get('seasonNumber', 0)
            
            if season_number == 0:  # Skip specials
                continue
                
            if air_date_str:
                air_date = datetime.fromisoformat(air_date_str.replace('Z','')).replace(tzinfo=timezone.utc)
                if air_date > datetime.now(timezone.utc):
                    has_future_episodes = True
                    break
        
        if has_future_episodes:
            continue
            
        # Find the latest aired episode (excluding specials)
        latest_episode = None
        latest_date = None
        
        for ep in episodes:
            air_date_str = ep.get('airDateUtc')
            season_number = ep.get('seasonNumber', 0)
            has_file = ep.get('hasFile', False)
            
            # Skip specials and episodes that haven't been downloaded
            if season_number == 0 or not has_file:
                continue
                
            if air_date_str:
                air_date = datetime.fromisoformat(air_date_str.replace('Z','')).replace(tzinfo=timezone.utc)
                if air_date <= datetime.now(timezone.utc) and (latest_date is None or air_date > latest_date):
                    latest_date = air_date
                    latest_episode = ep
        
        # Check if the latest episode aired within the recent period
        if latest_episode and latest_date and latest_date >= cutoff_date:
            tvdb_id = series.get('tvdbId')
            season_num = latest_episode.get('seasonNumber')
            episode_num = latest_episode.get('episodeNumber')
            air_date_str_yyyy_mm_dd = latest_date.date().isoformat()
            
            show_dict = {
                'title': series['title'],
                'seasonNumber': season_num,
                'episodeNumber': episode_num,
                'airDate': air_date_str_yyyy_mm_dd,
                'tvdbId': tvdb_id
            }
            
            matched_shows.append(show_dict)
    
    return matched_shows

def format_date(yyyy_mm_dd, date_format, capitalize=False):
    dt_obj = datetime.strptime(yyyy_mm_dd, "%Y-%m-%d")
    
    format_mapping = {
        'mmm': '%b',    # Abbreviated month name
        'mmmm': '%B',   # Full month name
        'mm': '%m',     # 2-digit month
        'm': '%-m',     # 1-digit month
        'dddd': '%A',   # Full weekday name
        'ddd': '%a',    # Abbreviated weekday name
        'dd': '%d',     # 2-digit day
        'd': str(dt_obj.day),  # 1-digit day - direct integer conversion
        'yyyy': '%Y',   # 4-digit year
        'yyy': '%Y',    # 3+ digit year
        'yy': '%y',     # 2-digit year
        'y': '%y'       # Year without century
    }
    
    # Sort format patterns by length (longest first) to avoid partial matches
    patterns = sorted(format_mapping.keys(), key=len, reverse=True)
    
    # First, replace format patterns with temporary markers
    temp_format = date_format
    replacements = {}
    for i, pattern in enumerate(patterns):
        marker = f"@@{i}@@"
        if pattern in temp_format:
            replacements[marker] = format_mapping[pattern]
            temp_format = temp_format.replace(pattern, marker)
    
    # Now replace the markers with strftime formats
    strftime_format = temp_format
    for marker, replacement in replacements.items():
        strftime_format = strftime_format.replace(marker, replacement)
    
    try:
        result = dt_obj.strftime(strftime_format)
        if capitalize:
            result = result.upper()
        return result
    except ValueError as e:
        print(f"{RED}Error: Invalid date format '{date_format}'. Using default format.{RESET}")
        return yyyy_mm_dd  # Return original format as fallback

def create_overlay_yaml(output_file, shows, config_sections):
    import yaml
    from copy import deepcopy
    from datetime import datetime

    if not shows:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("#No matching shows found")
        return
    
    # Group shows by date if available
    date_to_tvdb_ids = defaultdict(list)
    all_tvdb_ids = set()
    
    # Check if this is a category that doesn't need dates
    no_date_needed = "SEASON_FINALE" in output_file or "FINAL_EPISODE" in output_file
    
    for s in shows:
        if s.get("tvdbId"):
            all_tvdb_ids.add(s['tvdbId'])
        
        # Only add to date groups if the show has an air date and dates are needed
        if s.get("airDate") and not no_date_needed:
            date_to_tvdb_ids[s['airDate']].append(s.get('tvdbId'))
    
    overlays_dict = {}
    
    # -- Backdrop Block --
    backdrop_config = deepcopy(config_sections.get("backdrop", {}))
    # Extract enable flag and default to True if not specified
    enable_backdrop = backdrop_config.pop("enable", True)

    # Only add backdrop overlay if enabled
    if enable_backdrop and all_tvdb_ids:
        backdrop_config["name"] = "backdrop"
        all_tvdb_ids_str = ", ".join(str(i) for i in sorted(all_tvdb_ids) if i)
        
        overlays_dict["backdrop"] = {
            "overlay": backdrop_config,
            "tvdb_show": all_tvdb_ids_str
        }
    
    # -- Text Blocks --
    text_config = deepcopy(config_sections.get("text", {}))
    enable_text = text_config.pop("enable", True)
    
    if enable_text and all_tvdb_ids:
        date_format = text_config.pop("date_format", "yyyy-mm-dd")
        use_text = text_config.pop("use_text", "New Season")
        capitalize_dates = text_config.pop("capitalize_dates", True)
        
        # For categories that need dates and shows with air dates, create date-specific overlays
        if date_to_tvdb_ids and not no_date_needed:
            for date_str in sorted(date_to_tvdb_ids):
                formatted_date = format_date(date_str, date_format, capitalize_dates)
                sub_overlay_config = deepcopy(text_config)
                sub_overlay_config["name"] = f"text({use_text} {formatted_date})"
                
                tvdb_ids_for_date = sorted(tvdb_id for tvdb_id in date_to_tvdb_ids[date_str] if tvdb_id)
                tvdb_ids_str = ", ".join(str(i) for i in tvdb_ids_for_date)
                
                block_key = f"TSSK_{formatted_date}"
                overlays_dict[block_key] = {
                    "overlay": sub_overlay_config,
                    "tvdb_show": tvdb_ids_str
                }
        # For shows without air dates or categories that don't need dates, create a single overlay
        else:
            sub_overlay_config = deepcopy(text_config)
            sub_overlay_config["name"] = f"text({use_text})"
            
            tvdb_ids_str = ", ".join(str(i) for i in sorted(all_tvdb_ids) if i)
            
            block_key = "TSSK_text"
            overlays_dict[block_key] = {
                "overlay": sub_overlay_config,
                "tvdb_show": tvdb_ids_str
            }
    
    final_output = {"overlays": overlays_dict}
    
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(final_output, f, sort_keys=False)

def create_collection_yaml(output_file, shows, config):
    import yaml
    from yaml.representer import SafeRepresenter
    from copy import deepcopy
    from collections import OrderedDict

    # Add representer for OrderedDict
    def represent_ordereddict(dumper, data):
        return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())
    
    yaml.add_representer(OrderedDict, represent_ordereddict, Dumper=yaml.SafeDumper)

    if not shows:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("#No matching shows found")
        return
    
    tvdb_ids = [s['tvdbId'] for s in shows if s.get('tvdbId')]
    if not tvdb_ids:
        return

    # Convert to comma-separated
    tvdb_ids_str = ", ".join(str(i) for i in sorted(tvdb_ids))

    # Determine collection type and get the appropriate config section
    collection_config = {}
    collection_name = ""
    
    if "SEASON_FINALE" in output_file:
        config_key = "collection_season_finale"
        summary = f"Shows with a season finale that aired within the past {config.get('recent_days_season_finale', 21)} days"
    elif "FINAL_EPISODE" in output_file:
        config_key = "collection_final_episode"
        summary = f"Shows with a final episode that aired within the past {config.get('recent_days_final_episode', 21)} days"
    elif "NEW_SEASON" in output_file:
        config_key = "collection_new_season"
        summary = f"Shows with a new season starting within {config.get('future_days_new_season', 31)} days"
    elif "UPCOMING_EPISODE" in output_file:
        config_key = "collection_upcoming_episode"
        summary = f"Shows with an upcoming episode within {config.get('future_days_upcoming_episode', 31)} days"
    elif "UPCOMING_FINALE" in output_file:
        config_key = "collection_upcoming_finale"
        summary = f"Shows with a season finale within {config.get('future_days_upcoming_finale', 31)} days"
    elif "ENDED" in output_file:
        config_key = "collection_ended"
        summary = "Shows that have completed their run"
    elif "RETURNING" in output_file:
        config_key = "collection_returning"
        summary = "Returning Shows without upcoming episodes within the chosen timeframes"
    else:
        # Default fallback
        config_key = None
        collection_name = "TV Collection"
        summary = "TV Collection"
    
    # Get the collection configuration if available
    if config_key and config_key in config:
        # Create a deep copy to avoid modifying the original config
        collection_config = deepcopy(config[config_key])
        # Extract the collection name and remove it from the config
        collection_name = collection_config.pop("collection_name", "TV Collection")
    
    class QuotedString(str):
        pass

    def quoted_str_presenter(dumper, data):
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

    yaml.add_representer(QuotedString, quoted_str_presenter, Dumper=yaml.SafeDumper)

    # Create the collection data structure as a regular dict
    collection_data = {}
    collection_data["summary"] = summary
    
    # Add all remaining parameters from the collection config
    for key, value in collection_config.items():
        # If it's a sort_title, make it a QuotedString
        if key == "sort_title":
            collection_data[key] = QuotedString(value)
        else:
            collection_data[key] = value
    
    # Add sync_mode after the config parameters
    collection_data["sync_mode"] = "sync"
    
    # Add tvdb_show as the last item
    collection_data["tvdb_show"] = tvdb_ids_str

    # Create the final structure with ordered keys
    ordered_collection = OrderedDict()
    
    # Add keys in the desired order
    ordered_collection["summary"] = collection_data["summary"]
    if "sort_title" in collection_data:
        ordered_collection["sort_title"] = collection_data["sort_title"]
    
    # Add all other keys except sync_mode and tvdb_show
    for key, value in collection_data.items():
        if key not in ["summary", "sort_title", "sync_mode", "tvdb_show"]:
            ordered_collection[key] = value
    
    # Add sync_mode and tvdb_show at the end
    ordered_collection["sync_mode"] = collection_data["sync_mode"]
    ordered_collection["tvdb_show"] = collection_data["tvdb_show"]

    data = {
        "collections": {
            collection_name: ordered_collection
        }
    }

    with open(output_file, "w", encoding="utf-8") as f:
        # Use SafeDumper so our custom representer is used
        yaml.dump(data, f, Dumper=yaml.SafeDumper, sort_keys=False)

def main():
    start_time = datetime.now()
    print(f"{BLUE}{'*' * 40}\n{'*' * 15} TSSK {VERSION} {'*' * 15}\n{'*' * 40}{RESET}")
    check_for_updates()

    config = load_config('config.yml')
    
    try:
        # Process and validate Sonarr URL
        sonarr_url = process_sonarr_url(config['sonarr_url'], config['sonarr_api_key'])
        sonarr_api_key = config['sonarr_api_key']
        
        # Get category-specific future_days values, with fallback to main future_days
        future_days = config.get('future_days', 14)
        future_days_new_season = config.get('future_days_new_season', future_days)
        future_days_upcoming_episode = config.get('future_days_upcoming_episode', future_days)
        future_days_upcoming_finale = config.get('future_days_upcoming_finale', future_days)
        
        # Get recent days values
        recent_days_season_finale = config.get('recent_days_season_finale', 14)
        recent_days_final_episode = config.get('recent_days_final_episode', 14)
        
        skip_unmonitored = str(config.get("skip_unmonitored", "false")).lower() == "true"

        # Print chosen values
        print(f"future_days_new_season: {future_days_new_season}")
        print(f"future_days_upcoming_episode: {future_days_upcoming_episode}")
        print(f"future_days_upcoming_finale: {future_days_upcoming_finale}")
        print(f"recent_days_season_finale: {recent_days_season_finale}")
        print(f"recent_days_final_episode: {recent_days_final_episode}")
        print(f"skip_unmonitored: {skip_unmonitored}\n")

        # Track all tvdbIds to exclude from other categories
        all_excluded_tvdb_ids = set()
        
        # ---- Recent Season Finales ----
        season_finale_shows = find_recent_season_finales(
            sonarr_url, sonarr_api_key, recent_days_season_finale
        )
        
        # Add to excluded IDs
        for show in season_finale_shows:
            if show.get('tvdbId'):
                all_excluded_tvdb_ids.add(show['tvdbId'])
        
        if season_finale_shows:
            print(f"{GREEN}Shows with a season finale that aired within the past {recent_days_season_finale} days:{RESET}")
            for show in season_finale_shows:
                print(f"- {show['title']} (S{show['seasonNumber']}E{show['episodeNumber']}) aired on {show['airDate']}")
        
        create_overlay_yaml("TSSK_TV_SEASON_FINALE_OVERLAYS.yml", season_finale_shows, 
                           {"backdrop": config.get("backdrop_season_finale", {}),
                            "text": config.get("text_season_finale", {})})
        
        create_collection_yaml("TSSK_TV_SEASON_FINALE_COLLECTION.yml", season_finale_shows, config)
        
        # ---- Recent Final Episodes ----
        final_episode_shows = find_recent_final_episodes(
            sonarr_url, sonarr_api_key, recent_days_final_episode
        )
        
        # Add to excluded IDs
        for show in final_episode_shows:
            if show.get('tvdbId'):
                all_excluded_tvdb_ids.add(show['tvdbId'])
        
        if final_episode_shows:
            print(f"\n{GREEN}Shows with a final episode that aired within the past {recent_days_final_episode} days:{RESET}")
            for show in final_episode_shows:
                print(f"- {show['title']} (S{show['seasonNumber']}E{show['episodeNumber']}) aired on {show['airDate']}")
        
        create_overlay_yaml("TSSK_TV_FINAL_EPISODE_OVERLAYS.yml", final_episode_shows, 
                           {"backdrop": config.get("backdrop_final_episode", {}),
                            "text": config.get("text_final_episode", {})})
        
        create_collection_yaml("TSSK_TV_FINAL_EPISODE_COLLECTION.yml", final_episode_shows, config)

        # Track all tvdbIds to exclude from the "returning" category
        all_included_tvdb_ids = set()

        # ---- New Season Shows ----
        matched_shows, skipped_shows = find_new_season_shows(
            sonarr_url, sonarr_api_key, future_days_new_season, skip_unmonitored
        )
        
        # Filter out shows that are in the season finale or final episode categories
        matched_shows = [show for show in matched_shows if show.get('tvdbId') not in all_excluded_tvdb_ids]
        
        # Add to excluded IDs for returning category
        for show in matched_shows:
            if show.get('tvdbId'):
                all_included_tvdb_ids.add(show['tvdbId'])
        
        if matched_shows:
            print(f"\n{GREEN}Shows with a new season starting within {future_days_new_season} days:{RESET}")
            for show in matched_shows:
                print(f"- {show['title']} (Season {show['seasonNumber']}) airs on {show['airDate']}")
        else:
            print(f"{RED}No shows with new seasons starting within {future_days_new_season} days.{RESET}")
        
        if skipped_shows:
            print(f"\n{ORANGE}Skipped shows (unmonitored season):{RESET}")
            for show in skipped_shows:
                print(f"- {show['title']} (Season {show['seasonNumber']}) airs on {show['airDate']}")

        # Create YAMLs for new seasons
        create_overlay_yaml("TSSK_TV_NEW_SEASON_OVERLAYS.yml", matched_shows, 
                           {"backdrop": config.get("backdrop_new_season", config.get("backdrop", {})),
                            "text": config.get("text_new_season", config.get("text", {}))})
        
        create_collection_yaml("TSSK_TV_NEW_SEASON_COLLECTION.yml", matched_shows, config)
        
        # ---- Upcoming Non-Finale Episodes ----
        upcoming_eps, skipped_eps = find_upcoming_regular_episodes(
            sonarr_url, sonarr_api_key, future_days_upcoming_episode, skip_unmonitored=skip_unmonitored
        )
        
        # Filter out shows that are in the season finale or final episode categories
        upcoming_eps = [show for show in upcoming_eps if show.get('tvdbId') not in all_excluded_tvdb_ids]
        
        # Add to excluded IDs for returning category
        for show in upcoming_eps:
            if show.get('tvdbId'):
                all_included_tvdb_ids.add(show['tvdbId'])
        
        if upcoming_eps:
            print(f"\n{GREEN}Shows with upcoming non-finale episodes within {future_days_upcoming_episode} days:{RESET}")
            for show in upcoming_eps:
                print(f"- {show['title']} (S{show['seasonNumber']}E{show['episodeNumber']}) airs on {show['airDate']}")
        
        create_overlay_yaml("TSSK_TV_UPCOMING_EPISODE_OVERLAYS.yml", upcoming_eps, 
                           {"backdrop": config.get("backdrop_upcoming_episode", {}),
                            "text": config.get("text_upcoming_episode", {})})
        
        create_collection_yaml("TSSK_TV_UPCOMING_EPISODE_COLLECTION.yml", upcoming_eps, config)
        
        # ---- Upcoming Finale Episodes ----
        finale_eps, skipped_finales = find_upcoming_finales(
            sonarr_url, sonarr_api_key, future_days_upcoming_finale, skip_unmonitored=skip_unmonitored
        )
        
        # Filter out shows that are in the season finale or final episode categories
        finale_eps = [show for show in finale_eps if show.get('tvdbId') not in all_excluded_tvdb_ids]
        
        # Add to excluded IDs for returning category
        for show in finale_eps:
            if show.get('tvdbId'):
                all_included_tvdb_ids.add(show['tvdbId'])
        
        if finale_eps:
            print(f"\n{GREEN}Shows with upcoming season finales within {future_days_upcoming_finale} days:{RESET}")
            for show in finale_eps:
                print(f"- {show['title']} (S{show['seasonNumber']}E{show['episodeNumber']}) airs on {show['airDate']}")
        
        create_overlay_yaml("TSSK_TV_UPCOMING_FINALE_OVERLAYS.yml", finale_eps, 
                           {"backdrop": config.get("backdrop_upcoming_finale", {}),
                            "text": config.get("text_upcoming_finale", {})})
        
        create_collection_yaml("TSSK_TV_UPCOMING_FINALE_COLLECTION.yml", finale_eps, config)
        
        # ---- Ended Shows ----
        ended_shows = find_ended_shows(sonarr_url, sonarr_api_key)
        
        # Filter out shows that are in the season finale or final episode categories
        ended_shows = [show for show in ended_shows if show.get('tvdbId') not in all_excluded_tvdb_ids]
        
        # Add to excluded IDs for returning category
        for show in ended_shows:
            if show.get('tvdbId'):
                all_included_tvdb_ids.add(show['tvdbId'])
        
#        if ended_shows:
#            print(f"\n{GREEN}Shows that have ended:{RESET}")
#            for show in ended_shows:
#                print(f"- {show['title']}")
        
        create_overlay_yaml("TSSK_TV_ENDED_OVERLAYS.yml", ended_shows, 
                           {"backdrop": config.get("backdrop_ended", {}),
                            "text": config.get("text_ended", {})})
        
        create_collection_yaml("TSSK_TV_ENDED_COLLECTION.yml", ended_shows, config)
        
        # ---- Returning Shows ----
        returning_shows = find_returning_shows(sonarr_url, sonarr_api_key, all_included_tvdb_ids)
        
        # Filter out shows that are in the season finale or final episode categories
        returning_shows = [show for show in returning_shows if show.get('tvdbId') not in all_excluded_tvdb_ids]
        
#        if returning_shows:
#            print(f"\n{GREEN}Shows that are continuing but don't have scheduled episodes:{RESET}")
#            for show in returning_shows:
#                print(f"- {show['title']}")
        
        create_overlay_yaml("TSSK_TV_RETURNING_OVERLAYS.yml", returning_shows, 
                           {"backdrop": config.get("backdrop_returning", {}),
                            "text": config.get("text_returning", {})})
        
        create_collection_yaml("TSSK_TV_RETURNING_COLLECTION.yml", returning_shows, config)
        
        print(f"\nAll YAML files created successfully")

        # Calculate and display runtime
        end_time = datetime.now()
        runtime = end_time - start_time
        hours, remainder = divmod(runtime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        runtime_formatted = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        
        print(f"Total runtime: {runtime_formatted}")

    except ConnectionError as e:
        print(f"{RED}Error: {str(e)}{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{RED}Unexpected error: {str(e)}{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
