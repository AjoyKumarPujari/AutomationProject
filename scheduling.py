"""
scheduling.py
-------------
Runs pipeline.py automatically every 2 hours, forever, while this script is
running. Use this ONLY after you've run `python pipeline.py` manually a few
times and trust the output.

RUN IT
======
    python scheduling.py

Leave the terminal window open (or run it in the background -- see notes at
the bottom of this file for Windows/Mac/Linux specifics). Press Ctrl+C to
stop.
"""

import time
import traceback
from datetime import datetime

import pipeline

INTERVAL_SECONDS = 2 * 60 * 60  # 2 hours


def main():
    print("Scheduler started. Running pipeline every 2 hours. Ctrl+C to stop.\n")
    while True:
        try:
            pipeline.main()
        except Exception:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Pipeline run failed:")
            traceback.print_exc()
            print("Will retry on the next scheduled run.\n")

        next_run = datetime.now().timestamp() + INTERVAL_SECONDS
        print(f"Sleeping until {datetime.fromtimestamp(next_run):%Y-%m-%d %H:%M:%S} ...\n")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------
# NOTES ON RUNNING THIS IN THE BACKGROUND
# -----------------------------------------------------------------------
#
# Windows (Task Scheduler) -- recommended instead of leaving this running:
#   1. Open Task Scheduler -> Create Basic Task
#   2. Trigger: "Daily", repeat every 2 hours
#   3. Action: "Start a program"
#      Program: path to your python.exe
#      Arguments: pipeline.py
#      Start in: the job_pipeline folder
#   This way you don't need scheduling.py at all -- Windows handles timing.
#
# Mac/Linux (cron) -- also recommended instead of scheduling.py:
#   Run `crontab -e` and add a line like:
#     0 */2 * * * cd /path/to/job_pipeline && /usr/bin/python3 pipeline.py >> run.log 2>&1
#   This runs pipeline.py at the top of every even hour and logs output.
#
# Either OS-level option (Task Scheduler / cron) is more reliable than
# leaving scheduling.py running in a terminal, since it survives reboots
# and doesn't depend on a terminal window staying open.
