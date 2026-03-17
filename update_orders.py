#!/usr/bin/env python3
"""
update_orders.py – Update WooCommerce order statuses via the REST API.

Usage:
    python update_orders.py <path/to/orders.csv>

The CSV must have two columns: the first is the WooCommerce order ID and the
second is the target status to set for that order.
A header row is auto-detected and skipped when present.
The column delimiter is detected automatically (comma, semicolon, tab, or pipe).

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

    try:
        s = cfg["settings"]
        request_timeout = int(s["request_timeout"])
        retry_delay     = int(s["retry_delay"])
        max_retries     = int(s["max_retries"])
        call_delay      = int(s["call_delay"])
    except KeyError as exc:
        sys.exit(f"[ERROR] Missing key in [settings] section of config.ini: {exc}")
    except ValueError as exc:
        sys.exit(f"[ERROR] Invalid value in [settings] section of config.ini: {exc}")

    return shop_url, consumer_key, consumer_secret, request_timeout, retry_delay, max_retries, call_delay


# ---------------------------------------------------------------------------
# CSV reading
# ---------------------------------------------------------------------------

def read_orders(csv_path):
    """Return a list of (order_id, status) tuples from a CSV file.

    The first column must contain WooCommerce order IDs and the second column
    must contain the target status. A header row is auto-detected and skipped
    when the first cell is non-numeric. The column delimiter is detected
    automatically (comma, semicolon, tab, or pipe).
    """
    orders = []
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel  # fall back to comma-separated
        reader = csv.reader(fh, dialect)
        for line_num, row in enumerate(reader, start=1):
            if not row:
                continue
            order_id = row[0].strip()
            # Auto-skip a header row when the first cell is non-numeric
            if line_num == 1 and not order_id.lstrip("-").isdigit():
                print(f"[INFO] Skipping header row: {row}")
                continue
            if not order_id.lstrip("-").isdigit():
                print(f"[WARN] Line {line_num}: skipping non-numeric order ID '{order_id}'")
                continue
            if len(row) < 2 or not row[1].strip():
                print(f"[WARN] Line {line_num}: skipping order {order_id} – missing status in second column")
                continue
            status = row[1].strip()
            orders.append((order_id, status))
    return orders


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

    shop_url, consumer_key, consumer_secret, request_timeout, retry_delay, max_retries, call_delay = load_config()

    orders = read_orders(csv_path)
    if not orders:
        sys.exit("[ERROR] No valid orders found in the CSV file.")

    print(f"[INFO] Shop            : {shop_url}")
    print(f"[INFO] Orders to update: {len(orders)}")
    print("-" * 60)

    session = requests.Session()
    session.auth = HTTPBasicAuth(consumer_key, consumer_secret)
    session.headers.update({"Content-Type": "application/json"})

    success_count = 0
    failure_count = 0

    for i, (order_id, status) in enumerate(orders):
        try:
            resp = update_order(session, shop_url, order_id, status, request_timeout, retry_delay, max_retries)
            if resp.status_code == 200:
                print(f"  [OK]   Order {order_id}  →  {status}")
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

        if call_delay > 0 and i < len(orders) - 1:
            time.sleep(call_delay)

    print("-" * 60)
    print(f"[DONE] Success: {success_count}   Failed: {failure_count}")


if __name__ == "__main__":
    main()
