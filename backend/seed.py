"""Create a sample workspace using the same entry point as a judge."""
import sys

import httpx

if __name__ == "__main__":
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
    with httpx.Client(base_url=base) as client:
        response = client.post("/api/demo")
        response.raise_for_status()
        print(f"Created sample workspace {response.json()['workspace_id']}. "
              "The browser creates its own workspace through Try Live Demo.")
