import os
import sys

# Ensure project root is on sys.path when running this file directly
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

from crawler import (
	jugantor_scraper,
	daily_star_scraper,
	prothomalo_scraper,
	dhaka_tribune_scraper,
)


def run_all_scrapers():
	jugantor_scraper.main()
	daily_star_scraper.main()
	prothomalo_scraper.main()
	dhaka_tribune_scraper.main()


if __name__ == "__main__":
	run_all_scrapers()