from src.ingestion.pdf_parser import get_race_url, parse_pdf_sec_res, download_pdf

# The race_number value corresponds to race race_number in the season, which will have its
# race contents ran through the pipeline. 
race_number = 1

def main():
    print("Pipeline execution started.");
    race_url = get_race_url("src/ingestion/races26.csv", race_number)
    print(f"Race URL for race number {race_number}: {race_url}")
    print("Parsing PDF...")
    raw_data = parse_pdf_sec_res(race_url)
    # Print the first 45 rows of the DataFrame for inspection
    print(raw_data.head(200))

if __name__ == "__main__":
    main()