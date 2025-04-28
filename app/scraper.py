import time
import requests
from bs4 import BeautifulSoup, Tag # Import Tag for type checking
import re
from datetime import datetime, timedelta
from app.models import Fighter, Event, Fight, FightRoundStats
from app import db
import traceback

def scrape_event(event_url, db_session, scrape_queue, processed_urls):
    """Scrape event details and all fights from an event page."""
    if event_url in processed_urls:
        print(f"Skipping already processed event: {event_url}")
        return

    print(f"Scraping event: {event_url}")

    try:
        response = requests.get(event_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Optional: Save HTML for offline debugging ---
        # with open("event_page.html", "w", encoding="utf-8") as f:
        #     f.write(soup.prettify())
        # print("Saved event_page.html for debugging.")
        # -------------------------------------------------

        # Extract event details with checks
        event_name_elem = soup.select_one('h2.b-content__title span.b-content__title-highlight')
        if event_name_elem:
            event_name = event_name_elem.text.strip()
            print(f"Found event name: {event_name}")
        else:
            # Fallback if the specific span isn't found
            event_name_elem = soup.select_one('h2.b-content__title')
            if event_name_elem:
                 event_name = event_name_elem.text.strip()
                 print(f"Found event name (fallback selector): {event_name}")
            else:
                print(f"ERROR: Could not find event name element for URL: {event_url}")
                processed_urls.add(event_url)
                return

        # Extract Date and Location more robustly
        event_details_list = soup.select('ul.b-list__box-list li.b-list__box-list-item')
        event_date_str = None
        location = None
        print(f"Found {len(event_details_list)} detail list items. Looking for Date and Location...")
        for item in event_details_list:
            # Get all text within the list item, separated by spaces
            text_content = item.get_text(separator=" ", strip=True)
            if text_content.startswith("Date:"):
                event_date_str = text_content.replace("Date:", "").strip()
                print(f"Found date string: '{event_date_str}'")
            elif text_content.startswith("Location:"):
                location = text_content.replace("Location:", "").strip()
                print(f"Found location: '{location}'")

        if not event_date_str:
            print(f"ERROR: Could not find event date string for URL: {event_url}")
            processed_urls.add(event_url)
            return
        if not location:
            # Decide if location is critical. If not, you might want to continue.
            print(f"WARNING: Could not find location string for URL: {event_url}")

        # Parse date
        event_date = None
        try:
            # Handle potential extra text around the date if necessary
            clean_date_str = event_date_str.split(u'\\n')[0].strip()
            event_date = datetime.strptime(clean_date_str, '%B %d, %Y').date()
            print(f"Parsed event date: {event_date}")
        except ValueError as date_err:
            print(f"ERROR: Could not parse date string '{event_date_str}' (cleaned: '{clean_date_str}'): {date_err}")
            processed_urls.add(event_url)
            return

        # Find or create event (Use name AND date to make it more unique)
        event = db_session.query(Event).filter_by(event_name=event_name, event_date=event_date).first()
        if not event:
            event = Event(
                event_name=event_name,
                event_date=event_date,
                location=location
            )
            db_session.add(event)
            print(f"Creating new event: {event_name} on {event_date}")
            try:
                db_session.commit()
                print(f"Committed new event, ID: {event.id}")
            except Exception as commit_err:
                print(f"ERROR: Failed to commit new event: {commit_err}")
                db_session.rollback()
                processed_urls.add(event_url)
                return
        else:
            print(f"Found existing event: ID {event.id} - {event.event_name}")
            updated = False
            if location and event.location != location:
                print(f"Updating event {event.id} location to: {location}")
                event.location = location
                updated = True
            if updated:
                try:
                    db_session.commit()
                except Exception as commit_err:
                     print(f"ERROR: Failed to commit event update: {commit_err}")
                     db_session.rollback()

        # --- Fight Extraction ---
        fight_rows = soup.select('tr.b-fight-details__table-row[data-link]')
        print(f"Found {len(fight_rows)} fight rows using selector 'tr.b-fight-details__table-row[data-link]'.")

        if not fight_rows:
             print("WARNING: No fight rows found with data-link selector. Trying fallback 'tbody.b-fight-details__table-body tr'.")
             fight_rows = soup.select('tbody.b-fight-details__table-body tr')
             fight_rows = [row for row in fight_rows if row.select_one('td.b-fight-details__table-col')]
             print(f"Found {len(fight_rows)} rows using fallback selector (after filtering).")

        for i, row in enumerate(fight_rows):
            print(f"\n--- Processing Fight Row {i+1} ---")
            fight_details_url = row.get('data-link')
            if not fight_details_url:
                 link_tag = row.select_one('td a')
                 if link_tag and 'fight-details' in link_tag.get('href', ''):
                     fight_details_url = link_tag['href']
                     print(f"Found fight details URL in 'a' tag: {fight_details_url}")
                 else:
                    print("Skipping row: Could not find data-link attribute or fight details link.")
                    continue

            fighter_links = row.select('td:nth-of-type(2) p a')
            if len(fighter_links) < 2:
                print(f"Skipping fight row: Found {len(fighter_links)} fighter links in the second column, expected 2.")
                continue

            fighter1_url = fighter_links[0]['href']
            fighter2_url = fighter_links[1]['href']
            fighter1_name_text = fighter_links[0].text.strip()
            fighter2_name_text = fighter_links[1].text.strip()
            print(f"Processing fight: {fighter1_name_text} vs {fighter2_name_text}")
            print(f"  Fighter 1 URL: {fighter1_url}")
            print(f"  Fighter 2 URL: {fighter2_url}")
            print(f"  Fight Details URL: {fight_details_url}")

            columns = row.select('td.b-fight-details__table-col')
            def get_col_text(idx):
                if len(columns) > idx and columns[idx]:
                    return columns[idx].text.strip()
                return None

            weight_class = get_col_text(6)
            method = get_col_text(7)
            end_round_str = get_col_text(8)
            end_time = get_col_text(9)
            scheduled_rounds_str = get_col_text(11)

            print(f"  Weight: {weight_class}, Method: {method}, Round: {end_round_str}, Time: {end_time}, Scheduled: {scheduled_rounds_str}")

            end_round = int(end_round_str) if end_round_str and end_round_str.isdigit() else None
            scheduled_rounds = int(scheduled_rounds_str) if scheduled_rounds_str and scheduled_rounds_str.isdigit() else 3

            fighter1_id = scrape_fighter(fighter1_url, db_session, scrape_queue, processed_urls)
            time.sleep(1.5)
            fighter2_id = scrape_fighter(fighter2_url, db_session, scrape_queue, processed_urls)
            time.sleep(1.5)

            if not fighter1_id or not fighter2_id:
                print(f"ERROR: Could not get IDs for both fighters in fight: {fighter1_name_text} vs {fighter2_name_text}. Skipping fight detail scraping for this fight.")
                continue

            existing_fight = db_session.query(Fight).filter(
                Fight.event_id == event.id,
                ( (Fight.fighter1_id == fighter1_id) & (Fight.fighter2_id == fighter2_id) ) |
                ( (Fight.fighter1_id == fighter2_id) & (Fight.fighter2_id == fighter1_id) )
            ).first()

            fight_record_to_update = None
            if not existing_fight:
                print(f"Creating new fight record for Event ID {event.id}: Fighter {fighter1_id} vs Fighter {fighter2_id}")
                fight = Fight(
                    event_id=event.id,
                    fighter1_id=fighter1_id,
                    fighter2_id=fighter2_id,
                    weight_class=weight_class,
                    method=method,
                    end_round=end_round,
                    end_time=end_time,
                    scheduled_rounds=scheduled_rounds
                )
                db_session.add(fight)
                try:
                    db_session.commit()
                    print(f"Committed new fight, ID: {fight.id}")
                    fight_record_to_update = fight
                except Exception as commit_err:
                    print(f"ERROR: Failed to commit new fight record: {commit_err}")
                    db_session.rollback()
                    continue
            else:
                print(f"Found existing fight record: ID {existing_fight.id}")
                updated = False
                if not existing_fight.weight_class and weight_class:
                    existing_fight.weight_class = weight_class; updated = True
                if not existing_fight.method and method:
                     existing_fight.method = method; updated = True
                if updated:
                    print("Updating existing fight record with basic info.")
                    try:
                        db_session.commit()
                    except Exception as commit_err:
                        print(f"ERROR: Failed to commit update to existing fight {existing_fight.id}: {commit_err}")
                        db_session.rollback()
                fight_record_to_update = existing_fight

            if fight_record_to_update:
                print(f"--> Scraper: Calling scrape_fight_details for Fight ID {fight_record_to_update.id}")
                scrape_fight_details(fight_details_url, fight_record_to_update, db_session, processed_urls)
                time.sleep(1.5)
            else:
                 print(f"Skipping scrape_fight_details because fight record could not be obtained/created.")

        processed_urls.add(event_url)
        print(f"--- Finished processing event: {event_url} ---")

    except requests.exceptions.RequestException as req_err:
        print(f"HTTP Error scraping event {event_url}: {req_err}")
    except Exception as e:
        print(f"Unexpected Error scraping event {event_url}: {type(e).__name__} - {e}")
        traceback.print_exc()
        db_session.rollback()
        processed_urls.add(event_url)


def scrape_fighter(fighter_url, db_session, scrape_queue, processed_urls):
    """Scrape fighter details and return fighter ID."""
    print(f"Processing fighter: {fighter_url}")
    
    # Skip if already processed - but first try to find the fighter in the database
    if fighter_url in processed_urls:
        # Extract fighter name from URL for preliminary check
        fighter_id_part = fighter_url.split('/')[-1]
        
        # Common URL format: /fighter/firstname-lastname-nickpart
        name_parts = fighter_id_part.split('-')
        if len(name_parts) >= 2:
            # Make a best-effort attempt to get first and last name from URL
            first_name_guess = name_parts[0].capitalize()
            last_name_guess = name_parts[1].capitalize()
            
            # Try to find fighter by name before scraping
            existing_fighter = db_session.query(Fighter).filter_by(
                first_name=first_name_guess, 
                last_name=last_name_guess
            ).first()
            
            if existing_fighter:
                print(f"Found existing fighter from URL parse: {existing_fighter.first_name} {existing_fighter.last_name} (ID: {existing_fighter.id})")
                return existing_fighter.id
            else:
                print(f"URL {fighter_url} already processed but fighter couldn't be identified by name in URL.")
                # Skip further processing since URL is already in processed_urls
                return None
        else:
            print(f"URL {fighter_url} already processed and couldn't parse name from URL.")
            return None
    
    print(f"Scraping fighter: {fighter_url}")

    try:
        response = requests.get(fighter_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract name - this is the minimum we need
        name_elem = soup.select_one('span.b-content__title-highlight')
        if not name_elem:
            print(f"ERROR: Could not find name element for fighter: {fighter_url}")
            processed_urls.add(fighter_url)
            return None
        
        name_text = name_elem.text.strip()
        print(f"Found fighter name: {name_text}")

        # Parse name into first and last name
        first_name = "Unknown"
        last_name = "Unknown"
        name_parts = name_text.split()
        if len(name_parts) >= 1:
            first_name = name_parts[0]
        if len(name_parts) >= 2:
            last_name = ' '.join(name_parts[1:])
            
        # Check if fighter already exists in database by name
        existing_fighter = db_session.query(Fighter).filter_by(
            first_name=first_name, 
            last_name=last_name
        ).first()
        
        if existing_fighter:
            print(f"Found existing fighter: {first_name} {last_name} (ID: {existing_fighter.id})")
            # We still continue with scraping to update any new information
            fighter = existing_fighter
        else:
            # Will create a new fighter after scraping all details
            fighter = None
            
        # Extract nickname safely
        nickname_elem = soup.select_one('p.b-content__Nickname')
        nickname = nickname_elem.text.strip('" ') if nickname_elem else None
        print(f"Found nickname: {nickname}")

        # Extract basic stats first (height, weight, reach, stance, etc.)
        # Initialize variables to prevent UnboundLocalError
        height = None
        weight = None
        reach = None
        stance = None
        dob = None
        age = None

        # Extract basic stats first (height, weight, reach, stance, etc.)
        stats = {}
        
        # First, try to find the basic stats in the small-width info box
        basic_stats_container = soup.select_one('div.b-list__info-box_style_small-width')
        if basic_stats_container:
            print(f"Container HTML class: {basic_stats_container.get('class')}")
            
            # Debug the entire container HTML for troubleshooting
            container_html = str(basic_stats_container)
            print(f"Container HTML (first 100 chars): {container_html[:100]}...")
            
            # Try multiple selectors to find the list items
            stat_items = basic_stats_container.select('li.b-list__box-list-item')
            if not stat_items:
                stat_items = basic_stats_container.select('li')
                print(f"Fallback to generic li selector, found {len(stat_items)} items")
            
            print(f"Found {len(stat_items)} basic stat list items in container")
            
            for idx, item in enumerate(stat_items):
                print(f"Processing item #{idx+1}: {item.get_text(strip=True)[:30]}...")
                
                # Try different selectors for the label element
                label_elem = None
                for selector in ['i.b-list__box-item-title', '.b-list__box-item-title', 'i.b-list__box-item-title_type_width']:
                    label_elem = item.select_one(selector)
                    if label_elem:
                        print(f"  Found label using selector: {selector}")
                        break
                
                if label_elem:
                    label = label_elem.text.strip(':').strip()
                    # Get the text after the label
                    value_text = item.get_text(strip=True).replace(label_elem.get_text(strip=True), '', 1).strip()
                    stats[label] = value_text
                else:
                    print(f"  No label element found for item: {item}")
        else:
            # Fallback to searching through all list items
            print("Basic stats container not found, trying generic list items")
            stat_items = soup.select('li.b-list__box-list-item')
            print(f"Found {len(stat_items)} potential basic stat list items")
            
            for item in stat_items:
                label_elem = item.select_one('.b-list__box-item-title')
                if label_elem and ('Height' in label_elem.text or 'Weight' in label_elem.text or 
                                  'Reach' in label_elem.text or 'STANCE' in label_elem.text or 
                                  'DOB' in label_elem.text):
                    label = label_elem.text.strip(':').strip()
                    value_text = item.get_text(strip=True).replace(label_elem.get_text(strip=True), '', 1).strip()
                    stats[label] = value_text
        
        print(f"Extracted basic stats: {stats}")
        
        # Normalize keys to handle possible case differences and remove colons
        normalized_stats = {}
        for key, value in stats.items():
            clean_key = key.strip(':').strip().upper()
            if clean_key == 'HEIGHT':
                normalized_stats['Height'] = value
            elif clean_key == 'WEIGHT':
                normalized_stats['Weight'] = value
            elif clean_key == 'REACH':
                normalized_stats['Reach'] = value
            elif clean_key == 'STANCE':
                normalized_stats['STANCE'] = value
            elif clean_key == 'DOB':
                 normalized_stats['DOB'] = value
            # Keep other potential stats if needed, or ignore
            # else:
            #     normalized_stats[key] = value # Keep original if not matched

        stats = normalized_stats # Replace original stats dict with normalized one
        print(f"Stats after normalization: {stats}")

        # Extract career stats safely
        career_stats = {}
        print("Attempting to extract career stats...")
        
        # Find all lowercase title elements and check their text content
        print("Attempting targeted stat extraction...")
        
        # Get all stats elements with the lowercase class
        stat_elems = soup.select('i.b-list__box-item-title_font_lowercase')
        print(f"Found {len(stat_elems)} potential stat elements with lowercase class")
        
        # Map of stat labels to their corresponding model field keys
        stat_mapping = {
            'SLpM': 'SLpM',
            'Str. Acc.': 'Str. Acc.',
            'SApM': 'SApM',
            'Str. Def': 'Str. Def',
            'TD Avg.': 'TD Avg.',
            'TD Acc.': 'TD Acc.',
            'TD Def.': 'TD Def.',
            'Sub. Avg.': 'Sub. Avg.'
        }
        
        # Process each stat element
        for elem in stat_elems:
            raw_label = elem.get_text(strip=True)
            clean_label = raw_label.strip(':')
            
            # Check if this is a stat we're interested in
            for target_label, target_key in stat_mapping.items():
                if clean_label == target_label:
                    # Found a relevant stat, get its value
                    parent_li = elem.find_parent('li')
                    if parent_li:
                        value_text = parent_li.get_text(strip=True).replace(raw_label, '', 1).strip()
                        
                        try:
                            # Parse percentage values
                            if '%' in value_text:
                                parsed_value = float(value_text.strip('%')) / 100.0
                                career_stats[target_key] = parsed_value
                            else:
                                parsed_value = float(value_text)
                                career_stats[target_key] = parsed_value
                        except ValueError:
                            print(f"  Could not parse {target_key}: {value_text}")
                    break
        
        # Fallback: If we couldn't find some stats, try looking through all list items
        if len(career_stats) < len(stat_mapping):
            print("Some stats missing, trying fallback extraction...")
            
            # Get all list items that might contain stats
            all_list_items = soup.select('li.b-list__box-list-item')
            for item in all_list_items:
                label_elem = item.select_one('i.b-list__box-item-title')
                if label_elem:
                    raw_label = label_elem.get_text(strip=True)
                    clean_label = raw_label.strip(':')
                    
                    # Check if this is a stat we're interested in and don't already have
                    for target_label, target_key in stat_mapping.items():
                        if clean_label == target_label and target_key not in career_stats:
                            value_text = item.get_text(strip=True).replace(raw_label, '', 1).strip()
                            print(f"Fallback found: {clean_label} = {value_text}")
                            
                            try:
                                # Parse percentage values
                                if '%' in value_text:
                                    parsed_value = float(value_text.strip('%')) / 100.0
                                    career_stats[target_key] = parsed_value
                                    print(f"  Fallback parsed: {target_key} = {parsed_value}")
                                else:
                                    parsed_value = float(value_text)
                                    career_stats[target_key] = parsed_value
                                    print(f"  Fallback parsed: {target_key} = {parsed_value}")
                            except ValueError:
                                print(f"  Could not parse fallback {target_key}: {value_text}")
                            break

        print(f"Extracted career stats: {career_stats}")

        # Extract record safely
        record_text = ""
        record_elem = soup.select_one('span.b-content__title-record')
        if record_elem:
            record_text = record_elem.text.strip()
        
        wins, losses, draws, nc = 0, 0, 0, 0
        record_match = re.search(r'Record: (\d+)-(\d+)-(\d+)(?:\s+\((\d+) NC\))?', record_text)
        if record_match:
            wins = int(record_match.group(1))
            losses = int(record_match.group(2))
            draws = int(record_match.group(3))
            nc = int(record_match.group(4)) if record_match.group(4) else 0

        # Parse height safely - Use normalized 'stats' dictionary
        height_str = stats.get('Height')
        if height_str:
            try:
                if "'" in height_str and '"' in height_str:
                    # Format: 5' 11"
                    feet, inches = height_str.split("'")
                    inches = inches.strip('" ')
                    height = int(feet.strip()) * 12 + int(inches)
                elif "cm" in height_str:
                    # Format: 180 cm
                    cm_value = float(height_str.replace("cm", "").strip())
                    height = round(cm_value / 2.54)  # Convert cm to inches
                elif height_str.isdigit():
                    # Just a number, assume inches
                    height = int(height_str)
            except (ValueError, TypeError) as e:
                print(f"Could not parse height '{height_str}': {e}")

        # Parse weight safely - Use normalized 'stats' dictionary
        weight_str = stats.get('Weight')
        if weight_str:
            try:
                if 'lbs.' in weight_str or 'lbs' in weight_str:
                    # Format: 145 lbs.
                    weight_parts = weight_str.split()
                    weight = float(weight_parts[0])
                elif 'kg' in weight_str:
                    # Format: 65.8 kg
                    kg_value = float(weight_str.replace("kg", "").strip())
                    weight = round(kg_value * 2.20462, 1)  # Convert kg to lbs
                elif weight_str.replace('.', '', 1).isdigit():
                    # Just a number, assume lbs
                    weight = float(weight_str)
            except (ValueError, TypeError) as e:
                print(f"Could not parse weight '{weight_str}': {e}")

        # Parse reach safely - Use normalized 'stats' dictionary
        reach_str = stats.get('Reach')
        if reach_str:
            try:
                if '"' in reach_str:
                    # Format: 72"
                    reach = float(reach_str.strip('" '))
                elif "cm" in reach_str:
                    # Format: 183 cm
                    cm_value = float(reach_str.replace("cm", "").strip())
                    reach = round(cm_value / 2.54, 1)  # Convert cm to inches
                elif reach_str.replace('.', '', 1).isdigit():
                    # Just a number, assume inches
                    reach = float(reach_str)
            except (ValueError, TypeError) as e:
                print(f"Could not parse reach '{reach_str}': {e}")

        # Get stance - Use normalized 'stats' dictionary
        stance = stats.get('STANCE')

        # Parse DOB safely - Use normalized 'stats' dictionary
        dob = None # Initialize dob and age
        age = None
        if 'DOB' in stats: # Now uses 'DOB' key
            dob_str = stats['DOB']
            try:
                dob = datetime.strptime(dob_str, '%b %d, %Y').date()
                today = datetime.now().date()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            except (ValueError, TypeError) as e:
                print(f"Could not parse DOB '{dob_str}': {e}")
        else:
             print("DOB key not found in normalized stats.")

        # Prepare career stats values for saving/updating
        # Use .get() with None default for safety
        slpm = career_stats.get('SLpM')
        str_acc = career_stats.get('Str. Acc.')
        sapm = career_stats.get('SApM')
        # Handle potential variations in Str. Def key from scraping
        str_def = career_stats.get('Str. Def') or career_stats.get('Str. Def.')
        td_avg = career_stats.get('TD Avg.')
        td_acc = career_stats.get('TD Acc.')
        td_def = career_stats.get('TD Def.')
        sub_avg = career_stats.get('Sub. Avg.')

        # Update existing fighter or create new one
        if fighter:  # We found an existing fighter by name earlier
            print(f"Updating existing fighter: ID {fighter.id}")
            # Update existing fighter data safely
            if nickname and fighter.nickname != nickname: fighter.nickname = nickname
            if height is not None and fighter.height != height: fighter.height = height
            if reach is not None and fighter.reach != reach: fighter.reach = reach
            if weight is not None and fighter.weight != weight: fighter.weight = weight
            if stance and fighter.stance != stance: fighter.stance = stance
            if dob and fighter.DOB != dob: fighter.DOB = dob
            if age is not None and fighter.age != age: fighter.age = age # Check age specifically
            if wins is not None and fighter.wins != wins: fighter.wins = wins
            if losses is not None and fighter.losses != losses: fighter.losses = losses
            if draws is not None and fighter.draws != draws: fighter.draws = draws
            if nc is not None and fighter.no_contests != nc: fighter.no_contests = nc

            # Update career stats if they are not None and different
            print(f"Updating career stats for fighter {fighter.id}:")
            if slpm is not None and fighter.SLpM != slpm: fighter.SLpM = slpm
            if str_acc is not None and fighter.Str_Acc != str_acc: fighter.Str_Acc = str_acc
            if sapm is not None and fighter.SApM != sapm: fighter.SApM = sapm
            if str_def is not None and fighter.Str_Def != str_def: fighter.Str_Def = str_def
            if td_avg is not None and fighter.Takedown_Avg != td_avg: fighter.Takedown_Avg = td_avg
            if td_acc is not None and fighter.Takedown_Acc != td_acc: fighter.Takedown_Acc = td_acc
            if td_def is not None and fighter.Takedown_Def != td_def: fighter.Takedown_Def = td_def
            if sub_avg is not None and fighter.Sub_Avg != sub_avg: fighter.Sub_Avg = sub_avg
        else:
            # Create a new fighter
            print(f"Creating new fighter: {first_name} {last_name}")
            fighter = Fighter(
                first_name=first_name,
                last_name=last_name,
                nickname=nickname,
                height=height,
                reach=reach,
                weight=weight,
                stance=stance,
                DOB=dob,
                age=age,
                # nationality=career_stats.get('Born'), # Commenting out - 'Born' wasn't in extracted stats
                wins=wins,
                losses=losses,
                draws=draws,
                no_contests=nc,
                # Assign career stats during creation
                SLpM=slpm,
                Str_Acc=str_acc,
                SApM=sapm,
                Str_Def=str_def,
                Takedown_Avg=td_avg,
                Takedown_Acc=td_acc,
                Takedown_Def=td_def,
                Sub_Avg=sub_avg
            )
            db_session.add(fighter)

        try:
            db_session.commit()
            fighter_id = fighter.id # Make sure fighter_id is assigned AFTER potential commit error
            print(f"Successfully saved/updated fighter {first_name} {last_name} with ID: {fighter_id}")
        except Exception as commit_err:
            print(f"ERROR: Failed to commit fighter {first_name} {last_name}: {commit_err}")
            db_session.rollback()
            processed_urls.add(fighter_url)
            return None

        # Find and add event/opponent links to queue
        try:
            fight_history_rows = soup.select('tbody.b-fight-details__table-body tr')
            for row in fight_history_rows:
                opponent_link = row.select_one('td:nth-of-type(2) a')
                event_link = row.select_one('td:nth-of-type(7) a')
                if opponent_link and opponent_link['href'] not in processed_urls:
                    # Use append instead of add for list
                    if opponent_link['href'] not in scrape_queue:
                        scrape_queue.append(opponent_link['href'])
                if event_link and event_link['href'] not in processed_urls:
                    # Use append instead of add for list
                    if event_link['href'] not in scrape_queue:
                        scrape_queue.append(event_link['href'])
        except Exception as e:
            print(f"Error processing fight history: {e}")
            # Non-critical error, continue

        processed_urls.add(fighter_url)
        return fighter_id

    except requests.exceptions.RequestException as req_err:
        print(f"HTTP Error scraping fighter {fighter_url}: {req_err}")
        processed_urls.add(fighter_url)
        return None
    except Exception as e:
        print(f"Unexpected Error scraping fighter {fighter_url}: {type(e).__name__} - {e}")
        traceback.print_exc()
        db_session.rollback()
        processed_urls.add(fighter_url)
        return None


def parse_full_name(full_name):
    """Parses a full name into first and last name."""
    parts = full_name.strip().split()
    if not parts:
        return None, None
    first_name = parts[0]
    last_name = " ".join(parts[1:]) if len(parts) > 1 else None
    # Handle potential missing last name for single-named fighters if necessary
    if not last_name:
        # Decide on handling: maybe last_name = first_name, or log a warning
        print(f"Warning: Only one name part found for '{full_name}'. Using '{first_name}' as first name.")
        # last_name = first_name # Option: Treat single name as first and last
    return first_name, last_name

def scrape_fight_details(fight_details_url, fight_record, db_session, processed_urls):
    """Scrape detailed fight statistics and round-by-round data."""
    if fight_details_url in processed_urls:
        print(f"Skipping already processed fight details: {fight_details_url}")
        return

    if not fight_record:
        print(f"ERROR: scrape_fight_details called with invalid fight_record (None) for URL: {fight_details_url}")
        processed_urls.add(fight_details_url) # Mark as processed to avoid loops
        return
    # Check if fight_record has an ID, needed for logging and relationships
    if fight_record.id is None:
        try:
            db_session.flush() # Try to get an ID if it's pending
        except Exception:
            print(f"ERROR: fight_record provided to scrape_fight_details has no ID yet. URL: {fight_details_url}")
            # Decide whether to proceed or return, maybe add it to processed_urls?
            processed_urls.add(fight_details_url)
            return # Fixed indentation

    print(f"Scraping fight details for Fight ID {fight_record.id}: {fight_details_url}")

    try:
        response = requests.get(fight_details_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Extract Fighter Names from Page ---
        fighter_name_elements = soup.select('a.b-fight-details__person-link')

        if len(fighter_name_elements) < 2:
            # Adding more debug info here: print the number found
            print(f"ERROR: Found only {len(fighter_name_elements)} fighter name links (expected 2) using selector 'a.b-fight-details__person-link' on page: {fight_details_url}. Skipping detail scrape.")
            # You might want to print soup.prettify() here or save to file if it keeps failing
            processed_urls.add(fight_details_url)
            return
        # Make sure we only take the first two, in case the selector matches other similar links elsewhere
        fighter_name_elements = fighter_name_elements[:2]


        page_fighter1_full_name = fighter_name_elements[0].text.strip()
        page_fighter2_full_name = fighter_name_elements[1].text.strip()
        print(f"Found names on page: '{page_fighter1_full_name}' vs '{page_fighter2_full_name}'")

        # --- Parse Names and Find Fighters in DB ---
        f1_first, f1_last = parse_full_name(page_fighter1_full_name)
        f2_first, f2_last = parse_full_name(page_fighter2_full_name)

        fighter1_db = None
        fighter2_db = None

        if f1_first and f1_last:
             fighter1_db = db_session.query(Fighter).filter_by(first_name=f1_first, last_name=f1_last).first()
        elif f1_first: # Fallback for single name match if needed
             fighter1_db = db_session.query(Fighter).filter_by(first_name=f1_first, last_name=None).first() # Or filter(first_name=f1_first) if last_name isn't nullable

        if f2_first and f2_last:
            fighter2_db = db_session.query(Fighter).filter_by(first_name=f2_first, last_name=f2_last).first()
        elif f2_first:
             fighter2_db = db_session.query(Fighter).filter_by(first_name=f2_first, last_name=None).first()

        # --- Assign or Verify Fighter IDs on fight_record ---
        fighter1_id_from_page = fighter1_db.id if fighter1_db else None
        fighter2_id_from_page = fighter2_db.id if fighter2_db else None

        print(f"DB Lookup Results: Fighter1 ID: {fighter1_id_from_page}, Fighter2 ID: {fighter2_id_from_page}")

        # Decision: Only populate if missing, or always overwrite?
        # Option 1: Populate if missing (safer if scrape_event is reliable)
        if fight_record.fighter1_id is None and fighter1_id_from_page:
            print(f"Assigning fighter1_id ({fighter1_id_from_page}) from page lookup.")
            fight_record.fighter1_id = fighter1_id_from_page
        elif fight_record.fighter1_id and fighter1_id_from_page and fight_record.fighter1_id != fighter1_id_from_page:
             print(f"WARNING: Fighter1 ID mismatch! Record has {fight_record.fighter1_id}, Page lookup found {fighter1_id_from_page} for name '{page_fighter1_full_name}'. Keeping original ID.")
             # Or decide to overwrite: fight_record.fighter1_id = fighter1_id_from_page

        if fight_record.fighter2_id is None and fighter2_id_from_page:
             print(f"Assigning fighter2_id ({fighter2_id_from_page}) from page lookup.")
             fight_record.fighter2_id = fighter2_id_from_page
        elif fight_record.fighter2_id and fighter2_id_from_page and fight_record.fighter2_id != fighter2_id_from_page:
            print(f"WARNING: Fighter2 ID mismatch! Record has {fight_record.fighter2_id}, Page lookup found {fighter2_id_from_page} for name '{page_fighter2_full_name}'. Keeping original ID.")
            # Or decide to overwrite: fight_record.fighter2_id = fighter2_id_from_page


        # --- Check if we have both fighter IDs before proceeding ---
        if not fight_record.fighter1_id or not fight_record.fighter2_id:
            print(f"ERROR: Could not determine both fighter IDs for Fight ID {fight_record.id}. Skipping detail scrape.")
            # Optionally try to scrape the fighters if not found? Less ideal here.
            # scrape_fighter(fighter_name_elements[0]['href'], ...) maybe?
            processed_urls.add(fight_details_url) # Mark as processed
            return

        # Now we are more confident fight_record.fighter1_id and fighter2_id are set.
        # Retrieve the fighter objects using the IDs on the fight_record
        fighter1 = db_session.query(Fighter).get(fight_record.fighter1_id)
        fighter2 = db_session.query(Fighter).get(fight_record.fighter2_id)

        if not fighter1 or not fighter2:
             print(f"ERROR: Could not retrieve Fighter objects from DB using IDs {fight_record.fighter1_id}, {fight_record.fighter2_id}. Skipping detail scrape.")
             processed_urls.add(fight_details_url)
             return


        # --- Optional: Save HTML for offline debugging ---
        # ...

        print("Extracting fight-level details...")
        details_section = soup.select_one('div.b-fight-details__content')
        referee = None
        finish_details_text = None
        scheduled_rounds = None # Initialize variable for scheduled rounds
        
        if details_section:
            # --- Referee Extraction (Revised) ---
            # Find the <i> tag containing the "Referee:" label
            referee_label_i = details_section.find('i', class_='b-fight-details__label', string=re.compile(r'\s*Referee:\s*'))
            if referee_label_i:
                # Find the nearest following <span> tag, which should contain the name
                referee_span = referee_label_i.find_next('span')
                if referee_span:
                    referee = referee_span.text.strip()
                else:
                    # Fallback: Try getting text from parent <p> and isolating (less reliable)
                    referee_parent_p = referee_label_i.find_parent('p', class_='b-fight-details__text')
                    if referee_parent_p:
                         full_text = referee_parent_p.get_text(separator=' ', strip=True)
                         # Try to extract text after "Referee:"
                         match = re.search(r'Referee:\s*(.*)', full_text, re.IGNORECASE)
                         if match:
                             potential_ref = match.group(1).strip()
                             # Avoid grabbing other fields if regex is too broad
                             if 'Details:' not in potential_ref and 'Method:' not in potential_ref:
                                 referee = potential_ref
            else:
                print("DEBUG: Referee label <i> not found.")


            # --- Finish Details Extraction (Revised) ---
            # Find the <i> tag containing the "Details:" label
            details_label_i = details_section.find('i', class_='b-fight-details__label', string=re.compile(r'\s*Details:\s*'))
            if details_label_i:
                # Get the parent <p> tag
                details_parent_p = details_label_i.find_parent('p', class_='b-fight-details__text')
                if details_parent_p:
                     # Get all text within the <p>, stripping extra whitespace
                     full_details_text = details_parent_p.get_text(separator=' ', strip=True)
                     # Remove the "Details:" label itself
                     finish_details_text = full_details_text.replace('Details:', '').strip()
                     # Optional: Clean up potential multiple spaces if get_text adds them
                     finish_details_text = re.sub(r'\s+', ' ', finish_details_text).strip()

                else:
                     print("DEBUG: Parent <p> for Details not found.")
            else:
                print("DEBUG: Details label <i> not found.")

            # --- Scheduled Rounds Extraction ---
            # Find the <i> tag containing the "Time format:" label
            time_format_label_i = details_section.find('i', class_='b-fight-details__label', string=re.compile(r'\s*Time format:\s*'))
            if time_format_label_i:
                # Get the parent <i> tag which contains the label and the value
                time_format_parent_i = time_format_label_i.find_parent('i', class_='b-fight-details__text-item')
                if time_format_parent_i:
                    # Extract the text content from the parent
                    full_text = time_format_parent_i.get_text(separator=' ', strip=True)
                    # Use regex to find a number followed by "Rnd"
                    match = re.search(r'(\d+)\s+Rnd', full_text)
                    if match:
                        try:
                            # Extract the matched number and convert to integer
                            scheduled_rounds = int(match.group(1))
                            print(f"DEBUG: Extracted scheduled rounds: {scheduled_rounds} from '{full_text}'")
                        except (ValueError, TypeError):
                            print(f"ERROR: Could not convert scheduled rounds number to int from '{match.group(1)}'")
                    else:
                        print(f"DEBUG: Could not find scheduled rounds pattern ('N Rnd') in text: '{full_text}'")
                else:
                    print("DEBUG: Parent <i> for Time Format not found.")
            else:
                 print("DEBUG: Time Format label <i> not found.")

        else:
             print("DEBUG: details_section (div.b-fight-details__content) not found.")


        print(f"  Referee: {referee}")
        print(f"  Finish Details: {finish_details_text}")
        print(f"  Scheduled Rounds: {scheduled_rounds}") # Add log for extracted value


        # Update fight record with these details
        if referee:
            print(f"DEBUG: Assigning referee '{referee}' to fight_record ID {fight_record.id}")
            fight_record.referee = referee
        else:
            print(f"DEBUG: No referee found or referee is empty for fight_record ID {fight_record.id}")

        if finish_details_text:
            print(f"DEBUG: Assigning finish_details '{finish_details_text}' to fight_record ID {fight_record.id}")
            fight_record.finish_details = finish_details_text
        else:
             print(f"DEBUG: No finish_details found or finish_details_text is empty for fight_record ID {fight_record.id}")

        # Assign scheduled rounds if found
        if scheduled_rounds is not None:
             print(f"DEBUG: Assigning scheduled_rounds '{scheduled_rounds}' to fight_record ID {fight_record.id}")
             fight_record.scheduled_rounds = scheduled_rounds
        else:
            # Optional: Decide if you want to default it if not found (e.g., to 3)
            # fight_record.scheduled_rounds = 3
            print(f"DEBUG: No scheduled_rounds found or value is None for fight_record ID {fight_record.id}. Keeping existing value: {fight_record.scheduled_rounds}")

        # Check if it's a title fight
        title_element = soup.select_one('i.b-fight-details__fight-title')
        fight_record.is_title_fight = bool(title_element and 'title' in title_element.text.lower())
        print(f"  Is Title Fight: {fight_record.is_title_fight}")

        # Determine winner (using fighter1 and fighter2 objects retrieved above)
        winner_name = None
        winner_elem = soup.select_one('i.b-fight-details__person-status_style_green')
        if winner_elem:
            parent_div = winner_elem.find_parent('div', class_='b-fight-details__person')
            if parent_div:
                winner_link = parent_div.select_one('a.b-fight-details__person-link')
                if winner_link:
                    winner_name = winner_link.text.strip()
                    print(f"Found winner name on page: {winner_name}")
                    
                    # Use the already retrieved fighter objects
                    f1_name = f"{fighter1.first_name} {fighter1.last_name}".strip()
                    f2_name = f"{fighter2.first_name} {fighter2.last_name}".strip()
                        
                    if winner_name.lower() in f1_name.lower() or f1_name.lower() in winner_name.lower():
                        fight_record.winner_id = fighter1.id
                        print(f"Set winner ID: {fighter1.id}")
                    elif winner_name.lower() in f2_name.lower() or f2_name.lower() in winner_name.lower():
                        fight_record.winner_id = fighter2.id
                        print(f"Set winner ID: {fighter2.id}")
                    else:
                        print(f"WARN: Winner name '{winner_name}' on page did not match fighters '{f1_name}' (ID: {fighter1.id}) or '{f2_name}' (ID: {fighter2.id})")
        else:
            print("Winner element not found on page.")
                    
        # Commit winner_id change if made
        if fight_record.winner_id:
            try:
                db_session.commit()
                print(f"Saved winner_id ({fight_record.winner_id}) to the database")
            except Exception as e:
                print(f"ERROR: Failed to save winner_id: {e}")
                db_session.rollback()

        # --- Helper function to extract stats like "Fighter Name X of Y (Z%)" ---
        def parse_stat_value(text_value):
            # Returns (landed, attempted, percentage) or None if not parsable
            original_text = text_value # Keep for logging
            text_value = text_value.strip()
            if not text_value:
                return None, None, None

            # Try time format "M:SS" first (more specific)
            time_match = re.search(r'(\d+):(\d+)', text_value)
            if time_match:
                try:
                    minutes = int(time_match.group(1))
                    seconds = int(time_match.group(2))
                    total_seconds = minutes * 60 + seconds
                    # print(f"DEBUG parse_stat: Matched time 'M:SS' in '{original_text}' -> {total_seconds} seconds") # Optional Debug
                    return total_seconds, None, None
                except (ValueError, TypeError, IndexError) as e:
                    print(f"DEBUG parse_stat: Error parsing 'M:SS' from '{original_text}': {e}")

            # Try "X of Y" next
            parts = re.search(r'(\d+)\s+of\s+(\d+)', text_value)
            if parts:
                try:
                    landed = int(parts.group(1))
                    attempted = int(parts.group(2))
                    # Try to get percentage explicitly listed like (Z%)
                    pct_match = re.search(r'\((\d+)%\)', text_value)
                    percentage = float(pct_match.group(1)) / 100.0 if pct_match else None
                    # Calculate if not listed
                    if percentage is None and attempted > 0:
                        percentage = landed / attempted
                    elif percentage is None: # attempts are 0 or parsing failed
                        percentage = 0.0 # Default if attempts are 0
                    # print(f"DEBUG parse_stat: Matched 'X of Y' in '{original_text}' -> ({landed}, {attempted}, {percentage})") # Optional Debug
                    return landed, attempted, percentage
                except (ValueError, TypeError, IndexError) as e:
                     print(f"DEBUG parse_stat: Error parsing 'X of Y' from '{original_text}': {e}")
                     return None, None, None # Error during parsing

            # Try percentage value like "48%"
            pct_only_match = re.search(r'(\d+)%', text_value)
            if pct_only_match:
                try:
                    # Return the number before the %, the assignment logic will divide by 100
                    pct_value = float(pct_only_match.group(1))
                    # print(f"DEBUG parse_stat: Matched percentage in '{original_text}' -> {pct_value}") # Optional Debug
                    return pct_value, None, None # Return the number (e.g., 48.0)
                except (ValueError, TypeError) as e:
                    print(f"DEBUG parse_stat: Error parsing percentage from '{original_text}': {e}")

            # Try just the first number found (for KD, Sub Att, Rev)
            num_match = re.search(r'(\d+)', text_value) # Find first sequence of digits
            if num_match:
                try:
                    value = int(num_match.group(1))
                    # print(f"DEBUG parse_stat: Matched first number in '{original_text}' -> ({value}, None, None)") # Optional Debug
                    return value, None, None # Landed = the number, Attempted=None, Pct=None
                except (ValueError, TypeError) as e:
                     print(f"DEBUG parse_stat: Error parsing number from '{original_text}': {e}")
                     return None, None, None

            # Special handling for "---" or "--"
            if text_value in ['---', '--']:
                # print(f"DEBUG parse_stat: Found dash in '{original_text}', treating as 0") # Optional Debug
                return 0, 0, 0.0 # Landed=0, Attempted=0, Pct=0.0 for stats like TD

            # Fallback: Couldn't parse known formats
            print(f"DEBUG parse_stat: Could not parse known stat format from: '{original_text}'")
            return None, None, None # Return tuple of Nones if unparseable


        # --- Identify Tables ---
        # First find sections that contain the tables we're looking for
        totals_section = soup.select_one('section.b-fight-details__section p.b-fight-details__collapse-link_tot')
        sig_strikes_section = soup.select_one('section.b-fight-details__section p.b-fight-details__collapse-link_tot[style*="margin-bottom: 0px"]')
        
        totals_table = None
        sig_strike_table = None
        col1_is_fighter1 = None # Initialize fighter order flag
        
        # Find the main totals table - it's the table immediately following the "Totals" section
        if totals_section:
            totals_section_parent = totals_section.find_parent('section')
            if totals_section_parent:
                # Get the next section that contains a table
                next_section = totals_section_parent.find_next_sibling('section')
                if next_section:
                    totals_table = next_section.select_one('table')
                    if totals_table:
                        print("Found main Totals table based on section heading")
                    else:
                        print("WARNING: Found Totals section but no table inside next section")
                else:
                    print("WARNING: Found Totals section but no next section")
        
        # Find the significant strikes table - it's the table immediately after the "Significant Strikes" section
        if sig_strikes_section:
            sig_table = sig_strikes_section.find_parent('section').find_next_sibling('table')
            if sig_table:
                sig_strike_table = sig_table
                print("Found Significant Strikes table based on section heading")
            else:
                print("WARNING: Found Significant Strikes section but no table")
                
        # Fallback to the old method if we couldn't find tables using the section headers
        if not totals_table or not sig_strike_table:
            print("Falling back to header-based table identification...")
            all_tables = soup.select('section table.b-fight-details__table, table') # Select all tables
            
            print(f"Found {len(all_tables)} tables in the page")
            for idx, table in enumerate(all_tables):
                # Skip tables we've already found
                if table == totals_table or table == sig_strike_table:
                    continue
                    
                # Check if we're in a round-specific section (avoid round tables)
                parent_row_head = table.find_parent('thead', class_='b-fight-details__table-row_type_head')
                if parent_row_head and "round" in parent_row_head.text.lower():
                    print(f"Skipping Table {idx} - appears to be round-specific data")
                    continue
                
                headers = [th.text.strip().lower() for th in table.select('thead th.b-fight-details__table-col')]
                if not headers:
                    continue
                    
                print(f"Table {idx} headers: {headers}")

                # Identify Totals Table if we still need one
                if not totals_table:
                    totals_indicators = ['total str.', 'kd', 'sub. att', 'rev.', 'ctrl']
                    totals_matches = sum(1 for indicator in totals_indicators if any(indicator in h for h in headers))
                    
                    # Avoid round-specific tables by checking if there's a Round header
                    round_header = any("round" in h.lower() for h in headers)
                    if not round_header and totals_matches >= 3:
                        print(f"Identified Table {idx} as Totals Table based on {totals_matches} matching headers.")
                        totals_table = table
                
                # Identify Significant Strikes Table if we still need one
                if not sig_strike_table:
                    sig_strike_indicators = ['head', 'body', 'leg', 'distance', 'clinch', 'ground']
                    sig_matches = sum(1 for indicator in sig_strike_indicators if indicator in headers)
                    
                    if sig_matches >= 3 and all(ind in headers for ind in ['head', 'body', 'leg']):
                        print(f"Identified Table {idx} as Significant Strikes Table based on headers.")
                        sig_strike_table = table

        if not totals_table:
            print("ERROR: Could not identify the Totals stats table!")
            # Decide if you want to return or continue without totals
        if not sig_strike_table:
            print("WARN: Could not identify the Significant Strikes breakdown table!")
            # Continue processing other data if possible

        # Determine fighter order from totals table if available
        if totals_table:
            col1_is_fighter1 = determine_fighter_order(totals_table, fighter1, fighter2)
        
        # Process tables with separated functions for better debugging
        if totals_table:
            parse_totals_table(totals_table, fight_record, fighter1, fighter2, col1_is_fighter1, parse_stat_value)
            
        if sig_strike_table:
            parse_significant_strikes_table(sig_strike_table, fight_record, col1_is_fighter1, parse_stat_value)
            
        # Now process the round-by-round stats
        parse_round_stats(soup, fight_record, fighter1, fighter2, col1_is_fighter1, parse_stat_value, db_session)
        
        processed_urls.add(fight_details_url)
        print(f"--- Finished processing fight details: {fight_details_url} ---")
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to fetch fight details for {fight_details_url}: {e}")
        processed_urls.add(fight_details_url)
        return

def determine_fighter_order(table, fighter1, fighter2):
    """Determine the order of fighters in the table (which one is in first row)"""
    print("\n--- Determining Fighter Order ---")
    stat_row = table.select_one('tbody.b-fight-details__table-body tr.b-fight-details__table-row')
    if not stat_row:
        print("WARNING: Could not find stats row to determine fighter order")
        return None
        
    stat_cells = stat_row.select('td.b-fight-details__table-col')
    if not stat_cells:
        print("WARNING: Could not find stat cells to determine fighter order")
        return None
        
    # Use the first cell (fighter names)
    fighter_cell = stat_cells[0]
    fighter_links = fighter_cell.select('p.b-fight-details__table-text a')
    if len(fighter_links) >= 2:
        fighter1_name = f"{fighter1.first_name} {fighter1.last_name}".strip()
        first_name_in_table = fighter_links[0].text.strip()
        if fighter1_name in first_name_in_table:
            col1_is_fighter1 = True
        else:
            col1_is_fighter1 = False # Assume fighter 2 is first if fighter 1 isn't
        print(f"Determined fighter order: col1_is_fighter1 = {col1_is_fighter1}")
        return col1_is_fighter1
    else:
        print("ERROR: Could not determine fighter order from table first column.")
        return None

def parse_totals_table(totals_table, fight_record, fighter1, fighter2, col1_is_fighter1, parse_stat_value):
    """Parse the totals table and populate the fight record with the data"""
    print("\n--- Processing Totals Table ---")
    header_cells = totals_table.select('tr.b-fight-details__table-row th.b-fight-details__table-col')
    if len(header_cells) < 2:
        print("WARNING: Could not find header cells in totals table")
        return
        
    col_to_stat = {}
    for idx, header in enumerate(header_cells):
        header_text = header.text.strip().lower()
        print(f"Found Totals header {idx}: '{header_text}'")
        col_to_stat[idx] = header_text
    print(f"Totals Column mapping: {col_to_stat}")

    stat_row = totals_table.select_one('tbody.b-fight-details__table-body tr.b-fight-details__table-row')
    if not stat_row:
        print("WARNING: Could not find stats row in totals table")
        return
        
    stat_cells = stat_row.select('td.b-fight-details__table-col')
    if len(stat_cells) < len(header_cells): # Check length consistency
        print(f"WARNING: Totals table header count ({len(header_cells)}) doesn't match data cell count ({len(stat_cells)})")
        return
        
    if col1_is_fighter1 is None: # Proceed only if order is determined
        print("ERROR: Fighter order not determined for totals table")
        return
        
    # Process each stat column (index matches header index)
    for col_idx, cell in enumerate(stat_cells):
        if col_idx not in col_to_stat or col_to_stat[col_idx] == 'fighter':
            continue # Skip fighter column or unmapped columns

        p_tags = cell.select('p.b-fight-details__table-text')
        if len(p_tags) < 2:
            print(f"WARNING: Totals Column {col_idx} ('{col_to_stat.get(col_idx)}') has fewer than 2 p tags")
            continue

        val1_raw = p_tags[0].text.strip()
        val2_raw = p_tags[1].text.strip()

        landed1, attempted1, pct1 = parse_stat_value(val1_raw)
        landed2, attempted2, pct2 = parse_stat_value(val2_raw)

        f1_landed, f1_attempted, f1_pct = (landed1, attempted1, pct1) if col1_is_fighter1 else (landed2, attempted2, pct2)
        f2_landed, f2_attempted, f2_pct = (landed2, attempted2, pct2) if col1_is_fighter1 else (landed1, attempted1, pct1)

        stat_name = col_to_stat[col_idx]
        print(f"  Processing Totals column: '{stat_name}' | F1: '{val1_raw if col1_is_fighter1 else val2_raw}' | F2: '{val2_raw if col1_is_fighter1 else val1_raw}'")

        # --- Assignment Logic for Totals Table ---
        if "kd" in stat_name:
            if f1_landed is not None: fight_record.fighter1_knockdowns = f1_landed
            if f2_landed is not None: fight_record.fighter2_knockdowns = f2_landed
        elif "sig. str." == stat_name: # Exact match for "Sig. str." (Landed/Attempted)
            if f1_landed is not None: fight_record.fighter1_sig_strikes_landed = f1_landed
            if f1_attempted is not None: fight_record.fighter1_sig_strikes_attempted = f1_attempted
            if f2_landed is not None: fight_record.fighter2_sig_strikes_landed = f2_landed
            if f2_attempted is not None: fight_record.fighter2_sig_strikes_attempted = f2_attempted
        elif "sig. str. %" == stat_name: # Exact match for "Sig. str. %"
            if f1_landed is not None: fight_record.fighter1_sig_strikes_pct = f1_landed / 100.0 # Comes as number like 48.0
            if f2_landed is not None: fight_record.fighter2_sig_strikes_pct = f2_landed / 100.0
        elif "total str." == stat_name: # Exact match for "Total str."
            if f1_landed is not None: fight_record.fighter1_total_strikes_landed = f1_landed
            if f1_attempted is not None: fight_record.fighter1_total_strikes_attempted = f1_attempted
            if f2_landed is not None: fight_record.fighter2_total_strikes_landed = f2_landed
            if f2_attempted is not None: fight_record.fighter2_total_strikes_attempted = f2_attempted
        elif "td" in stat_name and len(stat_name) <= 5: # More flexible match for any "td" or "td %" related column
            # Handle the takedown landed/attempted stat (typically just "td")
            if "%" not in stat_name and f1_landed is not None:
                fight_record.fighter1_takedowns_landed = f1_landed
                if f1_attempted is not None: fight_record.fighter1_takedowns_attempted = f1_attempted
                if f2_landed is not None: fight_record.fighter2_takedowns_landed = f2_landed
                if f2_attempted is not None: fight_record.fighter2_takedowns_attempted = f2_attempted
                
                # Calculate percentage here as primary source
                if f1_attempted is not None and f1_attempted > 0:
                    fight_record.fighter1_takedowns_pct = (f1_landed or 0) / f1_attempted
                    print(f"  Calculated fighter1_takedowns_pct: {fight_record.fighter1_takedowns_pct}")
                else:
                    fight_record.fighter1_takedowns_pct = 0.0
                    print(f"  Setting fighter1_takedowns_pct to 0.0")
                if f2_attempted is not None and f2_attempted > 0:
                    fight_record.fighter2_takedowns_pct = (f2_landed or 0) / f2_attempted
                    print(f"  Calculated fighter2_takedowns_pct: {fight_record.fighter2_takedowns_pct}")
                else:
                    fight_record.fighter2_takedowns_pct = 0.0
                    print(f"  Setting fighter2_takedowns_pct to 0.0")
            # Handle the takedown percentage stat (typically "td %")
            elif "%" in stat_name:
                # Only use this if calculation above didn't happen (e.g., TD column missing)
                if fight_record.fighter1_takedowns_pct is None:
                    if f1_landed is not None: fight_record.fighter1_takedowns_pct = f1_landed / 100.0
                    print(f"  Set fighter1_takedowns_pct from TD% col: {fight_record.fighter1_takedowns_pct}")
                if fight_record.fighter2_takedowns_pct is None:
                    if f2_landed is not None: fight_record.fighter2_takedowns_pct = f2_landed / 100.0
                    print(f"  Set fighter2_takedowns_pct from TD% col: {fight_record.fighter2_takedowns_pct}")
        elif "sub. att" in stat_name: # Fuzzy match ok here
            if f1_landed is not None: fight_record.fighter1_submission_attempts = f1_landed
            if f2_landed is not None: fight_record.fighter2_submission_attempts = f2_landed
        elif "rev." in stat_name: # Fuzzy match ok here
            if f1_landed is not None: fight_record.fighter1_reversals = f1_landed
            if f2_landed is not None: fight_record.fighter2_reversals = f2_landed
        elif "ctrl" in stat_name: # Fuzzy match ok here (Control Time)
            if f1_landed is not None: fight_record.fighter1_control_time_seconds = f1_landed
            if f2_landed is not None: fight_record.fighter2_control_time_seconds = f2_landed
        else:
            print(f"  Unknown or unhandled stat type in Totals: '{stat_name}'")

def parse_significant_strikes_table(sig_strike_table, fight_record, col1_is_fighter1, parse_stat_value):
    """Parse the significant strikes table and populate the fight record with the data"""
    print("\n--- Processing Significant Strikes Table ---")
    if col1_is_fighter1 is None:
        print("ERROR: Cannot process Sig Strikes table because fighter order was not determined")
        return
        
    header_cells_sig = sig_strike_table.select('tr.b-fight-details__table-row th.b-fight-details__table-col')
    col_to_breakdown = {}
    for idx, header in enumerate(header_cells_sig):
        header_text = header.text.strip().lower()
        print(f"Found Sig Strike header {idx}: '{header_text}'")
        col_to_breakdown[idx] = header_text
    print(f"Breakdown column mapping: {col_to_breakdown}")

    breakdown_row = sig_strike_table.select_one('tbody.b-fight-details__table-body tr.b-fight-details__table-row')
    if not breakdown_row:
        print("WARNING: Could not find breakdown stats row in Significant Strikes table")
        return
        
    breakdown_cells = breakdown_row.select('td.b-fight-details__table-col')
    if len(breakdown_cells) < len(header_cells_sig):
        print(f"WARNING: Sig Strike table header count ({len(header_cells_sig)}) doesn't match data cell count ({len(breakdown_cells)})")
        return
        
    # Process each breakdown column (index matches header index)
    for col_idx, cell in enumerate(breakdown_cells):
        if col_idx not in col_to_breakdown or col_to_breakdown[col_idx] == 'fighter':
            continue # Skip fighter column or unmapped columns

        p_tags = cell.select('p.b-fight-details__table-text')
        if len(p_tags) < 2:
            print(f"WARNING: Sig Strike Column {col_idx} ('{col_to_breakdown.get(col_idx)}') has fewer than 2 p tags")
            continue

        val1_raw = p_tags[0].text.strip()
        val2_raw = p_tags[1].text.strip()

        landed1, attempted1, _ = parse_stat_value(val1_raw)
        landed2, attempted2, _ = parse_stat_value(val2_raw)

        f1_landed, f1_attempted = (landed1, attempted1) if col1_is_fighter1 else (landed2, attempted2)
        f2_landed, f2_attempted = (landed2, attempted2) if col1_is_fighter1 else (landed1, attempted1)

        breakdown_type = col_to_breakdown[col_idx]
        print(f"  Processing breakdown: '{breakdown_type}' | F1: '{val1_raw if col1_is_fighter1 else val2_raw}' | F2: '{val2_raw if col1_is_fighter1 else val1_raw}'")

        # --- Assignment Logic for Significant Strikes Table ---
        if 'head' == breakdown_type:
            if f1_landed is not None: fight_record.fighter1_sig_strikes_head_landed = f1_landed
            if f1_attempted is not None: fight_record.fighter1_sig_strikes_head_attempted = f1_attempted
            if f2_landed is not None: fight_record.fighter2_sig_strikes_head_landed = f2_landed
            if f2_attempted is not None: fight_record.fighter2_sig_strikes_head_attempted = f2_attempted
        elif 'body' == breakdown_type:
            if f1_landed is not None: fight_record.fighter1_sig_strikes_body_landed = f1_landed
            if f1_attempted is not None: fight_record.fighter1_sig_strikes_body_attempted = f1_attempted
            if f2_landed is not None: fight_record.fighter2_sig_strikes_body_landed = f2_landed
            if f2_attempted is not None: fight_record.fighter2_sig_strikes_body_attempted = f2_attempted
        elif 'leg' == breakdown_type:
            if f1_landed is not None: fight_record.fighter1_sig_strikes_leg_landed = f1_landed
            if f1_attempted is not None: fight_record.fighter1_sig_strikes_leg_attempted = f1_attempted
            if f2_landed is not None: fight_record.fighter2_sig_strikes_leg_landed = f2_landed
            if f2_attempted is not None: fight_record.fighter2_sig_strikes_leg_attempted = f2_attempted
        elif 'distance' == breakdown_type:
            if f1_landed is not None: fight_record.fighter1_sig_strikes_distance_landed = f1_landed
            if f1_attempted is not None: fight_record.fighter1_sig_strikes_distance_attempted = f1_attempted
            if f2_landed is not None: fight_record.fighter2_sig_strikes_distance_landed = f2_landed
            if f2_attempted is not None: fight_record.fighter2_sig_strikes_distance_attempted = f2_attempted
        elif 'clinch' == breakdown_type:
            if f1_landed is not None: fight_record.fighter1_sig_strikes_clinch_landed = f1_landed
            if f1_attempted is not None: fight_record.fighter1_sig_strikes_clinch_attempted = f1_attempted
            if f2_landed is not None: fight_record.fighter2_sig_strikes_clinch_landed = f2_landed
            if f2_attempted is not None: fight_record.fighter2_sig_strikes_clinch_attempted = f2_attempted
        elif 'ground' == breakdown_type:
            if f1_landed is not None: fight_record.fighter1_sig_strikes_ground_landed = f1_landed
            if f1_attempted is not None: fight_record.fighter1_sig_strikes_ground_attempted = f1_attempted
            if f2_landed is not None: fight_record.fighter2_sig_strikes_ground_landed = f2_landed
            if f2_attempted is not None: fight_record.fighter2_sig_strikes_ground_attempted = f2_attempted
        # Note: The Sig Strike totals ('sig. str.' and 'sig. str. %') are usually in the *Totals* table,
        # not in this breakdown table. But for consistency we should handle them here too just in case.
        elif "sig. str" == breakdown_type or "sig. str." == breakdown_type:
            # Only assign if not already set from Totals table
            if fight_record.fighter1_sig_strikes_landed is None:
                if f1_landed is not None: fight_record.fighter1_sig_strikes_landed = f1_landed
            if fight_record.fighter1_sig_strikes_attempted is None:
                if f1_attempted is not None: fight_record.fighter1_sig_strikes_attempted = f1_attempted
            if fight_record.fighter2_sig_strikes_landed is None:
                if f2_landed is not None: fight_record.fighter2_sig_strikes_landed = f2_landed
            if fight_record.fighter2_sig_strikes_attempted is None:
                if f2_attempted is not None: fight_record.fighter2_sig_strikes_attempted = f2_attempted


def process_round_table(table_element, table_description, round_stats_dict, fight_record, fighter1, fighter2, col1_is_fighter1, parse_stat_value, db_session, is_sig_strike_table=False):
    """Processes a table containing round-by-round data (either general or sig strikes)."""
    print(f"  Processing table identified as: {table_description}")

    main_tbody = table_element.select_one(':scope > tbody') or table_element.find('tbody')
    if not main_tbody:
        print(f"    ERROR: Could not find a main tbody within the {table_description} table.")
        return

    print(f"    Found main tbody for {table_description} table. Iterating through its children...")

    current_round_number = None
    children = [child for child in main_tbody.children if isinstance(child, Tag)]
    print(f"    Found {len(children)} direct child tags in main tbody: {[c.name for c in children]}")

    for i, child in enumerate(children):
        # Check if the child is a THEAD containing the round header
        if child.name == 'thead':
            # --- Simplified Selector ---
            header_th = child.select_one('th[colspan]') # Look for any 'th' with colspan inside the thead
            if header_th:
                header_text = header_th.get_text(strip=True)
                round_match = re.search(r'round\s+(\d+)', header_text.lower())
                if round_match:
                    current_round_number = int(round_match.group(1))
                    print(f"\n    Found Header THEAD for Round {current_round_number}: '{header_text}' (Child Index: {i})")
                    continue # Expecting a TR next
                else:
                    print(f"    Found THEAD with th[colspan] (Child Index: {i}) but text '{header_text}' doesn't match 'Round X'.")
                    current_round_number = None # Not a round header
            else:
                print(f"    Found THEAD (Child Index: {i}) but couldn't find 'th[colspan]' inside it.")
                current_round_number = None

        # Check if the child is a TR AND we just identified a round header
        elif child.name == 'tr' and current_round_number is not None:
            print(f"    Found data TR (Child Index: {i}) following Header for Round {current_round_number}. Processing...")
            data_row = child

            data_cells = data_row.select(':scope > td.b-fight-details__table-col') or data_row.select('td.b-fight-details__table-col')
            if not data_cells:
                 print(f"      ERROR: Could not find data cells (td.b-fight-details__table-col) in data row for Round {current_round_number}.")
                 current_round_number = None
                 continue

            print(f"      Found {len(data_cells)} data cells for Round {current_round_number}")
            print("      Debug: Cell values for this row:")
            for cell_idx, cell in enumerate(data_cells):
                 p_tags = cell.select('p.b-fight-details__table-text')
                 cell_values = [p.get_text(strip=True) for p in p_tags]
                 print(f"        Cell {cell_idx}: {cell_values}")

            if current_round_number not in round_stats_dict:
                if is_sig_strike_table:
                    print(f"      WARNING: Sig strike data found for Round {current_round_number}, but no general stats object exists. Skipping.")
                    current_round_number = None
                    continue
                else:
                    fighter1_rs, fighter2_rs = get_or_create_round_stats(db_session, fight_record.id, fighter1.id, fighter2.id, current_round_number)
                    if fighter1_rs and fighter2_rs:
                        round_stats_dict[current_round_number] = (fighter1_rs, fighter2_rs)
                        if fighter1_rs not in db_session: db_session.add(fighter1_rs)
                        if fighter2_rs not in db_session: db_session.add(fighter2_rs)
                    else:
                        print(f"      Failed to get/create round stats objects for round {current_round_number}")
                        current_round_number = None
                        continue

            fighter1_round_stats, fighter2_round_stats = round_stats_dict[current_round_number]

            print(f"      Attempting to process stats for Round {current_round_number} ({table_description})...")
            if is_sig_strike_table:
                # Sig Strike Indices: 0=Fighter, 1=Sig Str, 2=Sig Str %, 3=Head, 4=Body, 5=Leg, 6=Distance, 7=Clinch, 8=Ground
                if len(data_cells) >= 4: process_round_stat(data_cells[3], 'Head', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'sig_strikes_head_landed', 'sig_strikes_head_attempted')
                if len(data_cells) >= 5: process_round_stat(data_cells[4], 'Body', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'sig_strikes_body_landed', 'sig_strikes_body_attempted')
                if len(data_cells) >= 6: process_round_stat(data_cells[5], 'Leg', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'sig_strikes_leg_landed', 'sig_strikes_leg_attempted')
                if len(data_cells) >= 7: process_round_stat(data_cells[6], 'Distance', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'sig_strikes_distance_landed', 'sig_strikes_distance_attempted')
                if len(data_cells) >= 8: process_round_stat(data_cells[7], 'Clinch', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'sig_strikes_clinch_landed', 'sig_strikes_clinch_attempted')
                if len(data_cells) >= 9: process_round_stat(data_cells[8], 'Ground', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'sig_strikes_ground_landed', 'sig_strikes_ground_attempted')
            else:
                # General Stats Indices: 0=Fighter, 1=KD, 2=Sig Str, 3=Sig Str %, 4=Total Str, 5=TD, 6=TD %, 7=Sub Att, 8=Rev, 9=Ctrl
                if len(data_cells) >= 2: process_round_stat(data_cells[1], 'KD', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'knockdowns')
                if len(data_cells) >= 3: process_round_stat(data_cells[2], 'Sig. Str.', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'sig_strikes_landed', 'sig_strikes_attempted')
                if len(data_cells) >= 4: process_round_stat(data_cells[3], 'Sig. Str. %', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'sig_strikes_pct', percentage=True)
                if len(data_cells) >= 5: process_round_stat(data_cells[4], 'Total Str.', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'total_strikes_landed', 'total_strikes_attempted')
                if len(data_cells) >= 6: process_round_stat(data_cells[5], 'TD', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'takedowns_landed', 'takedowns_attempted')
                if len(data_cells) >= 8: process_round_stat(data_cells[7], 'Sub. Att', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'submission_attempts')
                if len(data_cells) >= 9: process_round_stat(data_cells[8], 'Rev.', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'reversals')
                if len(data_cells) >= 10: process_round_stat(data_cells[9], 'Ctrl', fighter1_round_stats, fighter2_round_stats, col1_is_fighter1, parse_stat_value, 'control_time_seconds')

            current_round_number = None # Reset after processing the TR

        elif child.name == 'tbody':
             print(f"    Found TBODY (Child Index: {i}) but current_round_number is None. Skipping.")


def parse_round_stats(soup, fight_record, fighter1, fighter2, col1_is_fighter1, parse_stat_value, db_session):
    """Parse round-by-round stats and create FightRoundStats records."""
    print("\n--- Processing Round-by-Round Stats ---")

    round_stats = {} # Shared dictionary

    all_sections = soup.select('section.b-fight-details__section')
    per_round_sections = []
    print(f"Found {len(all_sections)} sections. Identifying 'Per round' sections...")
    for i, section in enumerate(all_sections):
        link = section.select_one('a.b-fight-details__collapse-link_rnd')
        if link:
            print(f"  Section {i+1} contains a 'Per round' link.")
            per_round_sections.append(section)

    if len(per_round_sections) < 1:
         print("WARNING: Could not find any 'Per round' sections. Skipping round stats.")
         return
    if len(per_round_sections) < 2:
        print(f"WARNING: Expected 2 sections with 'Per round' links, but found {len(per_round_sections)}. Sig Strike round stats may be missing.")

    # Process General Stats Table (if found)
    if len(per_round_sections) >= 1:
        general_stats_section = per_round_sections[0]
        print("\nProcessing FIRST 'Per round' section for GENERAL stats...")
        general_stats_table = general_stats_section.select_one(':scope > table.b-fight-details__table') or general_stats_section.select_one('table.b-fight-details__table')
        if general_stats_table:
            process_round_table(general_stats_table, "General", round_stats, fight_record, fighter1, fighter2, col1_is_fighter1, parse_stat_value, db_session, is_sig_strike_table=False)
        else:
            print("  WARNING: Could not find table within the first 'Per round' section.")

    # Process Sig Strikes Table (if found)
    if len(per_round_sections) >= 2:
        sig_strike_section = per_round_sections[1]
        print("\nProcessing SECOND 'Per round' section for SIGNIFICANT STRIKE stats...")
        sig_strike_table = sig_strike_section.select_one(':scope > table.b-fight-details__table') or sig_strike_section.select_one('table.b-fight-details__table')
        if sig_strike_table:
            process_round_table(sig_strike_table, "Significant Strikes", round_stats, fight_record, fighter1, fighter2, col1_is_fighter1, parse_stat_value, db_session, is_sig_strike_table=True)
        else:
            print("  WARNING: Could not find table within the second 'Per round' section.")

    # Save all round stats
    if round_stats:
        try:
            db_session.flush() # Assign IDs to new objects if needed
            db_session.commit()
            print(f"Successfully saved/updated round stats for Fight ID {fight_record.id}, Rounds {sorted(round_stats.keys())}")
        except Exception as commit_err:
            print(f"ERROR: Failed to commit round stats: {commit_err}")
            db_session.rollback()

def get_or_create_round_stats(db_session, fight_id, f1_id, f2_id, round_number):
    """Gets or initializes FightRoundStats objects for both fighters for a given round."""
    # Check if already exists in session's pending objects
    f1_stats = next((obj for obj in db_session.new if isinstance(obj, FightRoundStats) and obj.fight_id == fight_id and obj.fighter_id == f1_id and obj.round_number == round_number), None)
    if not f1_stats:
        f1_stats = db_session.query(FightRoundStats).filter_by(
            fight_id=fight_id, fighter_id=f1_id, round_number=round_number
        ).first()
    if not f1_stats:
        print(f"    Creating new FightRoundStats for Fighter1 (ID {f1_id}), Round {round_number}")
        f1_stats = FightRoundStats(fight_id=fight_id, fighter_id=f1_id, round_number=round_number)
        # Don't add here, add later if needed

    f2_stats = next((obj for obj in db_session.new if isinstance(obj, FightRoundStats) and obj.fight_id == fight_id and obj.fighter_id == f2_id and obj.round_number == round_number), None)
    if not f2_stats:
        f2_stats = db_session.query(FightRoundStats).filter_by(
            fight_id=fight_id, fighter_id=f2_id, round_number=round_number
        ).first()
    if not f2_stats:
         print(f"    Creating new FightRoundStats for Fighter2 (ID {f2_id}), Round {round_number}")
         f2_stats = FightRoundStats(fight_id=fight_id, fighter_id=f2_id, round_number=round_number)
         # Don't add here, add later if needed

    return f1_stats, f2_stats

def process_round_stat(cell, stat_name, fighter1_stats, fighter2_stats, col1_is_fighter1, parse_stat_value,
                      landed_field, attempted_field=None, percentage=False):
    """Helper function to process a single stat cell for round data"""
    p_tags = cell.select('p.b-fight-details__table-text')
    if len(p_tags) < 2:
        # Allow for stats that might only have one value (though unlikely in round tables)
        # print(f"      WARNING: {stat_name} cell has fewer than 2 p tags")
        if len(p_tags) == 1:
             val1_raw = p_tags[0].text.strip()
             val2_raw = "0" # Assume 0 for the missing fighter? Or None? Let's use 0 for now.
             print(f"      WARNING: {stat_name} cell only has 1 p tag. Assuming 0 for second fighter. Values: ['{val1_raw}']")
        else:
             print(f"      WARNING: {stat_name} cell has 0 p tags. Skipping.")
             return # Skip if no data
    else:
        val1_raw = p_tags[0].text.strip()
        val2_raw = p_tags[1].text.strip()

    # print(f"      Processing {stat_name}: F1='{val1_raw}', F2='{val2_raw}'")

    # Parse values
    landed1, attempted1, pct1 = parse_stat_value(val1_raw)
    landed2, attempted2, pct2 = parse_stat_value(val2_raw)

    # Assign based on fighter order
    if col1_is_fighter1:
        f1_landed, f1_attempted = landed1, attempted1
        f2_landed, f2_attempted = landed2, attempted2
    else:
        f1_landed, f1_attempted = landed2, attempted2
        f2_landed, f2_attempted = landed1, attempted1

    # Handle percentage values
    if percentage:
        target_val_f1 = f1_landed # Use landed value for percentage calculation
        target_val_f2 = f2_landed
        if target_val_f1 is not None:
            # Convert percentage (e.g. 72) to decimal (0.72)
            setattr(fighter1_stats, landed_field, target_val_f1 / 100.0)
        if target_val_f2 is not None:
            setattr(fighter2_stats, landed_field, target_val_f2 / 100.0)
    else:
        # Set landed value
        if f1_landed is not None:
            setattr(fighter1_stats, landed_field, f1_landed)
        if f2_landed is not None:
            setattr(fighter2_stats, landed_field, f2_landed)

        # Set attempted value if field provided
        if attempted_field:
            if f1_attempted is not None:
                setattr(fighter1_stats, attempted_field, f1_attempted)
            if f2_attempted is not None:
                setattr(fighter2_stats, attempted_field, f2_attempted)


def main_scraper(start_url):
    """Main function to control the scraping process."""
    # Use a list for the queue if order matters or potential retries are added
    scrape_queue = [start_url]
    processed_urls = set() # Keep track of URLs attempted

    # Get the session from the db instance within the app context
    # Note: We get the session inside the loop/functions now, as it needs the context
    # session = db.session # Remove this line or ensure it's used correctly within context

    print("--- Starting Main Scraper ---")
    print(f"Initial Queue: {scrape_queue}")

    try:
        while scrape_queue:
            # Use pop(0) for FIFO behavior (process in order added)
            current_url = scrape_queue.pop(0)
            print(f"\n>>> Processing URL from Queue: {current_url}")

            if current_url in processed_urls:
                print(f"Skipping already processed URL: {current_url}")
                continue

            # Pass the db session when calling scraping functions
            session = db.session

            # Determine URL type and call appropriate function
            if 'event-details' in current_url:
                scrape_event(current_url, session, scrape_queue, processed_urls)
            elif 'fighter-details' in current_url:
                scrape_fighter(current_url, session, scrape_queue, processed_urls)
            elif 'fight-details' in current_url:
                # We typically don't scrape fight details directly, they come from events
                # However, if needed, find the fight record first
                # This part might need adjustment depending on how you want to handle direct fight URLs
                # Example: find fight based on URL pattern or pass None and handle inside scrape_fight_details
                # fight_record = find_fight_by_url(current_url, session) # You'd need to implement this
                # if fight_record:
                #     scrape_fight_details(current_url, fight_record, session, processed_urls)
                # else:
                #     print(f"WARN: Could not find existing fight record for URL: {current_url}")
                # For now, just mark as processed if handling direct fight URLs isn't implemented/needed
                print(f"Skipping direct fight details URL (logic not implemented for standalone run): {current_url}")
                processed_urls.add(current_url) # Mark as processed
            else:
                print(f"Unknown URL type, skipping: {current_url}")
                processed_urls.add(current_url) # Mark as processed

            # Simple politeness delay
            time.sleep(1) # Reduce delay slightly now that sub-functions have delays

    except KeyboardInterrupt:
        print("\n--- Scraping interrupted by user (Ctrl+C) ---")
    except Exception as e:
        print(f"\n--- UNEXPECTED ERROR in main scraper loop ---")
        print(f"{type(e).__name__}: {e}")
        traceback.print_exc()
        # Rollback might fail if context is gone, handle gracefully
        try:
            db.session.rollback() # Use db.session directly here
        except Exception as rollback_err:
            print(f"Error during rollback in main loop exception handler: {rollback_err}")
    finally:
        # The session is managed by the Flask app context when run via CLI
        print(f"\n--- Scraping finished ---")
        print(f"Attempted to process approximately {len(processed_urls)} unique URLs.")
        print(f"{len(scrape_queue)} URLs remaining in queue (if interrupted).")


if __name__ == "__main__":
    import sys
    # Assume your Flask app object is named 'app' and created in 'app/__init__.py'
    # Adjust the import if your app object is located elsewhere or named differently
    from app import create_app, db

    if len(sys.argv) > 1:
        start_url = sys.argv[1]
        # Create the Flask app instance
        flask_app = create_app() # Use your app factory pattern if you have one
        # Push an application context
        with flask_app.app_context():
            print("Application context pushed.")
            # Now you can safely call functions that use db.session
            main_scraper(start_url) # Fixed indentation
            print("Application context popped.")
    else:
        print("Please provide a starting URL as an argument.") 