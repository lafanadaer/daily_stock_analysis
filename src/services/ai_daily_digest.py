# -*- coding: utf-8 -*-
"""
===================================
AI Daily Digest 每日技术资讯摘要服务
===================================

职责：
1. 并发抓取指定的 Hacker News 顶级技术博客 RSS 源
2. 调用配置的 LLM 模型对文章进行多维度评分和分类
3. 对高分文章进行摘要提炼和翻译
4. 生成 Markdown 格式的精选日报
"""

import concurrent.futures
import json
import logging
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

import litellm
from src.config import get_config

logger = logging.getLogger(__name__)

# 预设的 90 个精选 RSS 源 (部分示例，可全量补充)
RSS_FEEDS = [
    {"name": "simonwillison.net", "xmlUrl": "https://simonwillison.net/atom/everything/", "htmlUrl": "https://simonwillison.net"},
    {"name": "jeffgeerling.com", "xmlUrl": "https://www.jeffgeerling.com/blog.xml", "htmlUrl": "https://jeffgeerling.com"},
    {"name": "krebsonsecurity.com", "xmlUrl": "https://krebsonsecurity.com/feed/", "htmlUrl": "https://krebsonsecurity.com"},
    {"name": "daringfireball.net", "xmlUrl": "https://daringfireball.net/feeds/main", "htmlUrl": "https://daringfireball.net"},
    {"name": "antirez.com", "xmlUrl": "http://antirez.com/rss", "htmlUrl": "http://antirez.com"},
    {"name": "pluralistic.net", "xmlUrl": "https://pluralistic.net/feed/", "htmlUrl": "https://pluralistic.net"},
    {"name": "mitchellh.com", "xmlUrl": "https://mitchellh.com/feed.xml", "htmlUrl": "https://mitchellh.com"},
    {"name": "overreacted.io", "xmlUrl": "https://overreacted.io/rss.xml", "htmlUrl": "https://overreacted.io"},
    {"name": "paulgraham.com", "xmlUrl": "http://www.aaronsw.com/2002/feeds/pgessays.rss", "htmlUrl": "https://paulgraham.com"},
    {"name": "eli.thegreenplace.net", "xmlUrl": "https://eli.thegreenplace.net/feeds/all.atom.xml", "htmlUrl": "https://eli.thegreenplace.net"},
    {"name": "gwern.net", "xmlUrl": "https://gwern.substack.com/feed", "htmlUrl": "https://gwern.net"},
    {"name": "steveblank.com", "xmlUrl": "https://steveblank.com/feed/", "htmlUrl": "https://steveblank.com"},
    {"name": "troyhunt.com", "xmlUrl": "https://www.troyhunt.com/rss/", "htmlUrl": "https://troyhunt.com"},
    {"name": "experimental-history.com", "xmlUrl": "https://www.experimental-history.com/feed", "htmlUrl": "https://experimental-history.com"},
    {"name": "miguelgrinberg.com", "xmlUrl": "https://blog.miguelgrinberg.com/feed", "htmlUrl": "https://miguelgrinberg.com"},
]

CATEGORY_META = {
    'ai-ml': {'emoji': '🤖', 'label': 'AI / ML'},
    'security': {'emoji': '🔒', 'label': '安全'},
    'engineering': {'emoji': '⚙️', 'label': '工程'},
    'tools': {'emoji': '🛠', 'label': '工具 / 开源'},
    'opinion': {'emoji': '💡', 'label': '观点 / 杂谈'},
    'other': {'emoji': '📝', 'label': '其他'},
}

def strip_html(html: str) -> str:
    """去除非法字符和 HTML 标签"""
    if not html:
        return ""
    text = re.sub(r'<[^>]*>', '', html)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    return text.strip()

def extract_cdata(text: str) -> str:
    match = re.search(r'<!\[CDATA\[([\s\S]*?)\]\]>', text)
    return match.group(1) if match else text

def get_tag_content(xml: str, tag_name: str) -> str:
    patterns = [
        re.compile(fr'<{tag_name}[^>]*>([\s\S]*?)</{tag_name}>', re.IGNORECASE),
        re.compile(fr'<{tag_name}[^>]*/>', re.IGNORECASE)
    ]
    for pattern in patterns:
        match = pattern.search(xml)
        if match and match.groups():
            return strip_html(extract_cdata(match.group(1))).strip()
    return ''

def parse_date(date_str: str) -> datetime:
    try:
        from dateutil import parser
        return parser.parse(date_str)
    except Exception:
        pass
    # fallback
    try:
        return datetime.strptime(date_str[:25].strip(), "%a, %d %b %Y %H:%M:%S")
    except Exception:
        return datetime.fromtimestamp(0, tz=timezone.utc)

def parse_rss_items(xml: str) -> List[Dict[str, str]]:
    items = []
    is_atom = '<feed' in xml and 'http://www.w3.org/2005/Atom' in xml or '<feed ' in xml
    
    if is_atom:
        entries = re.findall(r'<entry[\s>]([\s\S]*?)</entry>', xml, re.IGNORECASE)
        for entry in entries:
            title = get_tag_content(entry, 'title')
            link_match = re.search(r'<link[^>]*href=["\']([^"\']*)["\'][^>]*rel=["\']alternate["\']', entry, re.IGNORECASE)
            if not link_match:
                link_match = re.search(r'<link[^>]*href=["\']([^"\']*)["\']', entry, re.IGNORECASE)
            link = link_match.group(1) if link_match else ''
            pub_date = get_tag_content(entry, 'published') or get_tag_content(entry, 'updated')
            desc = get_tag_content(entry, 'summary') or get_tag_content(entry, 'content')
            if title or link:
                items.append({'title': title, 'link': link, 'pubDate': pub_date, 'description': desc[:500]})
    else:
        elements = re.findall(r'<item[\s>]([\s\S]*?)</item>', xml, re.IGNORECASE)
        for element in elements:
            title = get_tag_content(element, 'title')
            link = get_tag_content(element, 'link') or get_tag_content(element, 'guid')
            pub_date = get_tag_content(element, 'pubDate') or get_tag_content(element, 'dc:date') or get_tag_content(element, 'date')
            desc = get_tag_content(element, 'description') or get_tag_content(element, 'content:encoded')
            if title or link:
                items.append({'title': title, 'link': link, 'pubDate': pub_date, 'description': desc[:500]})
    return items

def fetch_feed(feed: Dict[str, str], max_age_days: int) -> List[Dict[str, Any]]:
    articles = []
    try:
        req = urllib.request.Request(
            feed['xmlUrl'], 
            headers={'User-Agent': 'AI-Daily-Digest/1.0 (RSS Reader)', 'Accept': 'application/xml, text/xml, */*'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            xml = response.read().decode('utf-8', errors='ignore')
            items = parse_rss_items(xml)
            now = datetime.now(timezone.utc)
            for item in items:
                pub_date = parse_date(item['pubDate'])
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                if (now - pub_date).total_seconds() <= max_age_days * 86400:
                    articles.append({
                        'title': item['title'],
                        'link': item['link'],
                        'pubDate': pub_date,
                        'description': item['description'],
                        'sourceName': feed['name'],
                        'sourceUrl': feed['htmlUrl']
                    })
    except Exception as e:
        logger.debug(f"[AIDigest] Failed to fetch {feed['name']}: {e}")
    return articles

class AIDailyDigestService:
    def __init__(self):
        self.config = get_config()
        self.max_age_days = getattr(self.config, 'ai_daily_digest_days', 2)
        self.top_n = getattr(self.config, 'ai_daily_digest_top_n', 15)
        self.language = getattr(self.config, 'ai_daily_digest_language', 'zh')
        self.model = getattr(self.config, 'litellm_model', None)
        if not self.model:
            if getattr(self.config, 'gemini_api_key', None):
                self.model = "gemini/gemini-2.0-flash"
            elif getattr(self.config, 'deepseek_api_key', None):
                self.model = "deepseek/deepseek-chat"
            elif getattr(self.config, 'anthropic_api_key', None):
                self.model = "anthropic/claude-3-5-sonnet-20241022"
            elif getattr(self.config, 'openai_api_key', None):
                self.model = "openai/gpt-4o-mini"
            else:
                self.model = "gemini/gemini-2.0-flash"
            logger.warning(f"[AIDigest] LITELLM_MODEL is missing, fallback to {self.model}")

    def fetch_all_articles(self) -> List[Dict[str, Any]]:
        all_articles = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_feed = {executor.submit(fetch_feed, feed, self.max_age_days): feed for feed in RSS_FEEDS}
            for future in concurrent.futures.as_completed(future_to_feed):
                res = future.result()
                all_articles.extend(res)
        logger.info(f"[AIDigest] Fetched {len(all_articles)} articles in the last {self.max_age_days} days.")
        return all_articles

    def call_ai(self, prompt: str, json_format: bool = False) -> str:
        messages = [{"role": "user", "content": prompt}]
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
        }
        if json_format:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            resp = litellm.completion(**kwargs)
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"[AIDigest] LLM Call failed: {e}")
            return ""

    def score_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Batch scoring
        scored_articles = []
        batch_size = 10
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i+batch_size]
            prompt = self._build_scoring_prompt(batch)
            result_str = self.call_ai(prompt, json_format=True)
            if not result_str: continue
            try:
                # remove Markdown code blocks if any
                if result_str.startswith('```'):
                    result_str = re.sub(r'^```(json)?\n?|\n?```$', '', result_str.strip())
                parsed = json.loads(result_str)
                for res in parsed.get("results", []):
                    idx = res.get("index")
                    if idx is not None and 0 <= idx < len(batch):
                        article = batch[idx]
                        article['score'] = res.get('relevance', 5) * 5 + res.get('quality', 5) * 3 + res.get('timeliness', 5) * 2
                        article['category'] = res.get('category', 'other')
                        article['keywords'] = res.get('keywords', [])[:4]
                        scored_articles.append(article)
            except Exception as e:
                logger.error(f"[AIDigest] Scoring JSON parse error: {e}")
        return scored_articles

    def _build_scoring_prompt(self, batch: List[Dict[str, Any]]) -> str:
        articles_list = "\n\n---\n\n".join([f"Index {idx}: [{a['sourceName']}] {a['title']}\n{a['description'][:300]}" for idx, a in enumerate(batch)])
        return f"""你是一个技术内容策展人，正在为一份每日精选摘要筛选文章。
请对以下文章进行三个维度的评分（1-10），并分配分类标签（ai-ml, security, engineering, tools, opinion, other）及提取2-4个英文关键词。
## 待评分文章
{articles_list}

严格按照如下 JSON 格式返回，不要包含任何 markdown 代码块标识：
{{
  "results": [
    {{
      "index": 0,
      "relevance": 8,
      "quality": 7,
      "timeliness": 9,
      "category": "engineering",
      "keywords": ["Rust", "compiler"]
    }}
  ]
}}"""

    def summarize_top_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        articles.sort(key=lambda x: x.get('score', 0), reverse=True)
        top_articles = articles[:self.top_n]
        
        batch_size = 5
        for i in range(0, len(top_articles), batch_size):
            batch = top_articles[i:i+batch_size]
            prompt = self._build_summary_prompt(batch)
            result_str = self.call_ai(prompt, json_format=True)
            if not result_str: continue
            try:
                if result_str.startswith('```'):
                    result_str = re.sub(r'^```(json)?\n?|\n?```$', '', result_str.strip())
                parsed = json.loads(result_str)
                for res in parsed.get("results", []):
                    idx = res.get("index")
                    if idx is not None and 0 <= idx < len(batch):
                        batch[idx]['titleZh'] = res.get('titleZh', batch[idx]['title'])
                        batch[idx]['summary'] = res.get('summary', '')
                        batch[idx]['reason'] = res.get('reason', '')
            except Exception as e:
                logger.error(f"[AIDigest] Summary JSON parse error: {e}")
        return top_articles

    def _build_summary_prompt(self, batch: List[Dict[str, Any]]) -> str:
        articles_list = "\n\n---\n\n".join([f"Index {idx}: [{a['sourceName']}] {a['title']}\nURL: {a['link']}\n{a['description'][:800]}" for idx, a in enumerate(batch)])
        lang_instruction = "请用中文撰写摘要、推荐理由和中文标题翻译。" if self.language == 'zh' else "Write summarises in English."
        return f"""你是一个高级技术内容摘要专家。请为以下文章生成：
1. titleZh: 中文翻译标题
2. summary: 4-6 句结构化摘要（核心问题+关键论点+结论）
3. reason: 1 句推荐理由于

{lang_instruction}

## 待摘要文章
{articles_list}

严格按 JSON 格式返回，不要包含 markdown 代码块：
{{
  "results": [
    {{
      "index": 0,
      "titleZh": "中文翻译标题",
      "summary": "摘要内容...",
      "reason": "推荐理由..."
    }}
  ]
}}"""

    def generate_highlights(self, top_articles: List[Dict[str, Any]]) -> str:
        if not top_articles: return "无精选文章。"
        article_list = "\n".join([f"{i+1}. [{a.get('category')}] {a.get('titleZh', a['title'])} - {a.get('summary', '')[:100]}" for i, a in enumerate(top_articles[:10])])
        prompt = f"根据以下今日精选技术文章列表，写一段 3-5 句话的宏观趋势总结。直接返回纯文本。\n\n{article_list}"
        return self.call_ai(prompt).strip()

    def build_report(self, top_articles: List[Dict[str, Any]], highlights: str) -> str:
        if not top_articles:
            return "未获取到任何有价值资讯。"
        
        md = f"📝 **今日看点**\n\n{highlights}\n\n"
        md += "---\n\n🏆 **今日必读 Top 3**\n\n"
        for idx, a in enumerate(top_articles[:3]):
            md += f"### {idx+1}. {a.get('titleZh', a['title'])}\n"
            md += f"🔗 [{a['sourceName']}]({a['link']})\n"
            md += f"💡 **推荐理由**: {a.get('reason', '')}\n"
            md += f"📖 **摘要**: {a.get('summary', '')}\n"
            md += f"🏷️ `{'` `'.join(a.get('keywords', []))}`\n\n"
        
        md += "---\n\n📚 **分类速递**\n\n"
        grouped = {}
        for a in top_articles[3:]:
            cat = a.get('category', 'other')
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(a)
            
        for cat in ['ai-ml', 'security', 'engineering', 'tools', 'opinion', 'other']:
            if cat in grouped:
                meta = CATEGORY_META.get(cat, CATEGORY_META['other'])
                md += f"#### {meta['emoji']} {meta['label']}\n"
                for a in grouped[cat]:
                    md += f"- [{a.get('titleZh', a['title'])}]({a['link']}) - {a.get('summary', '')[:80]}...\n"
                md += "\n"
                
        return md

    def run(self) -> str:
        logger.info("[AIDigest] Starting AI Daily Digest pipeline...")
        articles = self.fetch_all_articles()
        if not articles:
            return "没有抓取到新文章。"
        scored = self.score_articles(articles)
        top = self.summarize_top_articles(scored)
        highlights = self.generate_highlights(top)
        report = self.build_report(top, highlights)
        logger.info("[AIDigest] Pipeline finished.")
        return report
