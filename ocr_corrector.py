import re
import json
from datetime import datetime


class OCRDataCorrector:
    """
    Class to handle OCR data corrections for the EFT Tracker application.
    Fixes common OCR recognition errors in map names, numerical values, and more.
    """

    def __init__(self):
        # Maps known incorrect OCR readings to their correct values
        self.map_corrections = {
            # Common map name errors
            "Factorv": "Factory",
            "Factorvy": "Factory",
            "Factary": "Factory",
            "Factor": "Factory",
            "interchannge": "Interchange",
            "Intcrchange": "Interchange",
            "intcrchange": "Interchange",
            "lnterchange": "Interchange",
            "Custams": "Customs",
            "Custom": "Customs",
            "Customs,": "Customs",
            "Custorns": "Customs",
            "Woads": "Woods",
            "Waods": "Woods",
            "\/Voods": "Woods",
            "VVoods": "Woods",
            "Light house": "Lighthouse",
            "Light-house": "Lighthouse",
            "Ughtthouse": "Lighthouse",
            "Ugnthouse": "Lighthouse",
            "Lghtthouse": "Lighthouse",
            "Reservs": "Reserve",
            "Reserva": "Reserve",
            "Rcserve": "Reserve",
            "Roserve": "Reserve",
            "Shorelina": "Shoreline",
            "Shorcline": "Shoreline",
            "Shorenne": "Shoreline",
            "Strest": "Streets",
            "Strects": "Streets",
            "Strects of Tarkov": "Streets",
            "Streets af Tarkov": "Streets",
            "Streets of Tarkav": "Streets",
            "Ground Zcro": "Ground Zero",
            "Ground 2ero": "Ground Zero",
            "Graund Zero": "Ground Zero",
            "Labratory": "The Lab",
            "Laboratary": "The Lab",
            "Laba": "The Lab",
            "The Laba": "The Lab"
        }

        # Common faction name corrections
        self.faction_corrections = {
            "USEC": "USEC",
            "BEAR": "BEAR",
            "USCC": "USEC",
            "USAR": "USEC",
            "BAER": "BEAR",
            "BFAR": "BEAR",
            "Scav": "Scav",
            "Boss": "Boss",
            "Rogue": "Rogue",
            "Roque": "Rogue",
            "Raider": "Raider"
        }

        # Common status corrections
        self.status_corrections = {
            "Survivcd": "Survived",
            "Survivod": "Survived",
            "Surwived": "Survived",
            "KIA": "KIA",  # Modified: Keep KIA as KIA
            "Killed": "Killed",  # Modified: Keep "Killed" as "Killed"
            "Killed in Acton": "Killed in Action",
            "MIA": "MIA",  # Modified: Keep MIA as MIA
            "Missing": "Missing",  # Modified: Keep "Missing" as "Missing"
            "Missinq in Action": "Missing in Action"
        }

    def correct_map_name(self, map_name):
        """Fixes common OCR errors in map names"""
        if not map_name or map_name == "Unknown":
            return "Unknown"

        # Check direct mapping first
        if map_name in self.map_corrections:
            return self.map_corrections[map_name]

        # Try case-insensitive mapping
        for incorrect, correct in self.map_corrections.items():
            if map_name.lower() == incorrect.lower():
                return correct

        # Handle special cases like "Streets of Tarkov" -> "Streets"
        if "street" in map_name.lower():
            return "Streets"
        if "lab" in map_name.lower():
            return "The Lab"
        if "light" in map_name.lower() and "house" in map_name.lower():
            return "Lighthouse"
        if "ground" in map_name.lower() and ("zero" in map_name.lower() or "0" in map_name.lower()):
            return "Ground Zero"

        # If no corrections found, return the original
        return map_name

    def correct_status(self, status_text):
        """
        Fixes common OCR errors in raid status
        Also replaces 'O' or 'o' between numbers with '0'
        """
        if not status_text or status_text == "Unknown":
            return "Unknown"

        # NEW: Replace 'O' or 'o' between numbers with '0'
        # Use regex to find 'O' or 'o' between digits
        corrected_text = re.sub(r'(?<=\d)[Oo](?=\d)', '0', status_text)

        # IMPORTANT: If the string already starts with "Killed", preserve it completely
        # This preserves weapon and distance information in kill lists
        if corrected_text.startswith("Killed"):
            return corrected_text

        # Check direct mapping for corrections
        if corrected_text in self.status_corrections:
            return self.status_corrections[corrected_text]

        # Look for keywords for other status types
        if "surv" in corrected_text.lower():
            return "Survived"

        # For raid status (not kill list status), preserve format
        if corrected_text.lower() == "kia":
            return "KIA"
        if corrected_text.lower() == "mia":
            return "MIA"

        # For raid status, handle expanded forms
        if "killed in action" in corrected_text.lower():
            return "Killed in Action"
        if "missing in action" in corrected_text.lower():
            return "Missing in Action"

        return corrected_text
    def correct_faction(self, faction_text):
        """Fixes common OCR errors in faction names"""
        if not faction_text or faction_text == "Unknown":
            return "Unknown"

        # Check direct mapping
        if faction_text in self.faction_corrections:
            return self.faction_corrections[faction_text]

        # Case insensitive checks
        faction_text_lower = faction_text.lower()
        if "usec" in faction_text_lower:
            return "USEC"
        if "bear" in faction_text_lower:
            return "BEAR"
        if "scav" in faction_text_lower:
            return "Scav"
        if "boss" in faction_text_lower:
            return "Boss"
        if "rog" in faction_text_lower:
            return "Rogue"
        if "raid" in faction_text_lower:
            return "Raider"

        return faction_text

    def correct_number(self, number_text):
        """
        Fixes OCR errors in numerical values
        Returns an integer or 0 if conversion fails

        Handles specific issues:
        - '0' read as '@'
        - '9' read as 'g'
        - 'O' (letter) read as '0' (number)
        """
        if not number_text:
            return 0

        # Replace common OCR misreadings
        corrected_text = number_text.replace('@', '0').replace('g', '9').replace('O', '0')

        # Extract only digits from the text
        try:
            # Find numbers in the text
            digits = re.findall(r'\d+', corrected_text)
            if digits:
                # Join all found digits and convert to int
                return int(''.join(digits))
            return 0
        except (ValueError, TypeError):
            return 0

    def correct_time_format(self, time_text):
        """
        Fixes OCR errors in time format
        Handles specific issues like:
        - '0' read as '@'
        - '9' read as 'g'
        - Improper separators (., :)
        - Reformats time as xx:xx:xx
        """
        if not time_text or time_text == "Unknown":
            return "Unknown"

        # First, correct common digit misreadings
        corrected_text = time_text.replace('@', '0').replace('g', '9')

        # Extract only digits from the text
        digits = re.findall(r'\d', corrected_text)

        # If we have at least 2 digits, format properly
        if len(digits) >= 2:
            # Pad with zeros if we don't have enough digits for HH:MM:SS
            while len(digits) < 6:
                digits.insert(0, '0')

            # Format as HH:MM:SS
            if len(digits) >= 6:
                return f"{digits[0]}{digits[1]}:{digits[2]}{digits[3]}:{digits[4]}{digits[5]}"

        # Fallback: just return the corrected text
        return corrected_text

    def correct_date_format(self, date_text, folder_name=None):
        """
        Attempts to correct and standardize date formats
        If the date text is unreadable, tries to extract from folder_name
        """
        if not date_text or date_text == "Unknown":
            # Try to extract from folder name if provided
            if folder_name:
                try:
                    # Try to parse folder name like "dd-mm-yyyy_hh-mm"
                    raid_date = datetime.strptime(folder_name, "%d-%m-%Y_%H-%M")
                    return raid_date.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    # If that fails, return as is
                    return folder_name
            return "Unknown"

        # Common OCR date format corrections could go here
        return date_text

    def correct_kill_data(self, kill_list):
        """
        Corrects OCR errors in the kill list data
        Returns an empty dictionary if row1 is empty
        """
        corrected_kills = {}

        # Check if row1 is empty or doesn't have a valid player name
        if "row1" in kill_list and not kill_list["row1"].get("Player", "").strip():
            # Return empty dictionary as requested
            return {}

        for row_key, kill_data in kill_list.items():
            # Skip empty or invalid rows
            if not kill_data.get("Player", "").strip():
                continue

            corrected_kill = {}

            # Correct each field
            corrected_kill["Time"] = self.correct_time_format(kill_data.get("Time", ""))
            corrected_kill["Player"] = kill_data.get("Player", "").strip()

            # Try to extract level as a number
            lvl_text = kill_data.get("LVL", "")
            if lvl_text:
                corrected_kill["LVL"] = str(self.correct_number(lvl_text))
            else:
                corrected_kill["LVL"] = ""

            corrected_kill["Faction"] = self.correct_faction(kill_data.get("Faction", ""))
            corrected_kill["Status"] = self.correct_status(kill_data.get("Status", ""))

            corrected_kills[row_key] = corrected_kill

        return corrected_kills

    def correct_raid_data(self, raid_data):
        """
        Main function to correct all raid data fields
        Takes a raid data dictionary and returns a corrected version
        """
        corrected_raid = raid_data.copy()

        # Correct map name
        corrected_raid["map"] = self.correct_map_name(raid_data.get("map", "Unknown"))

        # Correct status
        corrected_raid["status"] = self.correct_status(raid_data.get("status", "Unknown"))

        # Correct numerical values
        corrected_raid["kills"] = self.correct_number(str(raid_data.get("kills", 0)))
        corrected_raid["exp"] = self.correct_number(str(raid_data.get("exp", 0)))
        corrected_raid["level"] = self.correct_number(str(raid_data.get("level", 0)))

        # Correct time
        corrected_raid["time"] = self.correct_time_format(raid_data.get("time", "Unknown"))

        # Correct date
        corrected_raid["date"] = self.correct_date_format(
            raid_data.get("date", "Unknown"),
            raid_data.get("folder_name", "")
        )

        # Correct kill list if present
        if "kill_list" in raid_data:
            corrected_raid["kill_list"] = self.correct_kill_data(raid_data["kill_list"])

        return corrected_raid


# Example of how to integrate with the EFT Tracker app
def integrate_ocr_correction(eft_tracker_app):
    """
    Shows how to integrate OCR correction into the EFT Tracker app
    Replace the load_raids method or add to process_ocr_data
    """
    # Create the corrector instance
    corrector = OCRDataCorrector()

    # Original load_raids method
    original_raids = eft_tracker_app.raids.copy()

    # Apply corrections to each raid
    corrected_raids = []
    for raid in original_raids:
        corrected_raid = corrector.correct_raid_data(raid)
        corrected_raids.append(corrected_raid)

    # Update the app's raids with corrected data
    eft_tracker_app.raids = corrected_raids

    # Log the corrections
    if hasattr(eft_tracker_app, 'log_text_edit'):
        eft_tracker_app.log_text_edit.append(f"Applied OCR corrections to {len(corrected_raids)} raids")

    # Update the UI
    eft_tracker_app.update_raid_tiles()
    eft_tracker_app.update_stats()


# Example of JSON correction - for standalone use
def correct_raid_json_file(json_file_path, output_path=None):
    """
    Standalone function to correct a raid_data.json file
    Reads the file, applies corrections, and saves back or to a new file
    """
    try:
        # Read the original JSON
        with open(json_file_path, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)

        # Create corrector
        corrector = OCRDataCorrector()

        # Apply corrections to the OCR data structure
        # This would need to be adapted to match your specific JSON structure
        if "Status" in ocr_data:
            for key, value in ocr_data["Status"].items():
                if isinstance(value, list):
                    # Join list items and correct
                    corrected = value
                    if key == "Status":
                        joined = " ".join(value)
                        corrected_text = corrector.correct_status(joined)
                        corrected = [corrected_text]
                    ocr_data["Status"][key] = corrected

        if "KillList" in ocr_data:
            for row_key, row_data in ocr_data["KillList"].items():
                for field, value in row_data.items():
                    if field == "Faction":
                        row_data[field] = corrector.correct_faction(value)
                    # Add other corrections as needed

        if "RaidStatistics" in ocr_data and "map" in ocr_data["RaidStatistics"]:
            # Correct map name in the list
            if isinstance(ocr_data["RaidStatistics"]["map"], list):
                joined = " ".join(ocr_data["RaidStatistics"]["map"])
                ocr_data["RaidStatistics"]["map"] = [corrector.correct_map_name(joined)]

        # Save corrected data
        output_file = output_path if output_path else json_file_path
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ocr_data, f, ensure_ascii=False, indent=4)

        print(f"Corrected data saved to {output_file}")
        return True

    except Exception as e:
        print(f"Error correcting JSON file: {e}")
        return False