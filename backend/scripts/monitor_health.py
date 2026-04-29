import requests
import datetime
import time
import os

LOG_FILE = "/Users/mengzh/Desktop/vue-map/backend/logs/health_check.log"
BACKEND_URL = os.getenv("VITE_API_BASE_URL", "http://127.0.0.1:9988") + "/api/health"

def log_message(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def check_health():
    try:
        response = requests.get(BACKEND_URL, timeout=5)
        if response.status_code == 200 and response.json().get("status") == "ok":
            log_message(f"Backend health check SUCCESS: {BACKEND_URL} returned 200 OK.")
            return True
        else:
            log_message(f"Backend health check FAILED: {BACKEND_URL} returned {response.status_code} with response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        log_message(f"Backend health check FAILED: Could not connect to {BACKEND_URL}. Is the service running?")
        return False
    except requests.exceptions.Timeout:
        log_message(f"Backend health check FAILED: Request to {BACKEND_URL} timed out.")
        return False
    except Exception as e:
        log_message(f"Backend health check FAILED: An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    # Ensure log directory exists
    log_dir = os.path.dirname(LOG_FILE)
    os.makedirs(log_dir, exist_ok=True)
    
    log_message("Starting backend health monitoring...")
    # For demonstration, run once. In a real scenario, this would be in a loop.
    check_health()
    log_message("Health monitoring finished.")
