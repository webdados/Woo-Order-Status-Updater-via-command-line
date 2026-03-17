# WooCommerce Order Status Updater

A command-line Python script that reads a CSV file of WooCommerce order IDs and updates their status via the WooCommerce REST API.

---

## Requirements

- Python 3.7 or newer
- The `requests` Python package
- WooCommerce REST API credentials (consumer key and secret)

---

## Installation

### macOS / Linux

1. **Check if Python is installed:**
   ```bash
   python3 --version
   ```
   If not installed:

   - **macOS** — download from [python.org](https://www.python.org/downloads/) or install via Homebrew:
     ```bash
     brew install python
     ```
   - **Debian / Ubuntu:**
     ```bash
     sudo apt update && sudo apt install python3 python3-pip
     ```
   - **Fedora / RHEL / CentOS:**
     ```bash
     sudo dnf install python3 python3-pip
     ```

2. **Navigate to the script folder:**
   ```bash
   cd /path/to/woo-order-updater
   ```

3. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```
   If `pip3` is not found, use:
   ```bash
   python3 -m pip install -r requirements.txt
   ```

---

### Windows

1. **Install Python:**
   Download and install from [python.org](https://www.python.org/downloads/).
   > **Important:** During installation, check **"Add Python to PATH"**.

2. **Open Command Prompt or PowerShell** and navigate to the script folder:
   ```cmd
   cd C:\path\to\woo-order-updater
   ```

3. **Install dependencies:**
   ```cmd
   pip install -r requirements.txt
   ```
   If `pip` is not found, use:
   ```cmd
   python -m pip install -r requirements.txt
   ```
   Or use the Python Launcher:
   ```cmd
   py -m pip install -r requirements.txt
   ```

---

## Configuration

Before running the script, edit `config.ini` (located in the same folder as the script):

```ini
[woocommerce]
# Your shop's base URL (no trailing slash)
shop_url = https://your-shop.com

# WooCommerce REST API credentials
consumer_key    = ck_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
consumer_secret = cs_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

[settings]
# Status to set on every order in the CSV
status_to_set   = completed

# Seconds to wait for each API response before timing out
request_timeout = 30

# Seconds to wait between retry attempts on failure
retry_delay     = 2

# Maximum number of attempts per order before marking it as failed
max_retries     = 3

# Seconds to wait between the end of one API call and the start of the next
call_delay      = 1
```

### Generating API credentials

1. Log in to your WordPress admin panel.
2. Go to **WooCommerce → Settings → Advanced → REST API**.
3. Click **Add key**.
4. Set **Permissions** to **Read/Write**.
5. Click **Generate API key** and copy the **Consumer key** and **Consumer secret** into `config.ini`.

### Configuration reference

| Key | Description |
|---|---|
| `shop_url` | Base URL of your WooCommerce store, without trailing slash |
| `consumer_key` | WooCommerce REST API consumer key (`ck_...`) |
| `consumer_secret` | WooCommerce REST API consumer secret (`cs_...`) |
| `status_to_set` | The order status to apply to every order in the CSV (e.g. `processing`, `completed`) |
| `request_timeout` | Seconds to wait for an API response before considering the request timed out |
| `retry_delay` | Seconds to wait between retry attempts when a request fails |
| `max_retries` | How many times to attempt each order before marking it as failed |
| `call_delay` | Seconds to wait between consecutive API calls (reduces server load) |

All keys are required. The script will stop with a clear error message if any key is missing or empty.

---

## Preparing the CSV file

The CSV file must have **WooCommerce order IDs in the first column**. Additional columns are ignored.

A header row is optional — it is automatically detected and skipped if the first cell is not a number.

Example:
```
order_id
1001
1002
1003
```

Or without a header:
```
1001
1002
1003
```

---

## Usage

### macOS / Linux

Run with an explicit CSV file:
```bash
python3 update_orders.py path/to/orders.csv
```

Or, if the CSV is named `orders.csv` and is in the same folder as the script, you can omit it:
```bash
python3 update_orders.py
```

### Windows

```cmd
python update_orders.py path\to\orders.csv
```

Or using the Python Launcher:
```cmd
py update_orders.py path\to\orders.csv
```

If the CSV is named `orders.csv` and sits next to the script, the argument can be omitted:
```cmd
python update_orders.py
```

---

## Output

The script prints a line for each order, then a summary:

```
[INFO] Shop            : https://your-shop.com
[INFO] Orders to update: 3
[INFO] Target status   : completed
------------------------------------------------------------
  [OK]   Order 1001  →  completed
  [OK]   Order 1002  →  completed
  [FAIL] Order 1003  –  HTTP 404: {"code":"woocommerce_rest_shop_order_invalid_id"...}
------------------------------------------------------------
[DONE] Success: 2   Failed: 1
```

| Prefix | Meaning |
|---|---|
| `[INFO]` | General information |
| `[OK]` | Order updated successfully |
| `[FAIL]` | Order could not be updated (HTTP error or network error shown) |
| `[WARN]` | Non-critical issue, e.g. a skipped non-numeric row in the CSV, or a retry attempt |

---

## Troubleshooting

**`command not found: pip`** — Use `pip3` or `python3 -m pip` instead.

**`command not found: python`** — Use `python3` on macOS/Linux, or ensure Python is added to PATH on Windows.

**`[ERROR] config.ini still contains placeholder values`** — You haven't replaced the example `shop_url` or `consumer_key` in `config.ini`.

**`[ERROR] Missing key in [...] section of config.ini`** — A required setting is absent or the section header is missing from `config.ini`.

**`HTTP 401`** — Invalid API credentials. Double-check the consumer key and secret.

**`HTTP 404`** — The order ID does not exist in WooCommerce.

**`Request error: ... timed out`** — The server did not respond in time. Try increasing `request_timeout` in `config.ini`.

---

## Disclaimer

These instructions were written with the assistance of an AI language model. While every effort has been made to ensure accuracy, you should verify the steps against the official documentation for your specific operating system and Python version.
