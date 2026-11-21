"""Берёт официальный курс НБРК (CNY, USD, EUR) и пишет rates.json.
Если сайт Нацбанка недоступен, берёт рыночный курс open.er-api.com и помечает источник."""
import json, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

ALMATY = timezone(timedelta(hours=5))
now = datetime.now(ALMATY)
HDR = {"User-Agent": "Mozilla/5.0 (pdd-calc rates bot)"}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30) as r:
        return r.read()

def nbrk():
    # курс на завтра публикуется после 17:00 — берём самую свежую из сегодня/завтра.
    # НБРК иногда отдаёт XML с другой датой внутри — такой ответ пропускаем.
    for d in (now + timedelta(days=1), now, now - timedelta(days=1)):
        try:
            root = ET.fromstring(get(f"https://nationalbank.kz/rss/get_rates.cfm?fdate={d:%d.%m.%Y}"))
        except Exception as e:
            print("NBRK error", d.date(), e)
            continue
        got = (root.findtext("date") or "").strip()
        if got and got != f"{d:%d.%m.%Y}":
            print("NBRK date mismatch", d.date(), got)
            continue
        out = {}
        for it in root.iter("item"):
            code = (it.findtext("title") or "").strip()
            if code in ("CNY", "USD", "EUR"):
                q = float(it.findtext("quant") or 1)
                out[code] = round(float(it.findtext("description")) / q, 2)
        if len(out) == 3:
            return {"date": root.findtext("date") or f"{d:%d.%m.%Y}", "source": "НБРК", **out}
    return None

def market():
    data = json.loads(get("https://open.er-api.com/v6/latest/KZT"))
    r = data["rates"]
    return {"date": f"{now:%d.%m.%Y}", "source": "рыночный (НБРК недоступен)",
            **{c: round(1 / r[c], 2) for c in ("CNY", "USD", "EUR")}}

res = nbrk() or market()
res["updated"] = now.isoformat(timespec="minutes")
with open("rates.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print(res)
