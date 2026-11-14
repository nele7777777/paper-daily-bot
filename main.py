import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. 在这里填入你的研究方向关键词（支持 AND / OR）
SEARCH_QUERY = '(all:"dexterous manipulation" OR all:"retargeting" OR all:"humanoid") AND cat:cs.RO'
MAX_RESULTS = 5  # 每次抓取最新几篇

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

def fetch_arxiv():
    query = urllib.parse.quote(SEARCH_QUERY)
    url = f"http://export.arxiv.org/api/query?search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results={MAX_RESULTS}"
    xml_data = urllib.request.urlopen(url).read()
    root = ET.fromstring(xml_data)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    
    papers = []
    for entry in root.findall("atom:entry", ns):
        papers.append({
            "title": entry.find("atom:title", ns).text.strip().replace("\n", " "),
            "abstract": entry.find("atom:summary", ns).text.strip().replace("\n", " "),
            "url": entry.find("atom:id", ns).text.strip()
        })
    return papers

def summarize_and_translate(title, abstract):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""请阅读以下英文论文标题和摘要，用简洁专业的中文输出：
1. 【中文标题】准确翻译标题
2. 【核心问题】一句话说明解决了什么痛点
3. 【方法亮点】2-3条精炼总结核心技术方案
4. 【相关性评分】1-5星（评估与机器人灵巧操作/动作重定向的契合度）

英文标题：{title}
英文摘要：{abstract}"""

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res["candidates"][0]["content"]["parts"][0]["text"]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req)

if __name__ == "__main__":
    papers = fetch_arxiv()
    if not papers:
        send_telegram("今日暂无匹配的新论文。")
    else:
        send_telegram(f"📚 今日 arXiv 精选论文日报（{datetime.now().strftime('%Y-%m-%d')}），共 {len(papers)} 篇：")
        for idx, p in enumerate(papers, 1):
            ai_summary = summarize_and_translate(p["title"], p["abstract"])
            msg = f"【{idx}/{len(papers)}】{p['title']}\n\n{ai_summary}\n\n🔗 原文链接：{p['url']}"
            send_telegram(msg)
