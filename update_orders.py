#!/usr/bin/env python3
"""
update_orders.py – Update WooCommerce order statuses via the REST API.

Usage:
    python update_orders.py <path/to/orders.csv>

The CSV must have WooCommerce order IDs in its first column.
A header row is auto-detected and skipped when present.

Configuration is read from config.ini located in the same directory as this script.
"""

import csv
import sys
import os
import configparser
import time

try:
    import requests
    from requests.auth import HTTPBasicAuth
except ImportError:
    sys.exit(
        "[ERROR] The 'requests' library is not installed.\n"
        "        Run:  pip install requests"
    )

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.ini")

def load_config():
    """Read all configuration from config.ini."""
    if not os.path.isfile(CONFIG_PATH):
        sys.exit(f"[ERROR] Config file not found: {CONFIG_PATH}")

    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH, encoding="utf-8")

    try:
        wc = cfg["woocommerce"]
        shop_url        = wc["shop_url"].rstrip("/")
        consumer_key    = wc["consumer_key"].strip()
        consumer_secret = wc["consumer_secret"].strip()
    except KeyError as exc:
        sys.exit(f"[ERROR] Missing key in [woocommerce] section of config.ini: {exc}")

    if "your-shop.com" in shop_url or consumer_key.startswith("ck_xxx"):
        sys.exit(
            "[ERROR] config.ini still contains placeholder values.\n"
            f"        Please edit: {CONFIG_PATH}"
        )

    try:
        s = cfg["settings"]
        status_to_set   = s["status_to_set"].strip()
        if not status_to_set:
            sys.exit("[ERROR] 'status_to_set' is empty in [settings] section of config.ini")
        request_timeout = int(s["request_timeout"])
        retry_delay     = int(s["retry_delay"])
        max_retries     = int(s["max_retries"])
        call_delay      = int(s["call_delay"])
    except KeyError as exc:
        sys.exit(f"[ERROR] Missing key in [settings] section of config.ini: {exc}")
    except ValueError as exc:
        sys.exit(f"[ERROR] Invalid value in [settings] section of config.ini: {exc}")

    return shop_url, consumer_key, consumer_secret, status_to_set, request_timeout, retry_delay, max_retries, call_delay


# ---------------------------------------------------------------------------
# CSV reading
# ---------------------------------------------------------------------------

def read_order_ids(csv_path):
    """Return a list of order ID strings from the first column of a CSV file."""
    ids = []
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        for line_num, row in enumerate(reader, start=1):
            if not row:
                continue
            value = row[0].strip()
            # Auto-skip a header row when the first cell is non-numeric
            if line_num == 1 and not value.lstrip("-").isdigit():
                print(f"[INFO] Skipping header row: {row}")
                continue
            if not value.lstrip("-").isdigit():
                print(f"[WARN] Line {line_num}: skipping non-numeric value '{value}'")
                continue
            ids.append(value)
    return ids


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def update_order(session, base_url, order_id, status_to_set, request_timeout, retry_delay, max_retries):
    """PUT /wp-json/wc/v3/orders/<id> with the configured status, with retries."""
    url     = f"{base_url}/wp-json/wc/v3/orders/{order_id}"
    payload = {"status": status_to_set}

    for attempt in range(1, max_retries + 1):
        try:
            resp = session.put(url, json=payload, timeout=request_timeout)
            return resp
        except requests.exceptions.RequestException as exc:
            if attempt < max_retries:
                print(
                    f"  [WARN] Order {order_id} – attempt {attempt} failed "
                    f"({exc}). Retrying in {retry_delay}s…"
                )
                time.sleep(retry_delay)
            else:
                raise


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) >= 2:
        csv_path = sys.argv[1]
    else:
        csv_path = os.path.join(SCRIPT_DIR, "orders.csv")
        print(f"[INFO] No CSV specified – defaulting to: {csv_path}")

    if not os.path.isfile(csv_path):
        sys.exit(f"[ERROR] CSV file not found: {csv_path}")

    shop_url, consumer_key, consumer_secret, status_to_set, request_timeout, retry_delay, max_retries, call_delay = load_config()

    order_ids = read_order_ids(csv_path)
    if not order_ids:
        sys.exit("[ERROR] No valid order IDs found in the CSV file.")

    print(f"[INFO] Shop            : {shop_url}")
    print(f"[INFO] Orders to update: {len(order_ids)}")
    print(f"[INFO] Target status   : {status_to_set}")
    print("-" * 60)

    session = requests.Session()
    session.auth = HTTPBasicAuth(consumer_key, consumer_secret)
    session.headers.update({"Content-Type": "application/json"})

    success_count = 0
    failure_count = 0

    for i, order_id in enumerate(order_ids):
        try:
            resp = update_order(session, shop_url, order_id, status_to_set, request_timeout, retry_delay, max_retries)
            if resp.status_code == 200:
                print(f"  [OK]   Order {order_id}  →  {status_to_set}")
                success_count += 1
            else:
                # Show a trimmed snippet of the error body for diagnostics
                snippet = resp.text[:200].replace("\n", " ")
                print(
                    f"  [FAIL] Order {order_id}  –  HTTP {resp.status_code}: "
                    f"{snippet}"
                )
                failure_count += 1
        except requests.exceptions.RequestException as exc:
            print(f"  [FAIL] Order {order_id}  –  Request error: {exc}")
            failure_count += 1

        if call_delay > 0 and i < len(order_ids) - 1:
            time.sleep(call_delay)

    print("-" * 60)
    print(f"[DONE] Success: {success_count}   Failed: {failure_count}")


if __name__ == "__main__":
    main()
