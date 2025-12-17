import json, urllib.request
pkgs = ['"'"'starlette'"'"','"'"'python-multipart'"'"','"'"'python-jose'"'"','"'"'ecdsa'"'"','"'"'requests'"'"']
for name in pkgs:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json") as resp:
        data = json.load(resp)
    print(f"{name} {data['"'"'info'"'"']['"'"'version'"'"']}")
