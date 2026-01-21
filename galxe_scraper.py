import requests
import json
import re
import os
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

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ENABLE_BOT = BOT_TOKEN and CHAT_ID

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

def notify_telegram(message):
    if not ENABLE_BOT:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

# ==============================
# FETCH QUESTS
# ==============================

def fetch_quests():
    all_campaigns = []
    after = "-1"
    seen_cursors = set()
    max_pages = 10

    for _ in range(max_pages):
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

        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=20)
        data = resp.json()

        campaigns = data["data"]["campaigns"]["list"]
        page_info = data["data"]["campaigns"]["pageInfo"]

        if not campaigns:
            break

        all_campaigns.extend(campaigns)

        end_cursor = page_info["endCursor"]
        if not page_info["hasNextPage"] or end_cursor in seen_cursors:
            break

        seen_cursors.add(end_cursor)
        after = end_cursor

    return all_campaigns

# ==============================
# SCORE + PAYOUT
# ==============================

def calculate_payout_chance(score):
    if score >= 9:
        return 85
    elif score >= 7:
        return 65
    elif score >= 5:
        return 45
    elif score >= 3:
        return 25
    else:
        return 10

def score_quest(quest):
    score = 0

    name = (quest.get("name") or "").lower()
    desc = (quest.get("description") or "").lower()
    reward = (quest.get("rewardName") or "").lower()
    chain = (quest.get("chain") or "").upper()
    verified = quest["space"].get("isVerified", False)

    text = f"{name} {desc} {reward}"

    if verified:
        score += 4
    else:
        score -= 1

    if reward:
        score += 2
        strong_rewards = ["usdt", "usdc", "eth", "btc", "token", "airdrop", "nft"]
        if any(w in reward for w in strong_rewards):
            score += 2
    else:
        score -= 2

    top_chains = ["ETHEREUM", "ARBITRUM", "OPTIMISM", "BASE", "POLYGON"]
    mid_chains = ["BSC", "AVALANCHE", "SOLANA"]

    if chain in top_chains:
        score += 2
    elif chain in mid_chains:
        score += 1
    else:
        score -= 1

    good_types = ["airdrop", "testnet", "early", "whitelist", "reward", "points"]
    score += min(3, sum(1 for w in good_types if w in text))

    social_only = ["follow", "retweet", "like", "join discord", "invite"]
    score -= sum(1 for w in social_only if w in text)

    scam_words = ["guaranteed", "instant", "claim now", "hurry"]
    score -= sum(2 for w in scam_words if w in text)

    return max(score, 0)

# ==============================
# EXPORT HTML
# ==============================

def export_html(quests):
    rows = ""
    for q in quests:
        rows += f"""
        <tr>
            <td>{q['score']}</td>
            <td>{q['payout']}%</td>
            <td><a href="{q['url']}" target="_blank">{q['name']}</a></td>
            <td>{q['space']['name']}</td>
            <td>{q['chain']}</td>
            <td>{q['rewardName'] or '-'}</td>
            <td>{'✔️' if q['space']['isVerified'] else '❌'}</td>
        </tr>
        """

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Ranking Galxe</title>
</head>
<body>
<h1>Ranking Galxe</h1>
<table border="1">
<tr>
<th>Score</th><th>Payout</th><th>Quest</th><th>Projeto</th>
<th>Chain</th><th>Reward</th><th>Verificado</th>
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

    imperdiveis = []

    for quest in quests:
        quest["score"] = score_quest(quest)
        quest["payout"] = calculate_payout_chance(quest["score"])
        quest["url"] = build_galxe_url(quest)

        if quest["score"] >= 9:
            imperdiveis.append(quest)

    filtered = [q for q in quests if q["score"] >= 5]
    filtered.sort(key=lambda q: q["score"], reverse=True)

    today = date.today().isoformat()

    with open("quests_filtradas.json", "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    export_html(filtered)

    # ALERTA TELEGRAM
    if imperdiveis:
        for q in imperdiveis:
            msg = (
                f"🔥 <b>Quest Imperdível!</b>\n"
                f"<b>{q['name']}</b>\n"
                f"🎁 {q['rewardName'] or 'Sem reward claro'}\n"
                f"📊 Score: {q['score']} | Payout: {q['payout']}%\n"
                f"🔗 {q['url']}"
            )
            notify_telegram(msg)

    print(f"✅ {len(filtered)} quests salvas")
    print("🌐 quests_ranking.html gerado")

if __name__ == "__main__":
    main()
