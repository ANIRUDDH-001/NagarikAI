import subprocess
import sys

def main():
    subprocess.run([sys.executable, "backend/scrapers/generate_tier1_seed.py"] + sys.argv[1:])
    subprocess.run([sys.executable, "backend/scrapers/populate_real_schemes.py"] + sys.argv[1:])

if __name__ == "__main__":
    main()
