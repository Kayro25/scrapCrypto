import requests
import json
import re
from datetime import datetime, date

# ==============================
# CONFIG
# ==============================

API_URL = "https://graphigo.prd.galaxy.eco/query"

HEADERS = {
    "content-type": "application/json",
    "origin": "https://app.galxe.com",
    "referer": "https://app.galxe.com/",
    "platform": "web",
    "user-agent": "Mozilla/5.0"
}

TELEGRAM_TOKEN = "SEU_TOKEN_AQUI"
TELEGRAM_CHAT_ID = "SEU_CHAT_ID"

QUERY = """
query CampaignList($input: ListCampaignInput!) {
  campaigns(input: $input) {
    pageInfo {
      endCursor
      hasNextPage
    }
    list {
      id
      name
      description
      rewardName
      startTime
      endTime
      chain
      space {
        name
        isVerified
      }
    }
  }
}
"""

# ==============================
# UTILS
# ==============================

def slugify_space(name):
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")

def build_galxe_url(quest):
    space_slug = slugify_space(quest["space"]["name"])
    return f"https://app.galxe.com/quest/{space_slug}/{quest['id']}"

# ==============================
# TELEGRAM BOT
# ==============================

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Erro ao enviar Telegram:", e)

# ==============================
# GALXE SCRAPER
# ==============================

def fetch_quests():
    all_campaigns = []
    after = "-1"
    seen_cursors = set()
    page = 0
    max_pages = 25

    while page < max_pages:
        page += 1

        variables = {
            "input": {
                "listType": "Newest",
                "statuses": ["Active"],
                "first": 20,
                "after": after,
                "isRecurring": False
            }
        }

        payload = {
            "operationName": "CampaignList",
            "query": QUERY,
            "variables": variables
        }

        try:
            resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print("Erro ao buscar dados:", e)
            break

        if "errors" in data:
            print("Erro na API Galxe:")
            print(json.dumps(data, indent=2))
            break

        campaigns = data["data"]["campaigns"]["list"]
        page_info = data["data"]["campaigns"]["pageInfo"]

        if not campaigns:
            break

        all_campaigns.extend(campaigns)

        end_cursor = page_info["endCursor"]
        if end_cursor in seen_cursors or not page_info["hasNextPage"]:
            break

        seen_cursors.add(end_cursor)
        after = end_cursor

    return all_campaigns

# ==============================
# SCORE ENGINE
# ==============================

BLACKLIST_SPACES = ["gems.town", "now chain", "airdrop global"]

TOP_CHAINS = ["ETHEREUM", "ARBITRUM", "OPTIMISM", "BASE", "POLYGON"]
MID_CHAINS = ["BSC", "AVALANCHE", "SOLANA"]

STRONG_REWARDS = ["usdt", "usdc", "eth", "btc"]
MID_REWARDS = ["token", "airdrop"]
WEAK_REWARDS = ["points", "nft", "whitelist"]

GOOD_TYPES = ["airdrop", "testnet", "early", "whitelist", "incentive", "reward", "points", "pre-tge"]
SOCIAL_ONLY = ["follow", "retweet", "like", "join discord", "invite", "comment"]
SCAM_WORDS = ["guaranteed", "instant reward", "100% free", "claim now", "hurry up"]

def payout_probability_score(text, verified):
    score = 0
    if verified:
        score += 2
    if any(w in text for w in ["points", "season", "pre-tge", "early access"]):
        score += 3
    if any(w in text for w in ["testnet", "beta", "incentive"]):
        score += 2
    if any(w in text for w in ["raffle", "lottery", "chance"]):
        score -= 2
    if any(w in text for w in ["nft only", "commemorative"]):
        score -= 2
    return score

def score_quest(quest):
    score = 0

    name = (quest.get("name") or "").lower()
    desc = (quest.get("description") or "").lower()
    reward = (quest.get("rewardName") or "").lower()
    chain = (quest.get("chain") or "").upper()
    verified = quest["space"].get("isVerified", False)
    space_name = quest["space"]["name"].lower()

    text = f"{name} {desc} {reward}"

    if space_name in BLACKLIST_SPACES:
        return 0

    if verified:
        score += 4
    else:
        score -= 1

    if reward:
        if any(w in reward for w in STRONG_REWARDS):
            score += 4
        elif any(w in reward for w in MID_REWARDS):
            score += 3
        elif any(w in reward for w in WEAK_REWARDS):
            score += 1
        else:
            score += 1
    else:
        score -= 2

    if chain in TOP_CHAINS:
        score += 2
    elif chain in MID_CHAINS:
        score += 1
    else:
        score -= 1

    score += min(3, sum(1 for w in GOOD_TYPES if w in text))

    if any(w in text for w in SOCIAL_ONLY) and not reward:
        score -= 4
    else:
        score -= sum(1 for w in SOCIAL_ONLY if w in text)

    score -= sum(2 for w in SCAM_WORDS if w in text)

    if not verified and any(w in reward for w in ["1000", "5000", "100000"]):
        score -= 4

    if not verified and not reward:
        score -= 3

    score += payout_probability_score(text, verified)

    return max(score, 0)

# ==============================
# PAYOUT CHANCE
# ==============================

def payout_chance_percent(quest):
    score = quest["score"]
    reward = (quest.get("rewardName") or "").lower()
    verified = quest["space"].get("isVerified", False)
    text = f"{quest.get('name','')} {quest.get('description','')} {reward}".lower()

    chance = min(score * 7, 70)

    if verified:
        chance += 10

    if any(w in reward for w in ["usdt", "usdc", "eth", "btc"]):
        chance += 10
    elif any(w in reward for w in ["token", "airdrop"]):
        chance += 6
    elif any(w in reward for w in ["points", "nft", "whitelist"]):
        chance += 3

    if any(w in text for w in ["pre-tge", "season", "early access", "testnet", "incentive"]):
        chance += 10

    if any(w in text for w in ["raffle", "lottery", "chance"]):
        chance -= 15

    return max(5, min(chance, 95))

# ==============================
# CLASSIFICAÇÃO
# ==============================

def classify(score):
    if score >= 10:
        return "🔥 Imperdível"
    elif score >= 8:
        return "⭐ Excelente"
    elif score >= 6:
        return "✅ Boa"
    elif score >= 4:
        return "⚠️ Mediana"
    else:
        return "❌ Ruim"

# ==============================
# EXPORT HTML
# ==============================

def export_html(quests):
    rows = ""
    for q in quests:
        rows += f"""
        <tr>
            <td>{q['score']}</td>
            <td>{classify(q['score'])}</td>
            <td><a href="{q['url']}" target="_blank">{q['name']}</a></td>
            <td>{q['space']['name']}</td>
            <td>{q['chain']}</td>
            <td>{q['rewardName'] or '-'}</td>
            <td>{q['payout_chance']}%</td>
            <td>{'✔️' if q['space']['isVerified'] else '❌'}</td>
        </tr>
        """

    html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>Ranking de Quests Galxe</title>
<style>
body {{ font-family: Arial; background: #0d1117; color: #c9d1d9; padding: 20px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #30363d; padding: 8px; text-align: left; }}
th {{ background: #161b22; }}
tr:nth-child(even) {{ background: #161b22; }}
a {{ color: #58a6ff; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
h1 {{ color: #58a6ff; }}
</style>
</head>
<body>
<h1>📊 Ranking de Quests Galxe</h1>
<p>Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
<table>
<tr>
<th>Score</th>
<th>Classificação</th>
<th>Quest</th>
<th>Projeto</th>
<th>Chain</th>
<th>Reward</th>
<th>Chance de Payout</th>
<th>Verificado</th>
</tr>
{rows}
</table>
</body>
</html>
"""

    with open("quests_ranking.html", "w", encoding="utf-8") as f:
        f.write(html)

# ==============================
# MAIN
# ==============================

def main():
    print("🔎 Buscando quests...")
    quests = fetch_quests()

    for quest in quests:
        quest["score"] = score_quest(quest)
        quest["payout_chance"] = payout_chance_percent(quest)
        quest["url"] = build_galxe_url(quest)

    filtered = [
        q for q in quests
        if q["score"] >= 6 and (q["space"]["isVerified"] or q["rewardName"])
    ]

    filtered.sort(key=lambda q: (q["score"], q["payout_chance"]), reverse=True)

    today = date.today().isoformat()

    with open("quests_filtradas.json", "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    with open(f"quests_filtradas_{today}.json", "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    export_html(filtered)

    hot_quests = [
        q for q in filtered
        if q["score"] >= 10 and q["payout_chance"] >= 70
    ]

    if hot_quests:
        for q in hot_quests:
            msg = (
                f"🔥 <b>Quest Imperdível Detectada!</b>\n\n"
                f"📌 {q['name']}\n"
                f"🏗 Projeto: {q['space']['name']}\n"
                f"🔗 Chain: {q['chain']}\n"
                f"🎁 Reward: {q['rewardName'] or '-'}\n"
                f"📊 Score: {q['score']}\n"
                f"💰 Chance de Payout: {q['payout_chance']}%\n\n"
                f"👉 {q['url']}"
            )
            send_telegram_message(msg)

    print(f"✅ {len(filtered)} quests salvas")
    print("🌐 Arquivo visual gerado: quests_ranking.html")
    if hot_quests:
        print("🚨 Alerta enviado para Telegram!")

if __name__ == "__main__":
    main()
