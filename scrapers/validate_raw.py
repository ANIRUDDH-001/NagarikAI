import subprocess
import sys

def main():
    subprocess.run([sys.executable, "backend/scrapers/validate_raw.py"] + sys.argv[1:])

if __name__ == "__main__":
    main()
