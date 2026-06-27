import argparse
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("historical_backfill")

def main():
    parser = argparse.ArgumentParser(description="Historical Data Backfill Script")
    parser.add_argument("--sport", type=str, required=True, help="Sport to backfill (e.g., nba, nfl)")

    args = parser.parse_args()

    if args.sport.lower() == "nfl":
        logger.info("NFL backfill is currently deferred. No NFL data will be written.")
        sys.exit(0)

    # placeholder for actual logic
    logger.info(f"Starting backfill for {args.sport}...")

if __name__ == "__main__":
    main()
