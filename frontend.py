import os
import time
import glob
import subprocess
from typing import List, Optional
import streamlit as st

SCRAPER_COMMAND = ["python", "Classe_webscrapper/cls_webscrapper.py"]

class ScraperUI:
    """
    A class to manage the Streamlit UI for controlling and monitoring a long-running scraping process.
    This class handles:
    - Launching the scraping process in a separate subprocess.
    - Displaying a progress bar based on the elapsed time vs. the defined duration.
    - Displaying logs in real-time.
    - Stopping the scraping if an error appears in the logs or manually via a stop button.
    """

    def __init__(self, logs_dir: str = "logs", duration: int = 60*30) -> None:
        """
        Initialize the ScraperUI.

        Args:
            logs_dir (str): Directory where log files are stored.
            duration (int): The total duration of the scraping process in seconds.
        """
        self.logs_dir = logs_dir
        self.duration = duration
        # Initialize Streamlit session state variables if not present
        if "scraping_started" not in st.session_state:
            st.session_state["scraping_started"] = False
            st.session_state["scraping_start_time"] = None
            st.session_state["scraping_process"] = None
            st.session_state["scraping_error"] = False

    def run(self) -> None:
        """
        Run the Streamlit UI. This method draws the UI components and handles interactions.
        """
        st.set_page_config(
            page_title="Scraper with Progress",
            page_icon="📜",
            layout="wide"
        )

        st.title("📜 Scraper with Progress")
        st.write("This interface allows you to launch the scraper, display its logs, show a progress bar, and stop it manually or when an error is detected.")

        self._draw_sidebar()
        self._handle_main_area()

    def _draw_sidebar(self) -> None:
        """
        Draw the sidebar with refresh and stop buttons.
        """
        st.sidebar.title("Controls")

        if st.sidebar.button("Refresh"):
            # Pressing this button reruns the script, thus refreshing logs and status
            pass

        if st.sidebar.button("Stop Scraping"):
            # Attempt to stop the scraping process manually
            self._stop_scraping("Stopped manually by user.")

    def _handle_main_area(self) -> None:
        """
        Handle the main UI area logic: start button, progress bar, logs display.
        """
        if not st.session_state["scraping_started"] and not st.session_state["scraping_error"]:
            # Show start button if scraping not started and no error occurred
            if st.button("Start Scraping"):
                self._start_scraping()
                st.success("Scraping started!")
        elif st.session_state["scraping_error"]:
            # If an error has already occurred, inform the user
            st.error("Scraping stopped due to an ERROR in logs.")
        else:
            # Scraping is running
            st.info("Scraping is running...")

        # If scraping is ongoing and no error yet, display progress and logs
        if st.session_state["scraping_started"] and not st.session_state["scraping_error"]:
            elapsed = time.time() - st.session_state["scraping_start_time"]
            progress_ratio = min(elapsed / self.duration, 1.0)
            st.progress(progress_ratio)

            time_left = max(0, self.duration - elapsed)
            st.write(f"Time elapsed: {int(elapsed)} seconds")
            st.write(f"Time left: {int(time_left)} seconds")

            # Display logs
            self._display_logs()

            # If the total duration has elapsed, consider scraping completed
            if elapsed >= self.duration:
                st.success("Scraping completed!")
                self._stop_scraping("Duration reached, scraping completed.")

    def _start_scraping(self) -> None:
        """
        Start the scraping process in a subprocess and set the session state variables.
        """
        st.session_state["scraping_started"] = True
        st.session_state["scraping_start_time"] = time.time()
        st.session_state["scraping_process"] = subprocess.Popen(SCRAPER_COMMAND)

    def _stop_scraping(self, reason: str) -> None:
        """
        Stop the scraping process if running and reset session state.

        Args:
            reason (str): A message indicating why the scraping was stopped.
        """
        if st.session_state["scraping_process"] and st.session_state["scraping_process"].poll() is None:
            st.session_state["scraping_process"].terminate()
            st.session_state["scraping_process"].wait()
        st.session_state["scraping_started"] = False
        if "error" in reason.lower():
            st.session_state["scraping_error"] = True
        else:
            # If it's a normal stop (e.g., manual or duration reached), no error state needed
            st.session_state["scraping_error"] = False
        st.warning(reason)

    def _get_most_recent_log_file(self) -> Optional[str]:
        """
        Get the most recent log file from the logs directory.

        Returns:
            Optional[str]: The path to the most recent log file, or None if no files found.
        """
        if not os.path.isdir(self.logs_dir):
            return None
        log_files = glob.glob(os.path.join(self.logs_dir, "*.txt"))
        if not log_files:
            return None
        log_files.sort(key=os.path.getmtime, reverse=True)
        return log_files[0]

    def _load_logs(self, log_file_path: str) -> List[str]:
        """
        Load logs from a given file path.

        Args:
            log_file_path (str): The path to the log file.

        Returns:
            List[str]: List of log lines.
        """
        if not os.path.exists(log_file_path):
            return []
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return lines

    def _format_log_line(self, line: str) -> str:
        """
        Format a single log line with color coding based on the log level.

        Args:
            line (str): A single log line.

        Returns:
            str: HTML-formatted line.
        """
        if " - INFO - " in line:
            return f"<p style='color: #0066cc;'>{line.strip()}</p>"
        elif " - WARNING - " in line:
            return f"<p style='color: #ff9900;'>{line.strip()}</p>"
        elif " - ERROR - " in line:
            return f"<p style='color: #cc0000;'>{line.strip()}</p>"
        else:
            return f"<p style='color: #666;'>{line.strip()}</p>"

    def _display_logs(self) -> None:
        """
        Display the logs in the main area. If an error is found, stop the scraping.
        """
        most_recent_log = self._get_most_recent_log_file()
        if most_recent_log is None:
            st.info("No log files found yet. Please wait.")
            return

        lines = self._load_logs(most_recent_log)
        if not lines:
            st.info("Log file exists but is empty. Please wait.")
            return

        # Check for error lines
        error_found = any(" - ERROR - " in line for line in lines)
        if error_found:
            self._stop_scraping("Scraping stopped due to an ERROR in logs.")
            return

        # Limit the number of displayed lines
        max_lines = 500
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        formatted_lines = [self._format_log_line(line) for line in lines]
        st.markdown("<br>".join(formatted_lines), unsafe_allow_html=True)
        st.write(f"Displayed {len(lines)} lines from file: {most_recent_log}")
        st.write(f"Last updated at {time.strftime('%Y-%m-%d %H:%M:%S')}.")
        
        
def main(duration: int) -> None:
    """
    Main entry point to run the Streamlit UI.
    """
    ui = ScraperUI(duration=duration)
    ui.run()