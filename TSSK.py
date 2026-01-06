import requests
import yaml
from yaml.representer import SafeRepresenter
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from collections import OrderedDict
import sys
import os
from copy import deepcopy

# Constants
IS_DOCKER = os.getenv("DOCKER", "false").lower() == "true"
VERSION = "2026.01.06"

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

def load_config(file_path='config/config.yml'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Config file '{file_path}' not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML config file: {e}")
        sys.exit(1)

def convert_utc_to_local(utc_date_str, utc_offset):
    if not utc_date_str:
        return None
        
    # Remove 'Z' if present and parse the datetime
    clean_date_str = utc_date_str.replace('Z', '')
    utc_date = datetime.fromisoformat(clean_date_str).replace(tzinfo=timezone.utc)
    
    # Apply the UTC offset
    local_date = utc_date + timedelta(hours=utc_offset)
    return local_date

def debug_print(message, config):
    """Print debug messages only if debug mode is enabled"""
    if config.get('debug', False):
        print(message)

def ensure_output_directory():
    """Ensure the output directory exists and is writable"""
    output_dir = "/config/kometa/tssk/" if IS_DOCKER else "kometa/"
    try:
        os.makedirs(output_dir, exist_ok=True)
        # Test write permissions
        test_file = os.path.join(output_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        print(f"{GREEN}Output directory verified: {output_dir}{RESET}")
        return output_dir
    except Exception as e:
        print(f"{RED}Error: Cannot write to output directory {output_dir}: {str(e)}{RESET}")
        print(f"{RED}Please ensure the directory exists and has proper permissions.{RESET}")
        sys.exit(1)

def process_sonarr_url(base_url, api_key, timeout=90):
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
            response = requests.get(f"{test_url}/health", headers=headers, timeout=timeout)
            if response.status_code == 200:
                print(f"Successfully connected to Sonarr at: {test_url}")
                return test_url
        except requests.exceptions.RequestException as e:
            print(f"{ORANGE}Testing URL {test_url} - Failed: {str(e)}{RESET}")
            continue
    
    raise ConnectionError(f"{RED}Unable to establish connection to Sonarr. Tried the following URLs:\n" + 
                        "\n".join([f"- {base_url}{path}" for path in api_paths]) + 
                        f"\nPlease verify your URL and API key and ensure Sonarr is running.{RESET}")


def get_sonarr_series_and_tags(sonarr_url, api_key, timeout=90):
    try:
        # Fetch series
        print(f"{BLUE}Fetching series from Sonarr...{RESET}", flush=True)
        series_url = f"{sonarr_url}/series"
        headers = {"X-Api-Key": api_key}
        series_response = requests.get(series_url, headers=headers, timeout=timeout)
        series_response.raise_for_status()
        series_data = series_response.json()
        print(f"{GREEN}Done ✓ ({len(series_data)} series){RESET}")

        # Fetch tags
        print(f"{BLUE}Fetching tags from Sonarr...{RESET}", flush=True)
        tags_url = f"{sonarr_url}/tag"
        tags_response = requests.get(tags_url, headers=headers, timeout=timeout)
        tags_response.raise_for_status()
        tags_data = tags_response.json()
        print(f"{GREEN}Done ✓ ({len(tags_data)} tags){RESET}\n")

        # Create tag mapping
        tag_mapping = {}
        for tag in tags_data:
            tag_mapping[tag.get('id')] = tag.get('label', '').lower()
        
        return series_data, tag_mapping
        
    except requests.exceptions.RequestException as e:
        print(f"{ORANGE}Warning: Error connecting to Sonarr: {str(e)}{RESET}")
        print(f"{ORANGE}Continuing with empty series list...{RESET}")
        return [], {}

def get_sonarr_episodes(sonarr_url, api_key, series_id, timeout=90):
    try:
        url = f"{sonarr_url}/episode?seriesId={series_id}"
        headers = {"X-Api-Key": api_key}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"{ORANGE}Warning: Error fetching episodes for series {series_id}: {str(e)}{RESET}")
        print(f"{ORANGE}Skipping this series and continuing...{RESET}")
        return []

def has_ignore_finale_tag(series, ignore_finales_tags, tag_mapping):
    if not ignore_finales_tags or not tag_mapping:
        return False
    
    series_tags = series.get('tags', [])
    if not series_tags:
        return False
    
    ignore_tags_lower = [tag.strip().lower() for tag in ignore_finales_tags]

    for tag_id in series_tags:
        tag_name = tag_mapping.get(tag_id, '').lower()
        if tag_name in ignore_tags_lower:
            return True
    
    return False

def find_new_season_shows(sonarr_url, api_key, all_series, tag_mapping, future_days_new_season, utc_offset=0, skip_unmonitored=False):
    cutoff_date = datetime.now(timezone.utc) + timedelta(days=future_days_new_season)
    now_local = datetime.now(timezone.utc) + timedelta(hours=utc_offset)
    matched_shows = []
    skipped_shows = []
    
    for series in all_series:
        episodes = get_sonarr_episodes(sonarr_url, api_key, series['id'])
        
        future_episodes = []
        for ep in episodes:
            # Skip specials (season 0)
            season_number = ep.get('seasonNumber', 0)
            if season_number == 0:
                continue
                
            air_date_str = ep.get('airDateUtc')
            if not air_date_str:
                continue
            
            air_date = convert_utc_to_local(air_date_str, utc_offset)
            
            # Skip episodes that have already been downloaded - they should be treated as if they've aired
            if ep.get('hasFile', False):
                continue
                
            if air_date > now_local:
                future_episodes.append((ep, air_date))
        
        future_episodes.sort(key=lambda x: x[1])
        
        if not future_episodes:
            continue
        
        next_future, air_date_next = future_episodes[0]
        
        # Check if this is a new season starting (episode 1 of any season)
        # AND check that it's not a completely new show (season 1)
        if (
            next_future['seasonNumber'] > 1
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
        # If it's a completely new show (Season 1), add it to skipped shows for reporting
        elif (
            next_future['seasonNumber'] == 1
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
                'tvdbId': tvdb_id,
                'reason': "New show (Season 1)"  # Add reason for skipping
            }
            
            skipped_shows.append(show_dict)
    
    return matched_shows, skipped_shows

def find_upcoming_regular_episodes(sonarr_url, api_key, all_series, future_days_upcoming_episode, utc_offset=0, skip_unmonitored=False, ignore_finales_tags=None, tag_mapping=None):
    """Find shows with upcoming non-premiere, non-finale episodes within the specified days"""
    cutoff_date = datetime.now(timezone.utc) + timedelta(days=future_days_upcoming_episode)
    now_local = datetime.now(timezone.utc) + timedelta(hours=utc_offset)
    matched_shows = []
    skipped_shows = []
    
    for series in all_series:
        episodes = get_sonarr_episodes(sonarr_url, api_key, series['id'])
        
        # Check if this series should ignore finale detection
        should_ignore_finales = has_ignore_finale_tag(series, ignore_finales_tags, tag_mapping)
        
        # Group episodes by season
        seasons = defaultdict(list)
        for ep in episodes:
            if ep.get('seasonNumber') > 0:  # Skip specials
                seasons[ep.get('seasonNumber')].append(ep)
        
        # For each season, find the max episode number to identify finales
        season_finales = {}
        if not should_ignore_finales:
            for season_num, season_eps in seasons.items():
                if season_eps:
                    max_ep = max(ep.get('episodeNumber', 0) for ep in season_eps)
                    season_finales[season_num] = max_ep
        
        future_episodes = []
        for ep in episodes:
            # Skip specials (season 0)
            season_number = ep.get('seasonNumber', 0)
            if season_number == 0:
                continue
                
            air_date_str = ep.get('airDateUtc')
            if not air_date_str:
                continue
            
            air_date = convert_utc_to_local(air_date_str, utc_offset)
            
            # Skip episodes that have already been downloaded - they should be treated as if they've aired
            if ep.get('hasFile', False):
                continue
                
            if air_date > now_local and air_date <= cutoff_date:
                future_episodes.append((ep, air_date))
        
        future_episodes.sort(key=lambda x: x[1])
        
        if not future_episodes:
            continue
        
        next_future, air_date = future_episodes[0]
        season_num = next_future.get('seasonNumber')
        episode_num = next_future.get('episodeNumber')
        
        # Skip season premieres (episode 1 of any season)
        if episode_num == 1:
            continue
            
        # Skip season finales (only if not ignoring finales)
        if not should_ignore_finales:
            is_episode_finale = season_num in season_finales and episode_num == season_finales[season_num]
            if is_episode_finale:
                continue
        
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

def find_upcoming_finales(sonarr_url, api_key, all_series, future_days_upcoming_finale, utc_offset=0, skip_unmonitored=False, ignore_finales_tags=None, tag_mapping=None):
    """Find shows with upcoming season finales within the specified days"""
    cutoff_date = datetime.now(timezone.utc) + timedelta(days=future_days_upcoming_finale)
    matched_shows = []
    skipped_shows = []
    
    for series in all_series:
        # Skip shows with ignore finale tags
        if has_ignore_finale_tag(series, ignore_finales_tags, tag_mapping):
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
                # Only consider it a finale if it's not episode 1
                if max_ep > 1:
                    season_finales[season_num] = max_ep
        
        future_episodes = []
        for ep in episodes:
            # Skip specials (season 0)
            season_number = ep.get('seasonNumber', 0)
            if season_number == 0:
                continue
                
            air_date_str = ep.get('airDateUtc')
            if not air_date_str:
                continue
            
            air_date = convert_utc_to_local(air_date_str, utc_offset)
            
            now_local = datetime.now(timezone.utc) + timedelta(hours=utc_offset)
            
            # Skip episodes that have already been downloaded - they'll be handled by recent_season_finales
            if ep.get('hasFile', False):
                continue
                
            if air_date > now_local and air_date <= cutoff_date:
                future_episodes.append((ep, air_date))
        
        future_episodes.sort(key=lambda x: x[1])
        
        if not future_episodes:
            continue
        
        next_future, air_date = future_episodes[0]
        season_num = next_future.get('seasonNumber')
        episode_num = next_future.get('episodeNumber')
        
        # Only include season finales and ensure episode number is greater than 1
        is_episode_finale = season_num in season_finales and episode_num == season_finales[season_num] and episode_num > 1
        if not is_episode_finale:
            continue
        
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

def find_recent_season_finales(sonarr_url, api_key, all_series, recent_days_season_finale, utc_offset=0, skip_unmonitored=False, ignore_finales_tags=None, tag_mapping=None):
    """Find shows with status 'continuing' that had a season finale air within the specified days or have a future finale that's already downloaded"""
    now_local = datetime.now(timezone.utc) + timedelta(hours=utc_offset)
    cutoff_date = now_local - timedelta(days=recent_days_season_finale)
    matched_shows = []
    
    for series in all_series:
        # Only include continuing shows
        if series.get('status') not in ['continuing', 'upcoming']:
            continue
            
        # Skip shows with ignore finale tags
        if has_ignore_finale_tag(series, ignore_finales_tags, tag_mapping):
            continue
        
        # Skip unmonitored shows if requested
        if skip_unmonitored and not series.get('monitored', True):
            continue
            
        episodes = get_sonarr_episodes(sonarr_url, api_key, series['id'])
        
        # Group episodes by season and find downloaded episodes
        seasons = defaultdict(list)
        downloaded_episodes = defaultdict(list)
        
        for ep in episodes:
            season_number = ep.get('seasonNumber', 0)
            if season_number > 0:  # Skip specials
                seasons[season_number].append(ep)
                if ep.get('hasFile', False):
                    downloaded_episodes[season_number].append(ep)
        
        # For each season, find the max episode number to identify finales
        season_finales = {}
        for season_num, season_eps in seasons.items():
            # Only consider it a finale if there are multiple episodes in the season
            if len(season_eps) > 1:
                max_ep = max(ep.get('episodeNumber', 0) for ep in season_eps)
                season_finales[season_num] = max_ep
        
        # Look for recently aired season finales
        for season_num, max_episode_num in season_finales.items():
            # Skip if no episodes downloaded for this season
            if season_num not in downloaded_episodes:
                continue
                
            # Find the finale episode
            finale_episode = None
            for ep in downloaded_episodes[season_num]:
                if ep.get('episodeNumber') == max_episode_num:
                    finale_episode = ep
                    break
            
            if not finale_episode:
                continue
                
            # Skip if the season is unmonitored and skip_unmonitored is True
            if skip_unmonitored:
                season_monitored = True
                for season_info in series.get("seasons", []):
                    if season_info.get("seasonNumber") == season_num:
                        season_monitored = season_info.get("monitored", True)
                        break
                
                if not season_monitored:
                    continue
                
                # Also check if the episode itself is monitored
                if not finale_episode.get("monitored", True):
                    continue
            
            air_date_str = finale_episode.get('airDateUtc')
            if not air_date_str:
                continue
                
            air_date = convert_utc_to_local(air_date_str, utc_offset)
            
            # Include if:
            # 1. It aired within the recent period, OR
            # 2. It has a future air date but has already been downloaded
            if (air_date <= now_local and air_date >= cutoff_date) or (air_date > now_local and finale_episode.get('hasFile', False)):
                tvdb_id = series.get('tvdbId')
                
                # If it's a future episode that's already downloaded, use today's date instead
                if air_date > now_local and finale_episode.get('hasFile', False):
                    air_date_str_yyyy_mm_dd = now_local.date().isoformat()
                else:
                    air_date_str_yyyy_mm_dd = air_date.date().isoformat()
                
                show_dict = {
                    'title': series['title'],
                    'seasonNumber': season_num,
                    'episodeNumber': max_episode_num,
                    'airDate': air_date_str_yyyy_mm_dd,
                    'tvdbId': tvdb_id
                }
                
                matched_shows.append(show_dict)
    
    return matched_shows

def find_recent_final_episodes(sonarr_url, api_key, all_series, recent_days_final_episode, utc_offset=0, skip_unmonitored=False, ignore_finales_tags=None, tag_mapping=None):
    """Find shows with status 'ended' that had their final episode air within the specified days or have a future final episode that's already downloaded"""
    now_local = datetime.now(timezone.utc) + timedelta(hours=utc_offset)
    cutoff_date = now_local - timedelta(days=recent_days_final_episode)
    matched_shows = []
  
    for series in all_series:
        # Only include ended shows
        if series.get('status') != 'ended':
            continue
            
        # Skip shows with ignore finale tags
        if has_ignore_finale_tag(series, ignore_finales_tags, tag_mapping):
            continue
            
        # Skip unmonitored shows if requested
        if skip_unmonitored and not series.get('monitored', True):
            continue
            
        episodes = get_sonarr_episodes(sonarr_url, api_key, series['id'])
        
        # Group episodes by season and find downloaded episodes
        seasons = defaultdict(list)
        downloaded_episodes = defaultdict(list)
        
        for ep in episodes:
            season_number = ep.get('seasonNumber', 0)
            if season_number > 0:  # Skip specials
                seasons[season_number].append(ep)
                if ep.get('hasFile', False):
                    downloaded_episodes[season_number].append(ep)
        
        # Skip if no episodes downloaded
        if not any(downloaded_episodes.values()):
            continue
            
        # Find the highest season with downloaded episodes
        max_season = max(downloaded_episodes.keys()) if downloaded_episodes else 0
        
        # Skip if no valid seasons found
        if max_season == 0:
            continue
            
        # Find the highest episode number in the highest season
        max_episode_num = max(ep.get('episodeNumber', 0) for ep in downloaded_episodes[max_season])
        
        # Find the final episode
        final_episode = None
        for ep in downloaded_episodes[max_season]:
            if ep.get('episodeNumber') == max_episode_num:
                final_episode = ep
                break
        
        if not final_episode:
            continue
            
        # Skip if the season is unmonitored and skip_unmonitored is True
        if skip_unmonitored:
            season_monitored = True
            for season_info in series.get("seasons", []):
                if season_info.get("seasonNumber") == max_season:
                    season_monitored = season_info.get("monitored", True)
                    break
            
            if not season_monitored:
                continue
            
            # Also check if the episode itself is monitored
            if not final_episode.get("monitored", True):
                continue
        
        # Check if there are any future episodes that aren't downloaded
        has_future_undownloaded_episodes = False
        for ep in episodes:
            air_date_str = ep.get('airDateUtc')
            season_number = ep.get('seasonNumber', 0)
            has_file = ep.get('hasFile', False)
            
            if season_number == 0:  # Skip specials
                continue
                
            if air_date_str:
                air_date = convert_utc_to_local(air_date_str, utc_offset)
                if air_date > now_local and not has_file:
                    has_future_undownloaded_episodes = True
                    break
        
        if has_future_undownloaded_episodes:
            continue
            
        air_date_str = final_episode.get('airDateUtc')
        if not air_date_str:
            continue
            
        air_date = convert_utc_to_local(air_date_str, utc_offset)
        
        # Include if:
        # 1. It aired within the recent period, OR
        # 2. It has a future air date but has already been downloaded
        if (air_date <= now_local and air_date >= cutoff_date) or (air_date > now_local and final_episode.get('hasFile', False)):
            tvdb_id = series.get('tvdbId')
            
            # If it's a future episode that's already downloaded, use today's date instead
            if air_date > now_local and final_episode.get('hasFile', False):
                air_date_str_yyyy_mm_dd = now_local.date().isoformat()
            else:
                air_date_str_yyyy_mm_dd = air_date.date().isoformat()
            
            show_dict = {
                'title': series['title'],
                'seasonNumber': max_season,
                'episodeNumber': max_episode_num,
                'airDate': air_date_str_yyyy_mm_dd,
                'tvdbId': tvdb_id
            }
            
            matched_shows.append(show_dict)
    
    return matched_shows

def find_new_season_started(sonarr_url, api_key, all_series, recent_days_new_season_started, utc_offset=0, skip_unmonitored=False):
    """Find shows where a new season (not season 1) has been downloaded within the specified days"""
    now_local = datetime.now(timezone.utc) + timedelta(hours=utc_offset)
    cutoff_date = now_local - timedelta(days=recent_days_new_season_started)
    matched_shows = []
   
    for series in all_series:
        # Skip unmonitored shows if requested
        if skip_unmonitored and not series.get('monitored', True):
            continue
            
        episodes = get_sonarr_episodes(sonarr_url, api_key, series['id'])
        
        # Group episodes by season and find downloaded episodes
        seasons = defaultdict(list)
        downloaded_episodes = defaultdict(list)
        
        for ep in episodes:
            season_number = ep.get('seasonNumber', 0)
            if season_number > 0:  # Skip specials
                seasons[season_number].append(ep)
                if ep.get('hasFile', False):
                    downloaded_episodes[season_number].append(ep)
        
        # Skip if there's only one season (new show)
        if len(seasons) <= 1:
            continue
            
        # Find the highest season number with downloaded episodes
        if not downloaded_episodes:
            continue
            
        max_season_with_downloads = max(downloaded_episodes.keys())
        
        # Skip if it's season 1 (new show)
        if max_season_with_downloads <= 1:
            continue
            
        # Check if there are previous seasons with downloads (to confirm it's not a new show)
        has_previous_season_downloads = any(season < max_season_with_downloads for season in downloaded_episodes.keys())
        if not has_previous_season_downloads:
            continue
        
        # Find the first episode of the highest season that was downloaded
        season_episodes = downloaded_episodes[max_season_with_downloads]
        first_episode = min(season_episodes, key=lambda ep: ep.get('episodeNumber', 999))
        
        # Skip if the season is unmonitored and skip_unmonitored is True
        if skip_unmonitored:
            season_monitored = True
            for season_info in series.get("seasons", []):
                if season_info.get("seasonNumber") == max_season_with_downloads:
                    season_monitored = season_info.get("monitored", True)
                    break
            
            if not season_monitored:
                continue
            
            # Also check if the episode itself is monitored
            if not first_episode.get("monitored", True):
                continue
        
        # Check when this episode was downloaded (use air date as proxy)
        air_date_str = first_episode.get('airDateUtc')
        if not air_date_str:
            continue
            
        air_date = convert_utc_to_local(air_date_str, utc_offset)
        
        # Include if it aired within the recent period (assuming download happened around air date)
        if air_date >= cutoff_date and air_date <= now_local:
            tvdb_id = series.get('tvdbId')
            air_date_str_yyyy_mm_dd = air_date.date().isoformat()
            
            show_dict = {
                'title': series['title'],
                'seasonNumber': max_season_with_downloads,
                'episodeNumber': first_episode.get('episodeNumber'),
                'airDate': air_date_str_yyyy_mm_dd,
                'tvdbId': tvdb_id
            }
            
            matched_shows.append(show_dict)
    
    return matched_shows

def format_date(yyyy_mm_dd, date_format, capitalize=False, simplify_next_week=False, utc_offset=0):
    dt_obj = datetime.strptime(yyyy_mm_dd, "%Y-%m-%d")
    
    # If simplify_next_week is enabled, check if date is within next 7 days
    if simplify_next_week:
        now_local = datetime.now(timezone.utc) + timedelta(hours=utc_offset)
        today = now_local.date()
        date_obj = dt_obj.date()
        days_diff = (date_obj - today).days
        
        # Check if date is within the next 7 days (0-6 days from today)
        if 0 <= days_diff <= 6:
            if days_diff == 0:
                result = "today"
            elif days_diff == 1:
                result = "tomorrow"
            else:
                # Use full weekday name
                result = dt_obj.strftime('%A').lower()
            
            if capitalize:
                result = result.upper()
            return result
    
    # Original date formatting logic
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

def create_collection_yaml(output_file, shows, config):
    # Ensure the directory exists
    output_dir = "/config/kometa/tssk/" if IS_DOCKER else "kometa/"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"{RED}Error creating directory {output_dir}: {str(e)}{RESET}")
        return
    
    output_file_path = os.path.join(output_dir, output_file)

    try:
        # Add representer for OrderedDict
        def represent_ordereddict(dumper, data):
            return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())
        
        yaml.add_representer(OrderedDict, represent_ordereddict, Dumper=yaml.SafeDumper)

        # Determine collection type and get the appropriate config section
        collection_config = {}
        collection_name = ""
        default_summary = ""
        
        if "SEASON_FINALE" in output_file:
            config_key = "collection_season_finale"
            default_summary = f"Shows with a season finale that aired within the past {config.get('recent_days_season_finale', 21)} days"
        elif "FINAL_EPISODE" in output_file:
            config_key = "collection_final_episode"
            default_summary = f"Shows with a final episode that aired within the past {config.get('recent_days_final_episode', 21)} days"
        elif "NEW_SEASON_STARTED" in output_file:
            config_key = "collection_new_season_started"
            default_summary = f"Shows with a new season that started within the past {config.get('recent_days_new_season_started', 14)} days"
        elif "NEW_SEASON" in output_file:
            config_key = "collection_new_season"
            default_summary = f"Shows with a new season starting within {config.get('future_days_new_season', 31)} days"
        elif "UPCOMING_EPISODE" in output_file:
            config_key = "collection_upcoming_episode"
            default_summary = f"Shows with an upcoming episode within {config.get('future_days_upcoming_episode', 31)} days"
        elif "UPCOMING_FINALE" in output_file:
            config_key = "collection_upcoming_finale"
            default_summary = f"Shows with a season finale within {config.get('future_days_upcoming_finale', 31)} days"
        else:
            # Default fallback
            config_key = None
            collection_name = "TV Collection"
            default_summary = "TV Collection"
        
        # Get the collection configuration if available
        if config_key and config_key in config:
            # Create a deep copy to avoid modifying the original config
            collection_config = deepcopy(config[config_key])
            # Extract the collection name and remove it from the config
            collection_name = collection_config.pop("collection_name", "TV Collection")
        
        # Extract user-provided summary and sort_title
        user_summary = collection_config.pop("summary", None)
        user_sort_title = collection_config.pop("sort_title", None)
        
        # Use user summary if provided, otherwise use default
        summary = user_summary if user_summary else default_summary
        
        class QuotedString(str):
            pass

        def quoted_str_presenter(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

        yaml.add_representer(QuotedString, quoted_str_presenter, Dumper=yaml.SafeDumper)

        # Handle the case when no shows are found
        if not shows:
            # Create the template for empty collections
            data = {
                "collections": {
                    collection_name: {
                        "plex_search": {
                            "all": {
                                "label": collection_name
                            }
                        },
                        "item_label.remove": collection_name,
                        "smart_label": "random",
                        "build_collection": False
                    }
                }
            }
            
            with open(output_file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, Dumper=yaml.SafeDumper, sort_keys=False)
            debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
            return
        
        tvdb_ids = [s['tvdbId'] for s in shows if s.get('tvdbId')]
        if not tvdb_ids:
            # Create the template for empty collections
            data = {
                "collections": {
                    collection_name: {
                        "plex_search": {
                            "all": {
                                "label": collection_name
                            }
                        },
                        "non_item_remove_label": collection_name,
                        "build_collection": False
                    }
                }
            }
            
            with open(output_file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, Dumper=yaml.SafeDumper, sort_keys=False)
            debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
            return

        # Convert to comma-separated
        tvdb_ids_str = ", ".join(str(i) for i in sorted(tvdb_ids))

        # Create the collection data structure as a regular dict
        collection_data = {}
        collection_data["summary"] = summary
        
        # Add sort_title if user provided it
        if user_sort_title:
            collection_data["sort_title"] = QuotedString(user_sort_title)
        
        # Add all remaining parameters from the collection config
        for key, value in collection_config.items():
            collection_data[key] = value
            
        # Add tvdb_show as the last item
        collection_data["tvdb_show"] = tvdb_ids_str

        # Create the final structure with ordered keys
        ordered_collection = OrderedDict()
        
        # Add summary first
        ordered_collection["summary"] = collection_data["summary"]
        
        # Add sort_title second (if it exists)
        if "sort_title" in collection_data:
            ordered_collection["sort_title"] = collection_data["sort_title"]
        
        # Add all other keys except summary, sort_title, and tvdb_show
        for key, value in collection_data.items():
            if key not in ["summary", "sort_title", "tvdb_show"]:
                ordered_collection[key] = value
        
        # Add tvdb_show at the end
        ordered_collection["tvdb_show"] = collection_data["tvdb_show"]

        data = {
            "collections": {
                collection_name: ordered_collection
            }
        }

        with open(output_file_path, "w", encoding="utf-8") as f:
            # Use SafeDumper so our custom representer is used
            yaml.dump(data, f, Dumper=yaml.SafeDumper, sort_keys=False)
        debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
        
    except Exception as e:
        print(f"{RED}Error writing file {output_file_path}: {str(e)}{RESET}")

def create_overlay_yaml(output_file, shows, config_sections, config, backdrop_block_name="backdrop"):
    # Ensure the directory exists
    output_dir = "/config/kometa/tssk/" if IS_DOCKER else "kometa/"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"{RED}Error creating directory {output_dir}: {str(e)}{RESET}")
        return
    
    output_file_path = os.path.join(output_dir, output_file)

    try:
        if not shows:
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write("#No matching shows found")
            debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
            return
        
        # Check if this is a new season overlay (needs season number grouping)
        is_new_season = "NEW_SEASON_OVERLAYS" in output_file or "NEW_SEASON_STARTED_OVERLAYS" in output_file
        is_new_season_started = "NEW_SEASON_STARTED_OVERLAYS" in output_file
        is_upcoming_finale = "UPCOMING_FINALE_OVERLAYS" in output_file
        is_season_finale = "SEASON_FINALE_OVERLAYS" in output_file
        
        # Check if [#] placeholder is being used
        use_text_value = config_sections.get("text", {}).get("use_text", "")
        has_season_placeholder = "[#]" in use_text_value
        
        # Group shows by date and season number if it's new season overlay
        date_season_to_tvdb_ids = defaultdict(lambda: defaultdict(list))
        season_to_tvdb_ids = defaultdict(list)  # For NEW_SEASON_STARTED and SEASON_FINALE with [#] (no dates)
        date_to_tvdb_ids = defaultdict(list)
        all_tvdb_ids = set()
        
        # Check if this is a category that doesn't need dates
        no_date_needed = "SEASON_FINALE" in output_file or "FINAL_EPISODE" in output_file
        
        for s in shows:
            if s.get("tvdbId"):
                all_tvdb_ids.add(s['tvdbId'])
            
            # For NEW_SEASON_STARTED or SEASON_FINALE with [#], group by season only (no dates)
            if (is_new_season_started or is_season_finale) and has_season_placeholder and s.get("seasonNumber"):
                season_to_tvdb_ids[s['seasonNumber']].append(s.get('tvdbId'))
            # For NEW_SEASON or UPCOMING_FINALE with [#], group by date AND season
            elif (is_new_season or is_upcoming_finale) and has_season_placeholder and s.get("airDate") and s.get("seasonNumber"):
                date_season_to_tvdb_ids[s['airDate']][s['seasonNumber']].append(s.get('tvdbId'))
            # For all other cases with dates (including NEW_SEASON without [#])
            elif s.get("airDate") and not no_date_needed:
                date_to_tvdb_ids[s['airDate']].append(s.get('tvdbId'))
        
        overlays_dict = {}
        
        # -- Backdrop Block --
        backdrop_config = deepcopy(config_sections.get("backdrop", {}))
        # Extract enable flag and default to True if not specified
        enable_backdrop = backdrop_config.pop("enable", True)

        # Only add backdrop overlay if enabled
        if enable_backdrop and all_tvdb_ids:
            # Check if user provided a custom name
            if "name" not in backdrop_config:
                backdrop_config["name"] = "backdrop"
            all_tvdb_ids_str = ", ".join(str(i) for i in sorted(all_tvdb_ids) if i)
            
            overlays_dict[backdrop_block_name] = {
                "overlay": backdrop_config,
                "tvdb_show": all_tvdb_ids_str
            }
        
        # -- Text Blocks --
        text_config = deepcopy(config_sections.get("text", {}))
        enable_text = text_config.pop("enable", True)
        
        # Get global settings
        simplify_next_week = config.get("simplify_next_week_dates", False)
        utc_offset = float(config.get('utc_offset', 0))
        
        if enable_text and all_tvdb_ids:
            date_format = text_config.pop("date_format", "yyyy-mm-dd")
            use_text = text_config.pop("use_text", "New Season")
            # capitalize_dates is category-specific, extracted from text_config
            capitalize_dates = text_config.pop("capitalize_dates", True)
            
            # Check if user provided a custom name
            has_custom_name = "name" in text_config
            
            # For NEW_SEASON_STARTED or SEASON_FINALE with [#] placeholder (no dates)
            if (is_new_season_started or is_season_finale) and has_season_placeholder and season_to_tvdb_ids:
                for season_num in sorted(season_to_tvdb_ids.keys()):
                    sub_overlay_config = deepcopy(text_config)
                    
                    # Replace [#] with actual season number
                    season_text = use_text.replace("[#]", str(season_num))
                    
                    # Only set name if user didn't provide a custom one
                    if not has_custom_name:
                        sub_overlay_config["name"] = f"text({season_text})"
                    
                    tvdb_ids_for_season = sorted(tvdb_id for tvdb_id in season_to_tvdb_ids[season_num] if tvdb_id)
                    tvdb_ids_str = ", ".join(str(i) for i in tvdb_ids_for_season)
                    
                    block_key = f"TSSK_S{season_num}"
                    overlays_dict[block_key] = {
                        "overlay": sub_overlay_config,
                        "tvdb_show": tvdb_ids_str
                    }
            # For NEW_SEASON_STARTED or SEASON_FINALE without [#] placeholder (no dates needed, group all shows together)
            elif (is_new_season_started or is_season_finale) and not has_season_placeholder:
                sub_overlay_config = deepcopy(text_config)
                
                # Only set name if user didn't provide a custom one
                if not has_custom_name:
                    sub_overlay_config["name"] = f"text({use_text})"
                
                tvdb_ids_str = ", ".join(str(i) for i in sorted(all_tvdb_ids) if i)
                
                # Determine block key based on category
                if is_new_season_started:
                    block_key = "TSSK_new_season_started"
                else:  # is_season_finale
                    block_key = "TSSK_season_finale"
                
                overlays_dict[block_key] = {
                    "overlay": sub_overlay_config,
                    "tvdb_show": tvdb_ids_str
                }
            # For NEW_SEASON and UPCOMING_FINALE with [#] placeholder (with dates)
            elif (is_new_season or is_upcoming_finale) and has_season_placeholder and date_season_to_tvdb_ids:
                for date_str in sorted(date_season_to_tvdb_ids):
                    formatted_date = format_date(date_str, date_format, capitalize_dates, simplify_next_week, utc_offset)
                    
                    # Group by season number for this date
                    for season_num in sorted(date_season_to_tvdb_ids[date_str].keys()):
                        sub_overlay_config = deepcopy(text_config)
                        
                        # Replace [#] with actual season number
                        season_text = use_text.replace("[#]", str(season_num))
                        
                        # Only set name if user didn't provide a custom one
                        if not has_custom_name:
                            sub_overlay_config["name"] = f"text({season_text} {formatted_date})"
                        
                        tvdb_ids_for_date_season = sorted(tvdb_id for tvdb_id in date_season_to_tvdb_ids[date_str][season_num] if tvdb_id)
                        tvdb_ids_str = ", ".join(str(i) for i in tvdb_ids_for_date_season)
                        
                        block_key = f"TSSK_{formatted_date}_S{season_num}"
                        overlays_dict[block_key] = {
                            "overlay": sub_overlay_config,
                            "tvdb_show": tvdb_ids_str
                        }
            # For categories that need dates and shows with air dates (no [#] placeholder)
            elif date_to_tvdb_ids and not no_date_needed and not is_new_season_started and not is_season_finale and not (is_upcoming_finale and has_season_placeholder):
                for date_str in sorted(date_to_tvdb_ids):
                    formatted_date = format_date(date_str, date_format, capitalize_dates, simplify_next_week, utc_offset)
                    sub_overlay_config = deepcopy(text_config)
                    
                    # Only set name if user didn't provide a custom one
                    if not has_custom_name:
                        sub_overlay_config["name"] = f"text({use_text} {formatted_date})"
                    
                    tvdb_ids_for_date = sorted(tvdb_id for tvdb_id in date_to_tvdb_ids[date_str] if tvdb_id)
                    tvdb_ids_str = ", ".join(str(i) for i in tvdb_ids_for_date)
                    
                    block_key = f"TSSK_{formatted_date}"
                    overlays_dict[block_key] = {
                        "overlay": sub_overlay_config,
                        "tvdb_show": tvdb_ids_str
                    }
            # For shows without air dates or categories that don't need dates
            else:
                sub_overlay_config = deepcopy(text_config)
                
                # Only set name if user didn't provide a custom one
                if not has_custom_name:
                    sub_overlay_config["name"] = f"text({use_text})"
                
                tvdb_ids_str = ", ".join(str(i) for i in sorted(all_tvdb_ids) if i)
                
                # Extract category name from filename
                if is_new_season_started:
                    block_key = "TSSK_new_season_started"
                elif is_season_finale:
                    block_key = "TSSK_season_finale"
                elif "FINAL_EPISODE" in output_file:
                    block_key = "TSSK_final_episode"
                elif is_upcoming_finale:
                    block_key = "TSSK_upcoming_finale"
                else:
                    block_key = "TSSK_text"  # fallback
                
                overlays_dict[block_key] = {
                    "overlay": sub_overlay_config,
                    "tvdb_show": tvdb_ids_str
                }
        
        final_output = {"overlays": overlays_dict}
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            yaml.dump(final_output, f, sort_keys=False)
        debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
        
    except Exception as e:
        print(f"{RED}Error writing file {output_file_path}: {str(e)}{RESET}")

def create_new_show_collection_yaml(output_file, config, recent_days):
    # Ensure the directory exists
    output_dir = "/config/kometa/tssk/" if IS_DOCKER else "kometa/"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"{RED}Error creating directory {output_dir}: {str(e)}{RESET}")
        return
    
    output_file_path = os.path.join(output_dir, output_file)

    try:
        # Add representer for OrderedDict
        def represent_ordereddict(dumper, data):
            return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())
        
        yaml.add_representer(OrderedDict, represent_ordereddict, Dumper=yaml.SafeDumper)

        class QuotedString(str):
            pass

        def quoted_str_presenter(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

        yaml.add_representer(QuotedString, quoted_str_presenter, Dumper=yaml.SafeDumper)

        # Get collection configuration
        collection_config = deepcopy(config.get("collection_new_show", {}))
        collection_name = collection_config.pop("collection_name", "New Shows")
        
        # Extract user-provided summary and sort_title
        user_summary = collection_config.pop("summary", None)
        user_sort_title = collection_config.pop("sort_title", None)
        
        # Use user summary if provided, otherwise use default
        summary = user_summary if user_summary else f"New Shows added in the past {recent_days} days"

        # Create the collection data structure as a regular dict
        collection_data = {}
        collection_data["summary"] = summary
        
        # Add sort_title if user provided it
        if user_sort_title:
            collection_data["sort_title"] = QuotedString(user_sort_title)
        
        # Add all remaining parameters from the collection config
        for key, value in collection_config.items():
            collection_data[key] = value
            
        # Add plex_all and filters instead of tvdb_show
        collection_data["plex_all"] = True
        collection_data["filters"] = {
            "added": recent_days,
            "label.not": "Coming Soon"
        }

        # Create the final structure with ordered keys
        ordered_collection = OrderedDict()
        
        # Add summary first
        ordered_collection["summary"] = collection_data["summary"]
        
        # Add sort_title second (if it exists)
        if "sort_title" in collection_data:
            ordered_collection["sort_title"] = collection_data["sort_title"]
        
        # Add all other keys except summary, sort_title, plex_all, and filters
        for key, value in collection_data.items():
            if key not in ["summary", "sort_title", "plex_all", "filters"]:
                ordered_collection[key] = value
        
        # Add plex_all and filters at the end
        ordered_collection["plex_all"] = collection_data["plex_all"]
        ordered_collection["filters"] = collection_data["filters"]

        data = {
            "collections": {
                collection_name: ordered_collection
            }
        }

        with open(output_file_path, "w", encoding="utf-8") as f:
            # Use SafeDumper so our custom representer is used
            yaml.dump(data, f, Dumper=yaml.SafeDumper, sort_keys=False)
        debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
        
    except Exception as e:
        print(f"{RED}Error writing file {output_file_path}: {str(e)}{RESET}")

def create_new_show_overlay_yaml(output_file, config_sections, recent_days, config, backdrop_block_name="backdrop_new_show"):
    """Create overlay YAML for new shows using Plex filters instead of Sonarr data"""  
    # Ensure the directory exists
    output_dir = "/config/kometa/tssk/" if IS_DOCKER else "kometa/"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"{RED}Error creating directory {output_dir}: {str(e)}{RESET}")
        return
    
    output_file_path = os.path.join(output_dir, output_file)
    
    try:
        overlays_dict = {}
        
        # -- Backdrop Block --
        backdrop_config = deepcopy(config_sections.get("backdrop", {}))
        enable_backdrop = backdrop_config.pop("enable", True)
        
        if enable_backdrop:
            # Check if user provided a custom name
            if "name" not in backdrop_config:
                backdrop_config["name"] = "backdrop"
            overlays_dict[backdrop_block_name] = {
                "plex_all": True,
                "filters": {
                    "added": recent_days,
                    "label.not": "Coming Soon, RequestNeeded"
                },
                "overlay": backdrop_config
            }
        
        # -- Text Block --
        text_config = deepcopy(config_sections.get("text", {}))
        enable_text = text_config.pop("enable", True)
        
        if enable_text:
            use_text = text_config.pop("use_text", "New Show")
            text_config.pop("date_format", None)  # Remove if present
            text_config.pop("capitalize_dates", None)  # Remove if present
            
            # Check if user provided a custom name
            if "name" not in text_config:
                text_config["name"] = f"text({use_text})"
            
            overlays_dict["new_show"] = {
                "plex_all": True,
                "filters": {
                    "added": recent_days,
                    "label.not": "Coming Soon, RequestNeeded"
                },
                "overlay": text_config
            }
        
        final_output = {"overlays": overlays_dict}
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            yaml.dump(final_output, f, sort_keys=False)
        debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
        
    except Exception as e:
        print(f"{RED}Error writing file {output_file_path}: {str(e)}{RESET}")

def create_returning_show_collection_yaml(output_file, config, use_tvdb=False):
    """Create collection YAML for returning shows using Plex filters instead of Sonarr data"""
    # Ensure the directory exists
    output_dir = "/config/kometa/tssk/" if IS_DOCKER else "kometa/"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"{RED}Error creating directory {output_dir}: {str(e)}{RESET}")
        return
    
    output_file_path = os.path.join(output_dir, output_file)

    try:
        # Add representer for OrderedDict
        def represent_ordereddict(dumper, data):
            return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())
        
        yaml.add_representer(OrderedDict, represent_ordereddict, Dumper=yaml.SafeDumper)

        class QuotedString(str):
            pass

        def quoted_str_presenter(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

        yaml.add_representer(QuotedString, quoted_str_presenter, Dumper=yaml.SafeDumper)

        # Get collection configuration
        collection_config = deepcopy(config.get("collection_returning", {}))
        collection_name = collection_config.pop("collection_name", "Returning Shows")
        
        # Extract user-provided summary and sort_title
        user_summary = collection_config.pop("summary", None)
        user_sort_title = collection_config.pop("sort_title", None)
        
        # Use user summary if provided, otherwise use default
        summary = user_summary if user_summary else "Returning Shows without upcoming episodes within the chosen timeframes"
        
        # Extract additional filters from config
        additional_filters = collection_config.pop("filters", {})

        # Create the collection data structure as a regular dict
        collection_data = {}
        collection_data["summary"] = summary
        
        # Add sort_title if user provided it
        if user_sort_title:
            collection_data["sort_title"] = QuotedString(user_sort_title)
        
        # Add all remaining parameters from the collection config
        for key, value in collection_config.items():
            collection_data[key] = value
            
        # Add plex_all and filters instead of tvdb_show
        collection_data["plex_all"] = True
        status_filter = "tvdb_status" if use_tvdb else "tmdb_status"
        status_value = "continuing" if use_tvdb else "returning"
        
        # Create filters dict with status filter first, then additional filters
        filters_dict = {status_filter: status_value}
        filters_dict.update(additional_filters)
        collection_data["filters"] = filters_dict

        # Create the final structure with ordered keys
        ordered_collection = OrderedDict()
        
        # Add summary first
        ordered_collection["summary"] = collection_data["summary"]
        
        # Add sort_title second (if it exists)
        if "sort_title" in collection_data:
            ordered_collection["sort_title"] = collection_data["sort_title"]
        
        # Add all other keys except summary, sort_title, plex_all, and filters
        for key, value in collection_data.items():
            if key not in ["summary", "sort_title", "plex_all", "filters"]:
                ordered_collection[key] = value
        
        # Add plex_all and filters at the end
        ordered_collection["plex_all"] = collection_data["plex_all"]
        ordered_collection["filters"] = collection_data["filters"]

        data = {
            "collections": {
                collection_name: ordered_collection
            }
        }

        with open(output_file_path, "w", encoding="utf-8") as f:
            # Use SafeDumper so our custom representer is used
            yaml.dump(data, f, Dumper=yaml.SafeDumper, sort_keys=False)
        debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
        
    except Exception as e:
        print(f"{RED}Error writing file {output_file_path}: {str(e)}{RESET}")

def create_returning_show_overlay_yaml(output_file, config_sections, use_tvdb=False, config=None, backdrop_block_name="backdrop_returning"):
    """Create overlay YAML for returning shows using Plex filters instead of Sonarr data"""  
    # Ensure the directory exists
    output_dir = "/config/kometa/tssk/" if IS_DOCKER else "kometa/"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"{RED}Error creating directory {output_dir}: {str(e)}{RESET}")
        return
    
    output_file_path = os.path.join(output_dir, output_file)
    
    try:
        overlays_dict = {}
        
        # -- Backdrop Block --
        backdrop_config = deepcopy(config_sections.get("backdrop", {}))
        enable_backdrop = backdrop_config.pop("enable", True)
        
        # Extract additional filters from backdrop config
        backdrop_additional_filters = backdrop_config.pop("filters", {})
        
        status_filter = "tvdb_status" if use_tvdb else "tmdb_status"
        status_value = "continuing" if use_tvdb else "returning"
        
        if enable_backdrop:
            # Check if user provided a custom name
            if "name" not in backdrop_config:
                backdrop_config["name"] = "backdrop"
            
            # Create filters dict with status filter first, then additional filters
            backdrop_filters = {status_filter: status_value}
            backdrop_filters.update(backdrop_additional_filters)
            
            overlays_dict[backdrop_block_name] = {
                "plex_all": True,
                "filters": backdrop_filters,
                "overlay": backdrop_config
            }
        
        # -- Text Block --
        text_config = deepcopy(config_sections.get("text", {}))
        enable_text = text_config.pop("enable", True)
        
        # Extract additional filters from text config
        text_additional_filters = text_config.pop("filters", {})
        
        if enable_text:
            use_text = text_config.pop("use_text", "Returning")
            text_config.pop("date_format", None)  # Remove if present
            text_config.pop("capitalize_dates", None)  # Remove if present
            
            # Check if user provided a custom name
            if "name" not in text_config:
                text_config["name"] = f"text({use_text})"
            
            # Create filters dict with status filter first, then additional filters
            text_filters = {status_filter: status_value}
            text_filters.update(text_additional_filters)
            
            overlays_dict["returning_show"] = {
                "plex_all": True,
                "filters": text_filters,
                "overlay": text_config
            }
        
        final_output = {"overlays": overlays_dict}
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            yaml.dump(final_output, f, sort_keys=False)
        if config:
            debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
        
    except Exception as e:
        print(f"{RED}Error writing file {output_file_path}: {str(e)}{RESET}")

def create_ended_show_collection_yaml(output_file, config, use_tvdb=False):
    """Create collection YAML for ended shows using Plex filters instead of Sonarr data"""
    # Ensure the directory exists
    output_dir = "/config/kometa/tssk/" if IS_DOCKER else "kometa/"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"{RED}Error creating directory {output_dir}: {str(e)}{RESET}")
        return
    
    output_file_path = os.path.join(output_dir, output_file)

    try:
        # Add representer for OrderedDict
        def represent_ordereddict(dumper, data):
            return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())
        
        yaml.add_representer(OrderedDict, represent_ordereddict, Dumper=yaml.SafeDumper)

        class QuotedString(str):
            pass

        def quoted_str_presenter(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

        yaml.add_representer(QuotedString, quoted_str_presenter, Dumper=yaml.SafeDumper)

        # Get collection configuration
        collection_config = deepcopy(config.get("collection_ended", {}))
        collection_name = collection_config.pop("collection_name", "Ended Shows")
        
        # Extract user-provided summary and sort_title
        user_summary = collection_config.pop("summary", None)
        user_sort_title = collection_config.pop("sort_title", None)
        
        # Use user summary if provided, otherwise use default
        summary = user_summary if user_summary else "Shows that have ended"
        
        # Extract additional filters from config
        additional_filters = collection_config.pop("filters", {})

        # Create the collection data structure as a regular dict
        collection_data = {}
        collection_data["summary"] = summary
        
        # Add sort_title if user provided it
        if user_sort_title:
            collection_data["sort_title"] = QuotedString(user_sort_title)
        
        # Add all remaining parameters from the collection config
        for key, value in collection_config.items():
            collection_data[key] = value
            
        # Add plex_all and filters instead of tvdb_show
        collection_data["plex_all"] = True
        status_filter = "tvdb_status" if use_tvdb else "tmdb_status"
        
        # Create filters dict with status filter first, then additional filters
        filters_dict = {status_filter: "ended"}
        filters_dict.update(additional_filters)
        collection_data["filters"] = filters_dict

        # Create the final structure with ordered keys
        ordered_collection = OrderedDict()
        
        # Add summary first
        ordered_collection["summary"] = collection_data["summary"]
        
        # Add sort_title second (if it exists)
        if "sort_title" in collection_data:
            ordered_collection["sort_title"] = collection_data["sort_title"]
        
        # Add all other keys except summary, sort_title, plex_all, and filters
        for key, value in collection_data.items():
            if key not in ["summary", "sort_title", "plex_all", "filters"]:
                ordered_collection[key] = value
        
        # Add plex_all and filters at the end
        ordered_collection["plex_all"] = collection_data["plex_all"]
        ordered_collection["filters"] = collection_data["filters"]

        data = {
            "collections": {
                collection_name: ordered_collection
            }
        }

        with open(output_file_path, "w", encoding="utf-8") as f:
            # Use SafeDumper so our custom representer is used
            yaml.dump(data, f, Dumper=yaml.SafeDumper, sort_keys=False)
        debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
        
    except Exception as e:
        print(f"{RED}Error writing file {output_file_path}: {str(e)}{RESET}")

def create_ended_show_overlay_yaml(output_file, config_sections, use_tvdb=False, config=None, backdrop_block_name="backdrop_ended"):
    """Create overlay YAML for ended shows using Plex filters instead of Sonarr data"""  
    # Ensure the directory exists
    output_dir = "/config/kometa/tssk/" if IS_DOCKER else "kometa/"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"{RED}Error creating directory {output_dir}: {str(e)}{RESET}")
        return
    
    output_file_path = os.path.join(output_dir, output_file)
    
    try:
        overlays_dict = {}
        
        # -- Backdrop Block --
        backdrop_config = deepcopy(config_sections.get("backdrop", {}))
        enable_backdrop = backdrop_config.pop("enable", True)
        
        # Extract additional filters from backdrop config
        backdrop_additional_filters = backdrop_config.pop("filters", {})
        
        status_filter = "tvdb_status" if use_tvdb else "tmdb_status"
        
        if enable_backdrop:
            # Check if user provided a custom name
            if "name" not in backdrop_config:
                backdrop_config["name"] = "backdrop"
            
            # Create filters dict with status filter first, then additional filters
            backdrop_filters = {status_filter: "ended"}
            backdrop_filters.update(backdrop_additional_filters)
            
            overlays_dict[backdrop_block_name] = {
                "plex_all": True,
                "filters": backdrop_filters,
                "overlay": backdrop_config
            }
        
        # -- Text Block --
        text_config = deepcopy(config_sections.get("text", {}))
        enable_text = text_config.pop("enable", True)
        
        # Extract additional filters from text config
        text_additional_filters = text_config.pop("filters", {})
        
        if enable_text:
            use_text = text_config.pop("use_text", "Ended")
            text_config.pop("date_format", None)  # Remove if present
            text_config.pop("capitalize_dates", None)  # Remove if present
            
            # Check if user provided a custom name
            if "name" not in text_config:
                text_config["name"] = f"text({use_text})"
            
            # Create filters dict with status filter first, then additional filters
            text_filters = {status_filter: "ended"}
            text_filters.update(text_additional_filters)
            
            overlays_dict["ended_show"] = {
                "plex_all": True,
                "filters": text_filters,
                "overlay": text_config
            }
        
        final_output = {"overlays": overlays_dict}
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            yaml.dump(final_output, f, sort_keys=False)
        if config:
            debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
        
    except Exception as e:
        print(f"{RED}Error writing file {output_file_path}: {str(e)}{RESET}")

def create_canceled_show_collection_yaml(output_file, config, use_tvdb=False):
    """Create collection YAML for canceled shows using Plex filters instead of Sonarr data"""
    # Ensure the directory exists
    output_dir = "/config/kometa/tssk/" if IS_DOCKER else "kometa/"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"{RED}Error creating directory {output_dir}: {str(e)}{RESET}")
        return
    
    output_file_path = os.path.join(output_dir, output_file)

    try:
        # Add representer for OrderedDict
        def represent_ordereddict(dumper, data):
            return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())
        
        yaml.add_representer(OrderedDict, represent_ordereddict, Dumper=yaml.SafeDumper)

        class QuotedString(str):
            pass

        def quoted_str_presenter(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

        yaml.add_representer(QuotedString, quoted_str_presenter, Dumper=yaml.SafeDumper)

        # Get collection configuration
        collection_config = deepcopy(config.get("collection_canceled", {}))
        collection_name = collection_config.pop("collection_name", "Canceled Shows")
        
        # Extract user-provided summary and sort_title
        user_summary = collection_config.pop("summary", None)
        user_sort_title = collection_config.pop("sort_title", None)
        
        # Use user summary if provided, otherwise use default
        summary = user_summary if user_summary else "Shows that have been canceled"
        
        # Extract additional filters from config
        additional_filters = collection_config.pop("filters", {})

        # Create the collection data structure as a regular dict
        collection_data = {}
        collection_data["summary"] = summary
        
        # Add sort_title if user provided it
        if user_sort_title:
            collection_data["sort_title"] = QuotedString(user_sort_title)
        
        # Add all remaining parameters from the collection config
        for key, value in collection_config.items():
            collection_data[key] = value
           
        # Add plex_all and filters instead of tvdb_show
        collection_data["plex_all"] = True
        status_filter = "tvdb_status" if use_tvdb else "tmdb_status"
        
        # Create filters dict with status filter first, then additional filters
        filters_dict = {status_filter: "canceled"}
        filters_dict.update(additional_filters)
        collection_data["filters"] = filters_dict

        # Create the final structure with ordered keys
        ordered_collection = OrderedDict()
        
        # Add summary first
        ordered_collection["summary"] = collection_data["summary"]
        
        # Add sort_title second (if it exists)
        if "sort_title" in collection_data:
            ordered_collection["sort_title"] = collection_data["sort_title"]
        
        # Add all other keys except summary, sort_title, plex_all, and filters
        for key, value in collection_data.items():
            if key not in ["summary", "sort_title", "plex_all", "filters"]:
                ordered_collection[key] = value
        
        # Add plex_all and filters at the end
        ordered_collection["plex_all"] = collection_data["plex_all"]
        ordered_collection["filters"] = collection_data["filters"]

        data = {
            "collections": {
                collection_name: ordered_collection
            }
        }

        with open(output_file_path, "w", encoding="utf-8") as f:
            # Use SafeDumper so our custom representer is used
            yaml.dump(data, f, Dumper=yaml.SafeDumper, sort_keys=False)
        debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
        
    except Exception as e:
        print(f"{RED}Error writing file {output_file_path}: {str(e)}{RESET}")

def create_canceled_show_overlay_yaml(output_file, config_sections, use_tvdb=False, config=None, backdrop_block_name="backdrop_canceled"):
    """Create overlay YAML for canceled shows using Plex filters"""  
    # Ensure the directory exists
    output_dir = "/config/kometa/tssk/" if IS_DOCKER else "kometa/"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"{RED}Error creating directory {output_dir}: {str(e)}{RESET}")
        return
    
    output_file_path = os.path.join(output_dir, output_file)
    
    try:
        overlays_dict = {}
        
        # -- Backdrop Block --
        backdrop_config = deepcopy(config_sections.get("backdrop", {}))
        enable_backdrop = backdrop_config.pop("enable", True)
        
        # Extract additional filters from backdrop config
        backdrop_additional_filters = backdrop_config.pop("filters", {})
        
        status_filter = "tvdb_status" if use_tvdb else "tmdb_status"
        
        if enable_backdrop:
            # Check if user provided a custom name
            if "name" not in backdrop_config:
                backdrop_config["name"] = "backdrop"
            
            # Create filters dict with status filter first, then additional filters
            backdrop_filters = {status_filter: "canceled"}
            backdrop_filters.update(backdrop_additional_filters)
            
            overlays_dict[backdrop_block_name] = {
                "plex_all": True,
                "filters": backdrop_filters,
                "overlay": backdrop_config
            }
        
        # -- Text Block --
        text_config = deepcopy(config_sections.get("text", {}))
        enable_text = text_config.pop("enable", True)
        
        # Extract additional filters from text config
        text_additional_filters = text_config.pop("filters", {})
        
        if enable_text:
            use_text = text_config.pop("use_text", "Canceled")
            text_config.pop("date_format", None)  # Remove if present
            text_config.pop("capitalize_dates", None)  # Remove if present
            
            # Check if user provided a custom name
            if "name" not in text_config:
                text_config["name"] = f"text({use_text})"
            
            # Create filters dict with status filter first, then additional filters
            text_filters = {status_filter: "canceled"}
            text_filters.update(text_additional_filters)
            
            overlays_dict["canceled_show"] = {
                "plex_all": True,
                "filters": text_filters,
                "overlay": text_config
            }
        
        final_output = {"overlays": overlays_dict}
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            yaml.dump(final_output, f, sort_keys=False)
        if config:
            debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
        
    except Exception as e:
        print(f"{RED}Error writing file {output_file_path}: {str(e)}{RESET}")

def sanitize_show_title(title):
    """Remove special characters from show title"""
    # Remove special characters: :,;.'"
    special_chars = ':,;.\'"'
    for char in special_chars:
        title = title.replace(char, '')
    return title.strip()

def create_metadata_yaml(output_file, shows, config, sonarr_url, api_key, all_series, sonarr_timeout=90):
    """Create metadata YAML file with sort_title based on air date and show name"""
    output_dir = "/config/kometa/tssk/" if IS_DOCKER else "kometa/"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"{RED}Error creating directory {output_dir}: {str(e)}{RESET}")
        return
    
    output_file_path = os.path.join(output_dir, output_file)

    try:
        # Read existing metadata file to track previously modified shows
        previously_modified_tvdb_ids = set()
        try:
            with open(output_file_path, 'r', encoding='utf-8') as f:
                existing_data = yaml.safe_load(f)
                if existing_data and 'metadata' in existing_data:
                    # Only include shows that have sort_title starting with !yyyymmdd
                    for tvdb_id, metadata in existing_data['metadata'].items():
                        sort_title = metadata.get('sort_title', '')
                        # Check if sort_title starts with ! followed by 8 digits
                        if sort_title and sort_title.startswith('!') and len(sort_title) > 9:
                            date_part = sort_title[1:9]  # Extract the 8 characters after !
                            if date_part.isdigit():
                                previously_modified_tvdb_ids.add(tvdb_id)
        except FileNotFoundError:
            pass  # First run, no existing file
        except Exception as e:
            print(f"{ORANGE}Warning: Could not read existing metadata file: {str(e)}{RESET}")
        
        # Build metadata dictionary for current matches
        metadata_dict = {}
        current_tvdb_ids = set()
        
        for show in shows:
            tvdb_id = show.get('tvdbId')
            air_date = show.get('airDate')  # Format: YYYY-MM-DD
            title = show.get('title', '')
            
            if not tvdb_id or not air_date or not title:
                continue
            
            current_tvdb_ids.add(tvdb_id)
            
            # Convert date from YYYY-MM-DD to YYYYMMDD
            date_yyyymmdd = air_date.replace('-', '')
            
            # Sanitize show title
            clean_title = sanitize_show_title(title)
            
            # Create sort_title value with date prefix
            sort_title_value = f"!{date_yyyymmdd} {clean_title}"
            
            # Add to metadata dict
            metadata_dict[tvdb_id] = {
                'sort_title': sort_title_value
            }
        
        # Find shows that were previously modified but are no longer in current matches
        # These need to have their sort_title reverted to original title
        shows_to_revert = previously_modified_tvdb_ids - current_tvdb_ids
        
        if shows_to_revert:
            # Create a mapping of tvdb_id to series title from all_series
            tvdb_to_title = {series.get('tvdbId'): series.get('title', '') 
                           for series in all_series if series.get('tvdbId')}
            
            for tvdb_id in shows_to_revert:
                # Get the original title from Sonarr data
                original_title = tvdb_to_title.get(tvdb_id)
                if original_title:
                    # Sanitize the title to match what we did for the prefixed version
                    clean_title = sanitize_show_title(original_title)
                    metadata_dict[tvdb_id] = {
                        'sort_title': clean_title
                    }
        
        # Handle empty result
        if not metadata_dict:
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write("#No matching shows found\n")
            debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
            return
        
        # Sort by tvdb_id for consistent output
        sorted_metadata = OrderedDict(sorted(metadata_dict.items()))
        
        final_output = {"metadata": sorted_metadata}
        
        # Custom representer to ensure tvdb_id is written as integer without quotes
        def represent_int_key_dict(dumper, data):
            return dumper.represent_mapping('tag:yaml.org,2002:map', 
                                          ((int(k), v) for k, v in data.items()))
        
        yaml.add_representer(OrderedDict, represent_int_key_dict, Dumper=yaml.SafeDumper)
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            yaml.dump(final_output, f, Dumper=yaml.SafeDumper, sort_keys=False, default_flow_style=False)
        
        if shows_to_revert:
            print(f"{GREEN}Reverting sort_title for {len(shows_to_revert)} shows no longer in 'new season soon' category{RESET}")
        
        debug_print(f"{GREEN}Created: {output_file_path}{RESET}", config)
        
    except Exception as e:
        print(f"{RED}Error writing file {output_file_path}: {str(e)}{RESET}")

def main():
    start_time = datetime.now()
    print(f"{BLUE}{'*' * 40}\n{'*' * 11} TSSK {VERSION} {'*' * 12}\n{'*' * 40}{RESET}")
    
    # Verify output directory before doing anything else
    output_dir = ensure_output_directory()
    print(f"Docker mode: {IS_DOCKER}")
    print(f"Output directory: {output_dir}\n")
    
    check_for_updates()

    config = load_config('config/config.yml')
    
    try:
        # Process and validate Sonarr URL
        sonarr_timeout = int(config.get('sonarr_timeout', 90))
        sonarr_url = process_sonarr_url(config['sonarr_url'], config['sonarr_api_key'], sonarr_timeout)
        sonarr_api_key = config['sonarr_api_key']

        # Get ignore_finales_tags configuration
        ignore_finales_tags_config = config.get('ignore_finales_tags', '')
        ignore_finales_tags = []
        if ignore_finales_tags_config:
            ignore_finales_tags = [tag.strip() for tag in ignore_finales_tags_config.split(',') if tag.strip()]
        
        # Get use_tvdb configuration
        use_tvdb = config.get('use_tvdb', False)
        
        # Get category-specific future_days values, with fallback to main future_days
        future_days = config.get('future_days', 14)
        future_days_new_season = config.get('future_days_new_season', future_days)
        future_days_upcoming_episode = config.get('future_days_upcoming_episode', future_days)
        future_days_upcoming_finale = config.get('future_days_upcoming_finale', future_days)
        
        # Get recent days values
        recent_days_season_finale = config.get('recent_days_season_finale', 14)
        recent_days_final_episode = config.get('recent_days_final_episode', 14)
        recent_days_new_season_started = config.get('recent_days_new_season_started', 7)
        recent_days_new_show = config.get('recent_days_new_show', 7)
        
        utc_offset = float(config.get('utc_offset', 0))
        skip_unmonitored = str(config.get("skip_unmonitored", "false")).lower() == "true"
        
        # Get process flags for each category (default to True if not specified)
        process_new_shows = str(config.get('process_new_shows', 'true')).lower() == 'true'
        process_new_season_soon = str(config.get('process_new_season_soon', 'true')).lower() == 'true'
        process_new_season_started = str(config.get('process_new_season_started', 'true')).lower() == 'true'
        process_upcoming_episode = str(config.get('process_upcoming_episode', 'true')).lower() == 'true'
        process_upcoming_finale = str(config.get('process_upcoming_finale', 'true')).lower() == 'true'
        process_season_finale = str(config.get('process_season_finale', 'true')).lower() == 'true'
        process_final_episode = str(config.get('process_final_episode', 'true')).lower() == 'true'
        process_returning_shows = str(config.get('process_returning_shows', 'true')).lower() == 'true'
        process_ended_shows = str(config.get('process_ended_shows', 'true')).lower() == 'true'
        process_canceled_shows = str(config.get('process_canceled_shows', 'true')).lower() == 'true'

        # Print chosen values
        print(f"future_days_new_season: {future_days_new_season}")
        print(f"recent_days_new_season_started: {recent_days_new_season_started}")
        print(f"future_days_upcoming_episode: {future_days_upcoming_episode}")
        print(f"future_days_upcoming_finale: {future_days_upcoming_finale}")
        print(f"recent_days_season_finale: {recent_days_season_finale}")
        print(f"recent_days_final_episode: {recent_days_final_episode}")
        print(f"recent_days_new_show: {recent_days_new_show}")
        print(f"skip_unmonitored: {skip_unmonitored}")
        print(f"ignore_finales_tags: {ignore_finales_tags}\n")
        print(f"UTC offset: {utc_offset} hours\n")

        # Get series and tags from Sonarr in one call
        all_series, tag_mapping = get_sonarr_series_and_tags(sonarr_url, sonarr_api_key, sonarr_timeout)

        # Track all tvdbIds to exclude from other categories
        all_excluded_tvdb_ids = set()

        # ---- New Show ----
        if process_new_shows:
            create_new_show_overlay_yaml("TSSK_TV_NEW_SHOW_OVERLAYS.yml", 
                                       {"backdrop": get_config_section(config, "backdrop_new_show"),
                                        "text": get_config_section(config, "text_new_show")}, 
                                       recent_days_new_show, config, "backdrop_new_show")

            create_new_show_collection_yaml("TSSK_TV_NEW_SHOW_COLLECTION.yml", config, recent_days_new_show)
            print(f"\n'New shows' overlay and collection .ymls created for shows added within the past {GREEN}{recent_days_new_show}{RESET} days")

        # ---- New Season Soon ----
        if process_new_season_soon:
            matched_shows, skipped_shows = find_new_season_shows(
                sonarr_url, sonarr_api_key, all_series, tag_mapping, future_days_new_season, utc_offset, skip_unmonitored
            )
                                
            if matched_shows:
                print(f"\n{GREEN}Shows with a new season starting within {future_days_new_season} days:{RESET}")
                for show in matched_shows:
                    print(f"- {show['title']} (Season {show['seasonNumber']}) airs on {show['airDate']}")
            else:
                print(f"\n{RED}No shows with new seasons starting within {future_days_new_season} days.{RESET}")
            
            # Create YAMLs for new seasons
            create_overlay_yaml("TSSK_TV_NEW_SEASON_OVERLAYS.yml", matched_shows, 
                               {"backdrop": config.get("backdrop_new_season", config.get("backdrop", {})),
                                "text": config.get("text_new_season", config.get("text", {}))}, config, "backdrop_new_season")
            
            create_collection_yaml("TSSK_TV_NEW_SEASON_COLLECTION.yml", matched_shows, config)
            
            create_metadata_yaml("TSSK_TV_NEW_SEASON_METADATA.yml", matched_shows, config, sonarr_url, sonarr_api_key, all_series, sonarr_timeout)

        # ---- New Season Started ----
        if process_new_season_started:
            new_season_started_shows = find_new_season_started(
                sonarr_url, sonarr_api_key, all_series, recent_days_new_season_started, utc_offset, skip_unmonitored
            )
            
            # Add to excluded IDs
            for show in new_season_started_shows:
                if show.get('tvdbId'):
                    all_excluded_tvdb_ids.add(show['tvdbId'])
            
            if new_season_started_shows:
                print(f"\n{GREEN}Shows with a new season that started within the past {recent_days_new_season_started} days:{RESET}")
                for show in new_season_started_shows:
                    print(f"- {show['title']} (Season {show['seasonNumber']}) started on {show['airDate']}")
            
            create_overlay_yaml("TSSK_TV_NEW_SEASON_STARTED_OVERLAYS.yml", new_season_started_shows, 
                               {"backdrop": config.get("backdrop_new_season_started", {}),
                                "text": config.get("text_new_season_started", {})}, config, "backdrop_new_season_started")
            
            create_collection_yaml("TSSK_TV_NEW_SEASON_STARTED_COLLECTION.yml", new_season_started_shows, config)

        # ---- Upcoming Regular Episodes ----
        if process_upcoming_episode:
            upcoming_eps, skipped_eps = find_upcoming_regular_episodes(
                sonarr_url, sonarr_api_key, all_series, future_days_upcoming_episode, utc_offset, skip_unmonitored, ignore_finales_tags, tag_mapping
            )
            
            # Filter out shows that are in the season finale or final episode categories
            upcoming_eps = [show for show in upcoming_eps if show.get('tvdbId') not in all_excluded_tvdb_ids]
                    
            if upcoming_eps:
                print(f"\n{GREEN}Shows with upcoming non-finale episodes within {future_days_upcoming_episode} days:{RESET}")
                for show in upcoming_eps:
                    print(f"- {show['title']} (S{show['seasonNumber']}E{show['episodeNumber']}) airs on {show['airDate']}")
            
            create_overlay_yaml("TSSK_TV_UPCOMING_EPISODE_OVERLAYS.yml", upcoming_eps, 
                               {"backdrop": config.get("backdrop_upcoming_episode", {}),
                                "text": config.get("text_upcoming_episode", {})}, config, "backdrop_upcoming_episode")
            
            create_collection_yaml("TSSK_TV_UPCOMING_EPISODE_COLLECTION.yml", upcoming_eps, config)

        # ---- Upcoming Finale Episodes ----
        if process_upcoming_finale:
            finale_eps, skipped_finales = find_upcoming_finales(
                sonarr_url, sonarr_api_key, all_series, future_days_upcoming_finale, utc_offset, skip_unmonitored, ignore_finales_tags, tag_mapping
            )
                    
            if finale_eps:
                print(f"\n{GREEN}Shows with upcoming season finales within {future_days_upcoming_finale} days:{RESET}")
                for show in finale_eps:
                    print(f"- {show['title']} (S{show['seasonNumber']}E{show['episodeNumber']}) airs on {show['airDate']}")
            
            create_overlay_yaml("TSSK_TV_UPCOMING_FINALE_OVERLAYS.yml", finale_eps, 
                               {"backdrop": config.get("backdrop_upcoming_finale", {}),
                                "text": config.get("text_upcoming_finale", {})}, config, "backdrop_upcoming_finale")
            
            create_collection_yaml("TSSK_TV_UPCOMING_FINALE_COLLECTION.yml", finale_eps, config)
        
        # ---- Recent Season Finales ----
        if process_season_finale:
            season_finale_shows = find_recent_season_finales(
                sonarr_url, sonarr_api_key, all_series, recent_days_season_finale, utc_offset, skip_unmonitored, ignore_finales_tags, tag_mapping
            )
            
            # Add to excluded IDs
            for show in season_finale_shows:
                if show.get('tvdbId'):
                    all_excluded_tvdb_ids.add(show['tvdbId'])
            
            if season_finale_shows:
                print(f"\n{GREEN}Shows with a season finale that aired within the past {recent_days_season_finale} days:{RESET}")
                for show in season_finale_shows:
                    print(f"- {show['title']} (S{show['seasonNumber']}E{show['episodeNumber']}) aired on {show['airDate']}")
            
            create_overlay_yaml("TSSK_TV_SEASON_FINALE_OVERLAYS.yml", season_finale_shows, 
                               {"backdrop": config.get("backdrop_season_finale", {}),
                                "text": config.get("text_season_finale", {})}, config, "backdrop_season_finale")
            
            create_collection_yaml("TSSK_TV_SEASON_FINALE_COLLECTION.yml", season_finale_shows, config)
        
        # ---- Recent Final Episodes ----
        if process_final_episode:
            final_episode_shows = find_recent_final_episodes(
                sonarr_url, sonarr_api_key, all_series, recent_days_final_episode, utc_offset, skip_unmonitored, ignore_finales_tags, tag_mapping
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
                                "text": config.get("text_final_episode", {})}, config, "backdrop_final_episode")
            
            create_collection_yaml("TSSK_TV_FINAL_EPISODE_COLLECTION.yml", final_episode_shows, config)

        # ---- Returning Shows ----
        if process_returning_shows:
            create_returning_show_overlay_yaml("TSSK_TV_RETURNING_OVERLAYS.yml", 
                                              {"backdrop": config.get("backdrop_returning", {}),
                                               "text": config.get("text_returning", {})}, use_tvdb, config, "backdrop_returning")
            
            create_returning_show_collection_yaml("TSSK_TV_RETURNING_COLLECTION.yml", config, use_tvdb)
            print(f"\n'Returning shows' overlay and collection .ymls created using {'TVDB' if use_tvdb else 'TMDB'} status filtering")
        
        # ---- Ended Shows ----
        if process_ended_shows:
            create_ended_show_overlay_yaml("TSSK_TV_ENDED_OVERLAYS.yml", 
                                         {"backdrop": config.get("backdrop_ended", {}),
                                          "text": config.get("text_ended", {})}, use_tvdb, config, "backdrop_ended")
            
            create_ended_show_collection_yaml("TSSK_TV_ENDED_COLLECTION.yml", config, use_tvdb)
            print(f"'Ended shows' overlay and collection .ymls created using {'TVDB' if use_tvdb else 'TMDB'} status filtering")
        
        # ---- Canceled Shows ----
        if process_canceled_shows:
            create_canceled_show_overlay_yaml("TSSK_TV_CANCELED_OVERLAYS.yml", 
                                             {"backdrop": config.get("backdrop_canceled", {}),
                                              "text": config.get("text_canceled", {})}, use_tvdb, config, "backdrop_canceled")
            
            create_canceled_show_collection_yaml("TSSK_TV_CANCELED_COLLECTION.yml", config, use_tvdb)
            print(f"'Canceled shows' overlay and collection .ymls created using {'TVDB' if use_tvdb else 'TMDB'} status filtering")

        # ---- skipped Shows ----
        if process_new_season_soon and skipped_shows:
            print(f"\n{ORANGE}Skipped shows (unmonitored or new show):{RESET}")
            for show in skipped_shows:
                print(f"- {show['title']} (Season {show['seasonNumber']}) airs on {show['airDate']}")
        
        # Print processing summary
        print(f"\n{BLUE}{'=' * 40}")
        print("Processing Summary:")
        print(f"{'=' * 40}{RESET}")
        categories = [
            ("New Shows", process_new_shows),
            ("New Season Soon", process_new_season_soon),
            ("New Season Started", process_new_season_started),
            ("Upcoming Episode", process_upcoming_episode),
            ("Upcoming Finale", process_upcoming_finale),
            ("Season Finale", process_season_finale),
            ("Final Episode", process_final_episode),
            ("Returning Shows", process_returning_shows),
            ("Ended Shows", process_ended_shows),
            ("Canceled Shows", process_canceled_shows)
        ]

        for category, enabled in categories:
            status = f"{GREEN}✓ Processed{RESET}" if enabled else f"{ORANGE}✗ Skipped{RESET}"
            print(f"{category:.<30} {status}")
        
        print(f"\nRun completed")

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