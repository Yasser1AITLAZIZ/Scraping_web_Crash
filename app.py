import os
from frontend import main


SCRAP_DURATION = int(os.getenv("SCRAPING_DURATION", 60*60))

if __name__ == "__main__":
    main(SCRAP_DURATION)
