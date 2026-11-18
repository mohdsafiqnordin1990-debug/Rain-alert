"""Rain/flood alert checker.
Fetches official warnings, finds new ones, sends them to an FCM topic.
No FCM credentials set = dry run (just prints), so you can test first.
"""
import hashlib, json, os, pathlib, requests

SOURCES = {
    "MET Malaysia": "https://api.data.gov.my/weather/warning?limit=50",
    "JPS flood": "https://api.data.gov.my/flood-warning?limit=50",
}
SEEN_FILE = pathlib.Path("seen.json")
TOPIC = "all_warnings"


def fetch(url):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        print("fetch failed:", url, e)
        return []


def record_id(rec):
    raw = json.dumps(rec, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode()).hexdigest()


def send(source, rec):
    title = f"Amaran / Alert ({source})"
    body = json.dumps(rec, ensure_ascii=False)[:180]  # TODO: map real fields
    if not os.environ.get("FIREBASE_CREDENTIALS"):
        print("DRY RUN:", title, body)
        return
    import firebase_admin
    from firebase_admin import credentials, messaging

    if not firebase_admin._apps:
        cred = credentials.Certificate(json.loads(os.environ["FIREBASE_CREDENTIALS"]))
        firebase_admin.initialize_app(cred)
    messaging.send(
        messaging.Message(
            topic=TOPIC,
            notification=messaging.Notification(title=title, body=body),
        )
    )


def main():
    seen = set(json.loads(SEEN_FILE.read_text())) if SEEN_FILE.exists() else set()
    for source, url in SOURCES.items():
        for rec in fetch(url):
            rid = record_id(rec)
            if rid not in seen:
                send(source, rec)
                seen.add(rid)
    SEEN_FILE.write_text(json.dumps(sorted(seen)))


if __name__ == "__main__":
    main()
