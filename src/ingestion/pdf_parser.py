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

def parse_pdf(race_url: str) -> pandas.DataFrame:
    """
    Parses the PDF file at the given URL and extracts lap data into a structured DataFrame.
    """
    # Download PDF into memory
    response = requests.get(race_url)
    response.raise_for_status()  # Check for HTTP errors (e.g., 404 or 403)

    all_laps = []
    # Wrap bytes in a BytesIO buffer for use with pdfplumber
    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")
        
            for line in lines:
                # Detect Driver Header (e.g., "Car 10 - Palou, Alex")
                driver_match = re.search(r'Car\s+(\d+)\s+-\s+([A-Za-z\s,]+)', line)
                if driver_match:
                    current_driver_no = driver_match.group(1)
                    current_driver_name = driver_match.group(2).strip()
                    continue

                # Detect Lap Data Lines (Starts with Lap Number integer)
                parts = line.split()
                if parts and parts[0].isdigit() and len(parts) > 4:
                    lap_num = int(parts[0])    
                    lap_time_str = parts[-2]  # Lap time string (e.g., '01:06.4211')
                    lap_speed = parts[-1]     # Lap speed (e.g., '110.231')

                    all_laps.append({
                        'CarNo': current_driver_no,
                        'Driver': current_driver_name,
                        'Lap': lap_num,
                        'LapTime': lap_time_str,
                        'LapSpeed': lap_speed
                    })

    # Return structured DataFrame ready for cleaning
    return pandas.DataFrame(all_laps)

def parse_race_pdf(file_path: str, race_number: int) -> pandas.DataFrame:
    """
    Combines the functionality of get_race_url and parse_pdf to directly 
    parse the PDF for a given race number from a CSV file.
    """
    race_url = get_race_url(file_path, race_number)
    return parse_pdf(race_url)