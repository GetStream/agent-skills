#!/usr/bin/env python3
"""Fetch a v2 app's activity and reaction samples for v2->v3 mapping analysis.

Calls the two server-side-only migration sample endpoints and writes both
responses to one JSON file:

    GET {base}/api/v1.0/migration/sample/activities   -> last 100 activities
    GET {base}/api/v1.0/migration/sample/reactions    -> 5 reactions per kind

Auth is a Stream server-side JWT: HS256 over {"resource":"*","action":"*",
"feed_id":"*"} signed with the app secret. A user token (one carrying only
user_id) is rejected by these endpoints by design.

Only the standard library is used, so this runs anywhere Python 3 does.

Usage:
    fetch_sample.py [--out PATH] [--base-url URL]

Credentials come from the STREAM_API_KEY and STREAM_API_SECRET environment
variables, which keeps the secret out of the process list and the shell
history. Both can be overridden with --api-key / --secret when that is not
practical.

Targets production by default. Pass --base-url for any other deployment
(EU, dedicated).
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://api.stream-io-api.com"

TIMEOUT_SECONDS = 60


def b64url(raw: bytes) -> str:
    """Base64url-encode without padding, as JWT requires."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def server_side_token(secret: str) -> str:
    """Mint a Stream server-side JWT.

    The wildcard resource/action/feed_id claims are what make this a
    server-side token rather than a user token; a token carrying *only* a
    user_id is treated as client-side and refused by these endpoints.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"resource": "*", "action": "*", "feed_id": "*"}

    # Compact separators matter: any extra whitespace changes the signed bytes.
    signing_input = "{}.{}".format(
        b64url(json.dumps(header, separators=(",", ":")).encode()),
        b64url(json.dumps(payload, separators=(",", ":")).encode()),
    )
    signature = hmac.new(
        secret.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    return "{}.{}".format(signing_input, b64url(signature))


def get(base_url: str, path: str, api_key: str, token: str) -> dict:
    url = "{}{}?api_key={}".format(base_url.rstrip("/"), path, api_key)
    request = urllib.request.Request(url, method="GET")
    request.add_header("Authorization", token)
    request.add_header("Stream-Auth-Type", "jwt")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as err:
        body = err.read().decode(errors="replace")
        raise SystemExit(
            "{} failed: HTTP {}\n{}\n\n"
            "403/401 here usually means the secret is wrong, or the token was "
            "built as a user token. 404 means this deployment predates the "
            "migration sample endpoints.".format(path, err.code, body)
        )
    except urllib.error.URLError as err:
        raise SystemExit("{} failed: could not reach {} ({})".format(path, base_url, err.reason))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-key",
        default=os.environ.get("STREAM_API_KEY"),
        help="Stream app API key (defaults to $STREAM_API_KEY)",
    )
    parser.add_argument(
        "--secret",
        default=os.environ.get("STREAM_API_SECRET"),
        help="Stream app secret (defaults to $STREAM_API_SECRET)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="API base URL (default: {})".format(DEFAULT_BASE_URL),
    )
    parser.add_argument("--out", default="v3sync-sample.json", help="output file path")
    args = parser.parse_args()

    if not args.api_key:
        parser.error("--api-key is required (or set STREAM_API_KEY)")
    if not args.secret:
        parser.error("--secret is required (or set STREAM_API_SECRET)")

    if args.base_url is None:
        args.base_url = DEFAULT_BASE_URL

    token = server_side_token(args.secret)

    activities = get(args.base_url, "/api/v1.0/migration/sample/activities", args.api_key, token)
    reactions = get(args.base_url, "/api/v1.0/migration/sample/reactions", args.api_key, token)

    sample = {
        "api_key": args.api_key,
        "base_url": args.base_url,
        "activities": activities.get("activities", []),
        "activity_count": activities.get("count", 0),
        "reactions": reactions.get("reactions", {}),
        "kinds": reactions.get("kinds", []),
        "reaction_count": reactions.get("count", 0),
    }

    with open(args.out, "w") as handle:
        json.dump(sample, handle, indent=2, sort_keys=True)

    # Everything on stdout is safe to show the user; the secret never appears
    # in the output file or in this summary.
    print("wrote {}".format(args.out))
    print("activities: {}".format(sample["activity_count"]))
    print("reaction kinds: {}".format(", ".join(sample["kinds"]) or "(none)"))
    print("reactions: {}".format(sample["reaction_count"]))

    if sample["activity_count"] == 0:
        print("\nWARNING: no activities returned - the app may be empty, or its "
              "activity store may not support the sample scan.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
