"""
Номер справки = номер заявки, начиная с 37, автоинкремент.
Значение хранится в counter.json в этом же GitHub-репозитории — обновляется
через GitHub Contents API, чтобы не зависеть от файловой системы Render
(она сбрасывается при каждом холодном старте бесплатного тарифа).

Требует переменную окружения GITHUB_TOKEN — fine-grained PAT с правом
Contents: Read and write только на этот репозиторий.
"""

import base64
import json
import os
from urllib import request

GITHUB_REPO = "AleksandrSorokinvl/yeti-ndfl-api"
GITHUB_COUNTER_PATH = "counter.json"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_COUNTER_PATH}"


def next_cert_number() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        return ""

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    try:
        get_req = request.Request(GITHUB_API_URL, headers=headers)
        with request.urlopen(get_req, timeout=10) as resp:
            file_data = json.loads(resp.read())

        current = json.loads(base64.b64decode(file_data["content"]))
        value = int(current["next"])

        new_content = json.dumps({"next": value + 1}).encode("utf-8")
        put_body = json.dumps({
            "message": f"cert number {value} issued",
            "content": base64.b64encode(new_content).decode("ascii"),
            "sha": file_data["sha"],
        }).encode("utf-8")
        put_req = request.Request(
            GITHUB_API_URL,
            data=put_body,
            method="PUT",
            headers={**headers, "Content-Type": "application/json"},
        )
        request.urlopen(put_req, timeout=10)

        return str(value)
    except Exception:
        return ""
