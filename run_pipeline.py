from src.ingestion.pdf_parser import get_race_url, parse_pdf

# The race_number value corresponds to race race_number in the season, which will have its
# race contents ran through the pipeline. 
race_number = 1

def main():
    print("Pipeline execution started.");
    race_url = get_race_url("src/ingestion/races26.csv", race_number)
    print(f"Race URL for race number {race_number}: {race_url}")
    raw_data = parse_pdf(race_url)