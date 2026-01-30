#!/usr/bin/env python3
"""Update CSV file with firmware versions and dates extracted from gpsinformation.net"""

import csv
from pathlib import Path

# Firmware data: product_id -> (version, date)
firmware_data = {
    # Edge devices
    4440: (2922, "2025-11-04"),  # Edge 1050
    3843: (2922, "2025-11-04"),  # Edge 1040
    4062: (2922, "2025-11-04"),  # Edge 840
    3122: (975, "2023-03-22"),  # Edge 830
    4061: (2922, "2025-11-04"),  # Edge 540
    3121: (975, "2023-03-22"),  # Edge 530
    4633: (2922, "2025-11-04"),  # Edge 550
    4634: (2922, "2025-11-04"),  # Edge 850
    3570: (675, "2023-03-22"),  # Edge 1030 Plus
    2713: (1375, "2023-03-22"),  # Edge 1030
    3558: (300, "2023-01-19"),  # Edge 130 Plus
    # Fenix devices
    4536: (2029, "2026-01-14"),  # Fenix 8 47mm
    4631: (2029, "2026-01-14"),  # Fenix 8 Pro
    3906: (2511, "2026-01-21"),  # Fenix 7
    3905: (2511, "2026-01-21"),  # Fenix 7S
    3907: (2511, "2026-01-21"),  # Fenix 7X
    3943: (2511, "2026-01-21"),  # Epix Gen 2
    # Forerunner devices
    4315: (2709, "2026-01-15"),  # Forerunner 965
    4024: (2709, "2026-01-15"),  # Forerunner 955
    4257: (2709, "2026-01-15"),  # Forerunner 265 Large
    3992: (2709, "2026-01-15"),  # Forerunner 255
    3113: (1370, "2024-12-02"),  # Forerunner 945
}

csv_file = Path("FitSDK_21.188.00_device_ids.csv")

# Read the CSV file
rows = []
with open(csv_file, "r") as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 2 and row[1].strip().isdigit():
            product_id = int(row[1].strip())

            # Update if we have firmware data for this product ID
            if product_id in firmware_data:
                version, date = firmware_data[product_id]

                # Ensure row has enough columns
                while len(row) < 5:
                    row.append("")

                # Update columns 4 and 5 (0-indexed: 3 and 4)
                row[3] = str(version)
                row[4] = date

                print(f"Updated {row[0]} (ID: {product_id}): v{version}, {date}")

        rows.append(row)

# Write back to CSV
with open(csv_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print(f"\nCSV file updated: {csv_file}")
