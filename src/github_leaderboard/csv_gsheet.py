import argparse
from argparse import ArgumentDefaultsHelpFormatter
from pathlib import Path

import gspread
import pandas as pd


def main():
    parser = argparse.ArgumentParser(
        description="Upload leaderboard CSV to Google Sheets.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-t', "--token-file",
        default=".google_token.json",
        type=Path,
        help="Service account credentials JSON",
        )
    parser.add_argument(
        "-i", "--input",
        default="leaderboard.csv",
        type=Path,
        help="Input CSV file",
        )
    parser.add_argument(
        '-s', "--sheet",
        default="github-leaderboard",
        help="Google Sheet name",
        )
    ns = parser.parse_args()

    # 1. Authorize
    gc = gspread.service_account(filename=ns.token_file)

    # 2. Open the Sheet
    try:
        sh = gc.open(ns.sheet)
    except gspread.exceptions.SpreadsheetNotFound:
        available = [s.title for s in gc.openall()]
        if available:
            print(f"Sheet {ns.sheet!r} not found. Available sheets:\n  " + "\n  ".join(available))
        else:
            print(f"Sheet {ns.sheet!r} not found. No sheets are accessible with this service account.")
        return
    worksheet = sh.get_worksheet(0)

    # 3. Load your CSV
    df = pd.read_csv(ns.input)

    # 4. Overwrite the Sheet
    worksheet.clear()
    worksheet.update([df.columns.tolist()] + df.values.tolist())

    print("Dashboard data updated successfully!")


if __name__ == "__main__":
    main()
