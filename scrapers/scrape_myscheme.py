import subprocess
import sys

def main():
    subprocess.run([sys.executable, "backend/scrapers/scrape_schemes_list.py"] + sys.argv[1:])
    subprocess.run([sys.executable, "backend/scrapers/scrape_schemes_details.py"] + sys.argv[1:])

if __name__ == "__main__":
    main()
