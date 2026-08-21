import pdfplumber
import pandas
import io
import requests
import re


def get_race_url(file_path: str, race_number: int) -> str:
    """
    Extracts the URL of a given race number race_number from a csv file.
    """
    df = pandas.read_csv(file_path, header=0)

    matching_rows = df.loc[df['Race'] == race_number, 'URL']

    return str(matching_rows.iloc[0])

def download_pdf(race_url: str) -> pandas.DataFrame:
    """
    Downloads pdf to see raw state of pdf for diagnostic purposes.
    """
    response = requests.get(race_url)
    response.raise_for_status()

    print(f"Downloaded {len(response.content):,} bytes")

    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        print(f"PDF contains {len(pdf.pages)} pages")

        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()

            # if not text:
            #     print(f"\n--- PAGE {page_number}: NO TEXT ---")
            #     continue

            # print(f"\n{'=' * 80}")
            # print(f"PAGE {page_number}")
            # print(f"{'=' * 80}")

            print(text[:5000])

            # Only inspect the first few pages for now
            if page_number >= 4:
                break

    return pandas.DataFrame()

def parse_time_to_float(time_str):
    """Safely converts time strings or speeds into floats, handling colons if present."""
    if not time_str:
        return None
    time_str = time_str.replace(",", "").replace("+", "").strip()
    try:
        if ":" in time_str:
            parts = time_str.split(":")
            return float(parts[0]) * 60 + float(parts[1])
        return float(time_str)
    except ValueError:
        return None

def parse_pdf_sec_res(race_url: str) -> pandas.DataFrame:
    """
    Parses IndyCar Section Results PDF to extract lap data for each driver. Returns a structured
    DataFrame with columns: CarNo, Driver, Lap, LapTime, LapSpeed. 
    
    """
    response = requests.get(race_url)
    response.raise_for_status()

    laps_data = {}
    current_driver_no = None
    current_driver_name = None

    # Wraps bytes in BytesIO stream for pdfplumber to read
    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            
            # Identify driver
            driver_match = re.search(r"Section Data for Car\s+(\d+)\s+-\s+(.+)", text)
            if driver_match:
                current_driver_no = driver_match.group(1).strip()
                current_driver_name = driver_match.group(2).strip()

            if not current_driver_no:
                continue

            words = page.extract_words()
            
            # Locate T/S header and anchor position
            ts_word = next((w for w in words if w['text'] == "T/S"), None)
            if not ts_word:
                continue
                
            ts_x0 = ts_word['x0']
            ts_top = ts_word['top']
            ts_bottom = ts_word['bottom']
            
            # Locate lap header to anchor lap column position
            header_lap_words = [
                w for w in words 
                if w['text'] == "Lap" and not (w['bottom'] < ts_top or w['top'] > ts_bottom)
            ]
            total_lap_word = next((w for w in header_lap_words if w['x0'] > ts_x0), None)
            
            # Skip pages without lap header
            if not total_lap_word:
                continue
                
            # Define bounding box for lap column
            col_x0 = total_lap_word['x0'] - 15
            col_x1 = total_lap_word['x1'] + 25

            # Define bounding box for lap number column
            lap_num_word = next((w for w in header_lap_words if w['x0'] < ts_x0), None)
            lap_col_x0 = lap_num_word['x0'] - 15 if lap_num_word else 0
            lap_col_x1 = lap_num_word['x1'] + 15 if lap_num_word else ts_x0

            # Find row anchors using 'T' and 'S' rows
            row_anchors = [
                w for w in words 
                if w['text'] in ["T", "S"] and abs(w['x0'] - ts_x0) < 15
            ]
            row_anchors.sort(key=lambda w: w['top'])
            
            current_lap = None
            
            for anchor in row_anchors:
                ts_type = anchor['text']
                
                # Loose Y-tolerance to capture all words on row line
                anchor_mid_y = (anchor['top'] + anchor['bottom']) / 2
                row_words = [
                    w for w in words 
                    if abs((w['top'] + w['bottom']) / 2 - anchor_mid_y) < 6
                ]
                
                # Extract lap number
                if ts_type == "T":
                    lap_cells = [
                        w for w in row_words 
                        if lap_col_x0 <= (w['x0'] + w['x1']) / 2 <= lap_col_x1 and w['text'].isdigit()
                    ]
                    if lap_cells:
                        current_lap = int(lap_cells[0]['text'])
                
                if current_lap is None:
                    continue
                    
                # Extract lap time and speed using lap column bounding box
                target_cells = [
                    w for w in row_words 
                    if col_x0 <= (w['x0'] + w['x1']) / 2 <= col_x1
                ]
                
                if target_cells:
                    # Take the word closest to the center of the column lane
                    col_center = (col_x0 + col_x1) / 2
                    best_cell = min(target_cells, key=lambda w: abs((w['x0'] + w['x1']) / 2 - col_center))
                    val_float = parse_time_to_float(best_cell['text'])
                    
                    if val_float is not None:
                        lap_key = (current_driver_no, current_lap)
                        if lap_key not in laps_data:
                            laps_data[lap_key] = {
                                "CarNo": current_driver_no,
                                "Driver": current_driver_name,
                                "Lap": current_lap,
                                "LapTime": None,
                                "LapSpeed": None
                            }
                            
                        if ts_type == "T":
                            laps_data[lap_key]["LapTime"] = val_float
                        elif ts_type == "S":
                            laps_data[lap_key]["LapSpeed"] = val_float

    completed_laps = list(laps_data.values())
    return pandas.DataFrame(
        completed_laps,
        columns=["CarNo", "Driver", "Lap", "LapTime", "LapSpeed"]
    )

def parse_race_pdf_sec_res(file_path: str, race_number: int) -> pandas.DataFrame:
    """
    Combines the functionality of get_race_url and parse_pdf to directly 
    parse the PDF for a given race number from a CSV file.
    """
    race_url = get_race_url(file_path, race_number)
    return parse_pdf_sec_res(race_url)