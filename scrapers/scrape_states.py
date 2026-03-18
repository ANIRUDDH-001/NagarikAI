import subprocess
import sys

def main():
    subprocess.run([sys.executable, "backend/scrapers/scrape_up.py"] + sys.argv[1:])
    subprocess.run([sys.executable, "backend/scrapers/scrape_bihar.py"] + sys.argv[1:])
    subprocess.run([sys.executable, "backend/scrapers/scrape_maharashtra.py"] + sys.argv[1:])
    subprocess.run([sys.executable, "backend/scrapers/scrape_tn.py"] + sys.argv[1:])

if __name__ == "__main__":
    main()
