"""Read installed local tags and verify OLLAMA_MODEL without generating text."""
import json
import os
from urllib.request import Request, urlopen


def main():
    base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "qwen3.5:9b")
    with urlopen(base + "/api/tags", timeout=10) as response:
        tags = json.load(response)["models"]
    for tag in tags:
        print(f"{tag['name']}  {tag['digest']}")
    if model not in {tag["name"] for tag in tags}:
        raise SystemExit(f"Selected tag is not installed: {model}")
    request = Request(base + "/api/show", data=json.dumps({"model": model}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=10) as response:
        info = json.load(response)
    print(f"PASS: selected model {model}; details={info.get('details', {})}")
    print("Metadata only; inference and parser conformance have not been tested.")


if __name__ == "__main__":
    main()
