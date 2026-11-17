"""Read daily aggregate calculator counts from the private report endpoint."""
import argparse
import json
import os
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--from", dest="start", required=True)
parser.add_argument("--to", dest="end", required=True)
parser.add_argument("--endpoint", required=True)
args = parser.parse_args()
if urllib.parse.urlsplit(args.endpoint).scheme != "https":
    raise SystemExit("The report endpoint must use HTTPS")
token = os.environ.get("CALCULATOR_USAGE_REPORT_TOKEN")
if not token:
    raise SystemExit("Set CALCULATOR_USAGE_REPORT_TOKEN to read the report")
request = urllib.request.Request(args.endpoint + "?" + urllib.parse.urlencode({"from": args.start, "to": args.end}),
                                 headers={"Authorization": "Bearer " + token})
with urllib.request.urlopen(request, timeout=30) as response:
    print(json.dumps(json.load(response), indent=2))
