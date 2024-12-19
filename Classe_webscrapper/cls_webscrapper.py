import os
import time
import datetime as dt
from datetime import datetime
from typing import Dict, Optional
import pytz
import re
import logging

from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException
)

from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc

from logger import setup_logger
from app import SCRAP_DURATION

class ImprovedWebScraper:
    def __init__(self, duration: int = 180, live_prediction: bool = False) -> None:
        """
        Initialize the ImprovedWebScraper instance.

        Args:
            duration (int, optional): Duration in seconds for the scraping session. Defaults to 180.
            live_prediction (bool, optional): Flag to control live prediction data flow. Defaults to False.
        """
        self.duration = duration
        self.live_prediction = live_prediction
        self.start_time = time.time()
        self.url_crash_plane = ""
        self.driver = None

        # Set up logger
        self.logger = setup_logger('ImprovedWebScraper', self.get_log_file_name())
        self.logger.info("ImprovedWebScraper initialized.")

    def setup_driver(self) -> None:
        """
        Configures the browser for scraping using undetected-chromedriver and webdriver_manager.
        This ensures the correct ChromeDriver version is selected automatically.
        """
        self.logger.info("Setting up the Chrome driver with undetected-chromedriver and webdriver_manager.")

        options = uc.ChromeOptions()
        # Run in headless mode in server environments
        options.headless = False
        options.add_argument("--window-size=1920x1080")
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        options.add_argument(f'user-agent={user_agent}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument("--lang=fr-FR")
        options.add_argument('--incognito')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')

        try:
            # Use webdriver_manager to automatically install the correct driver
            driver_path = ChromeDriverManager().install()
            self.driver = uc.Chrome(options=options, driver_executable_path=driver_path)
            self.logger.info("Chrome driver setup complete with webdriver_manager.")
        except WebDriverException as e:
            self.logger.error(f"Error initializing Chrome driver: {e}")
            raise

    def search_for_url(self) -> str:
        """
        Searches for the crash game URL by loading the base page and extracting the iframe src.
        The iframe with class 'games-project-frame__item' contains the game's URL in its src attribute.

        Returns:
            str: The extracted crash game URL.

        Raises:
            NoSuchElementException: If the game iframe or its src cannot be found.
        """
        self.logger.info("Searching for the crash game URL.")
        base_url = "https://1xbet.com/en/allgamesentrance/crash"
        try:
            self.driver.get(base_url)
            # Wait until the iframe is present on the page
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.games-project-frame__item"))
            )

            # Locate the iframe and extract its 'src'
            iframe = self.driver.find_element(By.CSS_SELECTOR, "iframe.games-project-frame__item")
            iframe_src = iframe.get_attribute('src')

            if iframe_src:
                # The src might be relative; if so, prepend the base domain if needed
                if iframe_src.startswith("/"):
                    final_url = "https://1xbet.com" + iframe_src
                else:
                    final_url = iframe_src

                self.logger.info(f"Found crash game URL: {final_url}")
                return final_url
            else:
                self.logger.error("Failed to extract crash game URL from iframe src.")
                raise NoSuchElementException("Could not find crash game URL in the page.")

        except (NoSuchElementException, TimeoutException) as e:
            self.logger.warning(f"Encountered an issue loading {base_url}, retrying: {e}")
            time.sleep(2)
            # Retry once
            self.driver.get(base_url)
            time.sleep(5)
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.games-project-frame__item"))
                )
                iframe = self.driver.find_element(By.CSS_SELECTOR, "iframe.games-project-frame__item")
                iframe_src = iframe.get_attribute('src')

                if iframe_src:
                    if iframe_src.startswith("/"):
                        final_url = "https://1xbet.com" + iframe_src
                    else:
                        final_url = iframe_src

                    self.logger.info(f"Found crash game URL on retry: {final_url}")
                    return final_url
                else:
                    self.logger.error("Failed to extract crash game URL after retry (no src found).")
                    raise NoSuchElementException("Could not find crash game URL even after retry.")
            except (NoSuchElementException, TimeoutException):
                self.logger.error("Failed to extract crash game URL after retry.")
                raise NoSuchElementException("Could not find crash game URL even after retry.")

    def extract_data(self) -> Dict[str, str]:
        """
        Extracts the required data fields from the current page:
        - Value X
        - Value Bets
        - Value Prize
        - Value Players

        Returns:
            dict: A dictionary containing the extracted data fields.
        """
        self.logger.debug("Extracting data from page elements.")
        elements = {
            "Value X": "text.crash-game__counter[font-size='83'][x='1160'][y='356']",
            "Value Bets": "span.crash-total__value.crash-total__value--bets.crash-text",
            "Value Prize": "span.crash-total__value.crash-total__value--prize.crash-text",
            "Value Players": "span.crash-total__value.crash-total__value--players.crash-text"
        }
        data = {}
        try:
            for key, selector in elements.items():
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                data[key] = element.text.strip()
            self.logger.debug(f"Extracted data: {data}")
        except NoSuchElementException as e:
            self.logger.warning(f"One or more elements not found: {e}")
            # Return partial or empty data to handle gracefully
        return data

    def fetch_data(self, url: str) -> None:
        """
        Extracts data from the given URL and writes it to a CSV file.

        The extracted fields are: Timestamp, Value X, Value Bets, Value Prize, and Value Players.

        Args:
            url (str): The URL of the page to scrape.
        """
        self.logger.info(f"Fetching data from URL: {url}")
        try:
            self.driver.get(url)
            time.sleep(5)  # Wait for the page to load completely

            output_file = self.get_output_file_name()
            self.logger.info(f"Writing scraped data to: {output_file}")

            with open(output_file, "w", encoding='utf-8') as file:
                file.write("Timestamp,Value X,Value Bets,Value Prize,Value Players\n")

                while time.time() - self.start_time < self.duration:
                    try:
                        # Wait for required elements
                        WebDriverWait(self.driver, 30).until(
                            EC.presence_of_all_elements_located((By.TAG_NAME, 'svg'))
                        )

                        # Extract data
                        data = self.extract_data()
                        if not data or data.get('Value X', "") == "":
                            self.logger.debug("No valid data found or Value X empty, waiting before retrying.")
                            time.sleep(3)
                            continue

                        timestamp = self.get_timestamp()
                        line = f"{timestamp},{data['Value X'].replace('x','')},{data['Value Bets']},{data['Value Prize']},{data['Value Players']}\n"
                        file.write(line)
                        self.logger.info(f"Data extracted and written: {line.strip()}")
                        time.sleep(0.8)

                    except NoSuchElementException:
                        self.logger.warning("The crash plane URL changed or elements not found.")
                        break

            self.logger.info("Data fetching completed successfully.")
        except Exception as e:
            self.logger.error(f"Error while fetching data: {e}")

    def get_timestamp(self) -> str:
        """
        Returns the current time formatted as a string in Morocco time.

        Returns:
            str: The formatted timestamp.
        """
        morocco_time = datetime.now(pytz.timezone('Africa/Casablanca'))
        return morocco_time.strftime('%Y-%m-%d %H:%M:%S')

    def get_output_file_name(self) -> str:
        """
        Returns the output CSV file name, based on the start and end time of the scraping session.

        Returns:
            str: The formatted output file name.
        """
        morocco_time = datetime.now(pytz.timezone('Africa/Casablanca'))
        start_time_str = self.get_timestamp().replace(':', '_')
        end_time = morocco_time + dt.timedelta(seconds=self.duration)
        end_time_str = end_time.strftime('%Y-%m-%d_%H_%M_%S')
        if self.live_prediction:
            return f"pipeline_ml/live_predictor/live_prediction/data_brute_{start_time_str}_to_{end_time_str}.csv"
        return f"data_brute_{start_time_str}_to_{end_time_str}.csv"

    def get_log_file_name(self) -> str:
        """
        Returns the name of the log file, including start and end time.

        Returns:
            str: The formatted log file name.
        """
        morocco_time = datetime.now(pytz.timezone('Africa/Casablanca'))
        start_time_str = datetime.now(pytz.timezone('Africa/Casablanca')).strftime('%Y-%m-%d_%H_%M_%S')
        end_time = morocco_time + dt.timedelta(seconds=self.duration)
        end_time_str = end_time.strftime('%Y-%m-%d_%H_%M_%S')
        if self.live_prediction:
            return f"pipeline_ml/live_predictor/live_prediction/logs/log_{start_time_str}_to_{end_time_str}.txt"
        return f"logs/log_{start_time_str}_to_{end_time_str}.txt"

    def start_scraping(self) -> None:
        """
        Starts the scraping process for the given duration:
        1. Search for the dynamic crash game URL.
        2. Fetch data from that URL.
        3. Close the driver at the end.
        """
        self.logger.info(f"Scraping will run for {self.duration} seconds.")
        try:
            self.url_crash_plane = self.search_for_url()
            self.fetch_data(self.url_crash_plane)
        except Exception as e:
            self.logger.error(f"Error in scraping process: {e}")
        finally:
            self.close_driver()

    def close_driver(self) -> None:
        """
        Closes the browser and quits the driver.
        """
        if self.driver:
            self.logger.info("Closing the Chrome driver.")
            self.driver.quit()
            self.driver = None
            self.logger.info("Chrome driver closed successfully.")
        else:
            self.logger.warning("Driver was not initialized or already closed.")


def main(duration: float): 
    scraper = ImprovedWebScraper(duration=duration, live_prediction=False)
    scraper.setup_driver()
    scraper.start_scraping()


if __name__ == "__main__":
    main(SCRAP_DURATION)