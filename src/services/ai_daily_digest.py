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
from datetime import datetime, timezone
from typing import List, Dict, Any

import litellm
from src.config import get_config

logger = logging.getLogger(__name__)

# 预设的 90 个精选 RSS 源 (部分示例，可全量补充)
RSS_FEEDS = [
    {"name": "simonwillison.net", "xmlUrl": "https://simonwillison.net/atom/everything/", "htmlUrl": "https://simonwillison.net"},
    {"name": "jeffgeerling.com", "xmlUrl": "https://www.jeffgeerling.com/blog.xml", "htmlUrl": "https://jeffgeerling.com"},
    {"name": "seangoedecke.com", "xmlUrl": "https://www.seangoedecke.com/rss.xml", "htmlUrl": "https://seangoedecke.com"},
    {"name": "krebsonsecurity.com", "xmlUrl": "https://krebsonsecurity.com/feed/", "htmlUrl": "https://krebsonsecurity.com"},
    {"name": "daringfireball.net", "xmlUrl": "https://daringfireball.net/feeds/main", "htmlUrl": "https://daringfireball.net"},
    {"name": "ericmigi.com", "xmlUrl": "https://ericmigi.com/rss.xml", "htmlUrl": "https://ericmigi.com"},
    {"name": "antirez.com", "xmlUrl": "http://antirez.com/rss", "htmlUrl": "http://antirez.com"},
    {"name": "idiallo.com", "xmlUrl": "https://idiallo.com/feed.rss", "htmlUrl": "https://idiallo.com"},
    {"name": "maurycyz.com", "xmlUrl": "https://maurycyz.com/index.xml", "htmlUrl": "https://maurycyz.com"},
    {"name": "pluralistic.net", "xmlUrl": "https://pluralistic.net/feed/", "htmlUrl": "https://pluralistic.net"},
    {"name": "shkspr.mobi", "xmlUrl": "https://shkspr.mobi/blog/feed/", "htmlUrl": "https://shkspr.mobi"},
    {"name": "lcamtuf.substack.com", "xmlUrl": "https://lcamtuf.substack.com/feed", "htmlUrl": "https://lcamtuf.substack.com"},
    {"name": "mitchellh.com", "xmlUrl": "https://mitchellh.com/feed.xml", "htmlUrl": "https://mitchellh.com"},
    {"name": "dynomight.net", "xmlUrl": "https://dynomight.net/feed.xml", "htmlUrl": "https://dynomight.net"},
    {"name": "utcc.utoronto.ca/~cks", "xmlUrl": "https://utcc.utoronto.ca/~cks/space/blog/?atom", "htmlUrl": "https://utcc.utoronto.ca/~cks"},
    {"name": "xeiaso.net", "xmlUrl": "https://xeiaso.net/blog.rss", "htmlUrl": "https://xeiaso.net"},
    {"name": "devblogs.microsoft.com/oldnewthing", "xmlUrl": "https://devblogs.microsoft.com/oldnewthing/feed", "htmlUrl": "https://devblogs.microsoft.com/oldnewthing"},
    {"name": "righto.com", "xmlUrl": "https://www.righto.com/feeds/posts/default", "htmlUrl": "https://righto.com"},
    {"name": "lucumr.pocoo.org", "xmlUrl": "https://lucumr.pocoo.org/feed.atom", "htmlUrl": "https://lucumr.pocoo.org"},
    {"name": "skyfall.dev", "xmlUrl": "https://skyfall.dev/rss.xml", "htmlUrl": "https://skyfall.dev"},
    {"name": "garymarcus.substack.com", "xmlUrl": "https://garymarcus.substack.com/feed", "htmlUrl": "https://garymarcus.substack.com"},
    {"name": "rachelbythebay.com", "xmlUrl": "https://rachelbythebay.com/w/atom.xml", "htmlUrl": "https://rachelbythebay.com"},
    {"name": "overreacted.io", "xmlUrl": "https://overreacted.io/rss.xml", "htmlUrl": "https://overreacted.io"},
    {"name": "timsh.org", "xmlUrl": "https://timsh.org/rss/", "htmlUrl": "https://timsh.org"},
    {"name": "johndcook.com", "xmlUrl": "https://www.johndcook.com/blog/feed/", "htmlUrl": "https://johndcook.com"},
    {"name": "gilesthomas.com", "xmlUrl": "https://gilesthomas.com/feed/rss.xml", "htmlUrl": "https://gilesthomas.com"},
    {"name": "matklad.github.io", "xmlUrl": "https://matklad.github.io/feed.xml", "htmlUrl": "https://matklad.github.io"},
    {"name": "derekthompson.org", "xmlUrl": "https://www.theatlantic.com/feed/author/derek-thompson/", "htmlUrl": "https://derekthompson.org"},
    {"name": "evanhahn.com", "xmlUrl": "https://evanhahn.com/feed.xml", "htmlUrl": "https://evanhahn.com"},
    {"name": "terriblesoftware.org", "xmlUrl": "https://terriblesoftware.org/feed/", "htmlUrl": "https://terriblesoftware.org"},
    {"name": "rakhim.exotext.com", "xmlUrl": "https://rakhim.exotext.com/rss.xml", "htmlUrl": "https://rakhim.exotext.com"},
    {"name": "joanwestenberg.com", "xmlUrl": "https://joanwestenberg.com/rss", "htmlUrl": "https://joanwestenberg.com"},
    {"name": "xania.org", "xmlUrl": "https://xania.org/feed", "htmlUrl": "https://xania.org"},
    {"name": "micahflee.com", "xmlUrl": "https://micahflee.com/feed/", "htmlUrl": "https://micahflee.com"},
    {"name": "nesbitt.io", "xmlUrl": "https://nesbitt.io/feed.xml", "htmlUrl": "https://nesbitt.io"},
    {"name": "construction-physics.com", "xmlUrl": "https://www.construction-physics.com/feed", "htmlUrl": "https://construction-physics.com"},
    {"name": "tedium.co", "xmlUrl": "https://feed.tedium.co/", "htmlUrl": "https://tedium.co"},
    {"name": "susam.net", "xmlUrl": "https://susam.net/feed.xml", "htmlUrl": "https://susam.net"},
    {"name": "entropicthoughts.com", "xmlUrl": "https://entropicthoughts.com/feed.xml", "htmlUrl": "https://entropicthoughts.com"},
    {"name": "buttondown.com/hillelwayne", "xmlUrl": "https://buttondown.com/hillelwayne/rss", "htmlUrl": "https://buttondown.com/hillelwayne"},
    {"name": "dwarkesh.com", "xmlUrl": "https://www.dwarkeshpatel.com/feed", "htmlUrl": "https://dwarkesh.com"},
    {"name": "borretti.me", "xmlUrl": "https://borretti.me/feed.xml", "htmlUrl": "https://borretti.me"},
    {"name": "wheresyoured.at", "xmlUrl": "https://www.wheresyoured.at/rss/", "htmlUrl": "https://wheresyoured.at"},
    {"name": "jayd.ml", "xmlUrl": "https://jayd.ml/feed.xml", "htmlUrl": "https://jayd.ml"},
    {"name": "minimaxir.com", "xmlUrl": "https://minimaxir.com/index.xml", "htmlUrl": "https://minimaxir.com"},
    {"name": "geohot.github.io", "xmlUrl": "https://geohot.github.io/blog/feed.xml", "htmlUrl": "https://geohot.github.io"},
    {"name": "paulgraham.com", "xmlUrl": "http://www.aaronsw.com/2002/feeds/pgessays.rss", "htmlUrl": "https://paulgraham.com"},
    {"name": "filfre.net", "xmlUrl": "https://www.filfre.net/feed/", "htmlUrl": "https://filfre.net"},
    {"name": "blog.jim-nielsen.com", "xmlUrl": "https://blog.jim-nielsen.com/feed.xml", "htmlUrl": "https://blog.jim-nielsen.com"},
    {"name": "dfarq.homeip.net", "xmlUrl": "https://dfarq.homeip.net/feed/", "htmlUrl": "https://dfarq.homeip.net"},
    {"name": "jyn.dev", "xmlUrl": "https://jyn.dev/atom.xml", "htmlUrl": "https://jyn.dev"},
    {"name": "geoffreylitt.com", "xmlUrl": "https://www.geoffreylitt.com/feed.xml", "htmlUrl": "https://geoffreylitt.com"},
    {"name": "downtowndougbrown.com", "xmlUrl": "https://www.downtowndougbrown.com/feed/", "htmlUrl": "https://downtowndougbrown.com"},
    {"name": "brutecat.com", "xmlUrl": "https://brutecat.com/rss.xml", "htmlUrl": "https://brutecat.com"},
    {"name": "eli.thegreenplace.net", "xmlUrl": "https://eli.thegreenplace.net/feeds/all.atom.xml", "htmlUrl": "https://eli.thegreenplace.net"},
    {"name": "abortretry.fail", "xmlUrl": "https://www.abortretry.fail/feed", "htmlUrl": "https://abortretry.fail"},
    {"name": "fabiensanglard.net", "xmlUrl": "https://fabiensanglard.net/rss.xml", "htmlUrl": "https://fabiensanglard.net"},
    {"name": "oldvcr.blogspot.com", "xmlUrl": "https://oldvcr.blogspot.com/feeds/posts/default", "htmlUrl": "https://oldvcr.blogspot.com"},
    {"name": "bogdanthegeek.github.io", "xmlUrl": "https://bogdanthegeek.github.io/blog/index.xml", "htmlUrl": "https://bogdanthegeek.github.io"},
    {"name": "hugotunius.se", "xmlUrl": "https://hugotunius.se/feed.xml", "htmlUrl": "https://hugotunius.se"},
    {"name": "gwern.net", "xmlUrl": "https://gwern.substack.com/feed", "htmlUrl": "https://gwern.net"},
    {"name": "berthub.eu", "xmlUrl": "https://berthub.eu/articles/index.xml", "htmlUrl": "https://berthub.eu"},
    {"name": "chadnauseam.com", "xmlUrl": "https://chadnauseam.com/rss.xml", "htmlUrl": "https://chadnauseam.com"},
    {"name": "simone.org", "xmlUrl": "https://simone.org/feed/", "htmlUrl": "https://simone.org"},
    {"name": "it-notes.dragas.net", "xmlUrl": "https://it-notes.dragas.net/feed/", "htmlUrl": "https://it-notes.dragas.net"},
    {"name": "beej.us", "xmlUrl": "https://beej.us/blog/rss.xml", "htmlUrl": "https://beej.us"},
    {"name": "hey.paris", "xmlUrl": "https://hey.paris/index.xml", "htmlUrl": "https://hey.paris"},
    {"name": "danielwirtz.com", "xmlUrl": "https://danielwirtz.com/rss.xml", "htmlUrl": "https://danielwirtz.com"},
    {"name": "matduggan.com", "xmlUrl": "https://matduggan.com/rss/", "htmlUrl": "https://matduggan.com"},
    {"name": "refactoringenglish.com", "xmlUrl": "https://refactoringenglish.com/index.xml", "htmlUrl": "https://refactoringenglish.com"},
    {"name": "worksonmymachine.substack.com", "xmlUrl": "https://worksonmymachine.substack.com/feed", "htmlUrl": "https://worksonmymachine.substack.com"},
    {"name": "philiplaine.com", "xmlUrl": "https://philiplaine.com/index.xml", "htmlUrl": "https://philiplaine.com"},
    {"name": "steveblank.com", "xmlUrl": "https://steveblank.com/feed/", "htmlUrl": "https://steveblank.com"},
    {"name": "bernsteinbear.com", "xmlUrl": "https://bernsteinbear.com/feed.xml", "htmlUrl": "https://bernsteinbear.com"},
    {"name": "danieldelaney.net", "xmlUrl": "https://danieldelaney.net/feed", "htmlUrl": "https://danieldelaney.net"},
    {"name": "troyhunt.com", "xmlUrl": "https://www.troyhunt.com/rss/", "htmlUrl": "https://troyhunt.com"},
    {"name": "herman.bearblog.dev", "xmlUrl": "https://herman.bearblog.dev/feed/", "htmlUrl": "https://herman.bearblog.dev"},
    {"name": "tomrenner.com", "xmlUrl": "https://tomrenner.com/index.xml", "htmlUrl": "https://tomrenner.com"},
    {"name": "blog.pixelmelt.dev", "xmlUrl": "https://blog.pixelmelt.dev/rss/", "htmlUrl": "https://blog.pixelmelt.dev"},
    {"name": "martinalderson.com", "xmlUrl": "https://martinalderson.com/feed.xml", "htmlUrl": "https://martinalderson.com"},
    {"name": "danielchasehooper.com", "xmlUrl": "https://danielchasehooper.com/feed.xml", "htmlUrl": "https://danielchasehooper.com"},
    {"name": "chiark.greenend.org.uk/~sgtatham", "xmlUrl": "https://www.chiark.greenend.org.uk/~sgtatham/quasiblog/feed.xml", "htmlUrl": "https://chiark.greenend.org.uk/~sgtatham"},
    {"name": "grantslatton.com", "xmlUrl": "https://grantslatton.com/rss.xml", "htmlUrl": "https://grantslatton.com"},
    {"name": "experimental-history.com", "xmlUrl": "https://www.experimental-history.com/feed", "htmlUrl": "https://experimental-history.com"},
    {"name": "anildash.com", "xmlUrl": "https://anildash.com/feed.xml", "htmlUrl": "https://anildash.com"},
    {"name": "aresluna.org", "xmlUrl": "https://aresluna.org/main.rss", "htmlUrl": "https://aresluna.org"},
    {"name": "michael.stapelberg.ch", "xmlUrl": "https://michael.stapelberg.ch/feed.xml", "htmlUrl": "https://michael.stapelberg.ch"},
    {"name": "miguelgrinberg.com", "xmlUrl": "https://blog.miguelgrinberg.com/feed", "htmlUrl": "https://miguelgrinberg.com"},
    {"name": "keygen.sh", "xmlUrl": "https://keygen.sh/blog/feed.xml", "htmlUrl": "https://keygen.sh"},
    {"name": "mjg59.dreamwidth.org", "xmlUrl": "https://mjg59.dreamwidth.org/data/rss", "htmlUrl": "https://mjg59.dreamwidth.org"},
    {"name": "computer.rip", "xmlUrl": "https://computer.rip/rss.xml", "htmlUrl": "https://computer.rip"},
    {"name": "tedunangst.com", "xmlUrl": "https://www.tedunangst.com/flak/rss", "htmlUrl": "https://tedunangst.com"},
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
    if not date_str:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    date_str = date_str.strip()
    try:
        from dateutil import parser
        return parser.parse(date_str)
    except Exception:
        pass
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
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
            batch = articles[i:i + batch_size]
            prompt = self._build_scoring_prompt(batch)
            result_str = self.call_ai(prompt, json_format=True)
            if not result_str:
                continue
            try:
                # remove Markdown code blocks if any
                if result_str.startswith('```'):
                    result_str = re.sub(r'^```(json)?\n?|\n?```$', '', result_str.strip())
                parsed = json.loads(result_str)
                for res in parsed.get("results", []):
                    idx = res.get("index")
                    if idx is not None and 0 <= idx < len(batch):
                        article = batch[idx]
                        article['score'] = res.get('relevance', 5) + res.get('quality', 5) + res.get('timeliness', 5)
                        article['category'] = res.get('category', 'other')
                        article['keywords'] = res.get('keywords', [])[:4]
                        scored_articles.append(article)
            except Exception as e:
                logger.error(f"[AIDigest] Scoring JSON parse error: {e}")
        return scored_articles

    def _build_scoring_prompt(self, batch: List[Dict[str, Any]]) -> str:
        articles_list = "\n\n---\n\n".join([f"Index {idx}: [{a['sourceName']}] {a['title']}\n{a['description'][:300]}" for idx, a in enumerate(batch)])
        return f"""你是一个技术内容策展人，正在为一份面向技术爱好者的每日精选摘要筛选文章。

请对以下文章进行三个维度的评分（1-10 整数，10 分最高），并为每篇文章分配一个分类标签和提取 2-4 个关键词。

### 1. 相关性 (relevance) - 对技术/编程/AI/互联网从业者的价值
- 10: 所有技术人都应该知道的重大事件/突破
- 7-9: 对大部分技术从业者有价值
- 4-6: 对特定技术领域有价值
- 1-3: 与技术行业关联不大

### 2. 质量 (quality) - 文章本身的深度和写作质量
- 10: 深度分析，原创洞见，引用丰富
- 7-9: 有深度，观点独到
- 4-6: 信息准确，表达清晰
- 1-3: 浅尝辄止或纯转述

### 3. 时效性 (timeliness) - 当前是否值得阅读
- 10: 正在发生的重大事件/刚发布的重要工具
- 7-9: 近期热点相关
- 4-6: 常青内容，不过时
- 1-3: 过时或无时效价值

## 分类标签（必须从以下选一个）
- ai-ml: AI、机器学习、LLM、深度学习相关
- security: 安全、隐私、漏洞、加密相关
- engineering: 软件工程、架构、编程语言、系统设计
- tools: 开发工具、开源项目、新发布的库/框架
- opinion: 行业观点、个人思考、职业发展、文化评论
- other: 以上都不太适合的

## 关键词提取
提取 2-4 个最能代表文章主题的关键词（用英文，简短，如 "Rust", "LLM", "database", "performance"）

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
            batch = top_articles[i:i + batch_size]
            prompt = self._build_summary_prompt(batch)
            result_str = self.call_ai(prompt, json_format=True)
            if not result_str:
                continue
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
        lang_instruction = "请用中文撰写摘要和推荐理由。如果原文是英文，请翻译为中文。标题翻译也用中文。" if self.language == 'zh' else "Write summaries, reasons, and title translations in English."
        return f"""你是一个技术内容摘要专家。请为以下文章完成三件事：

1. **中文标题** (titleZh): 将英文标题翻译成自然的中文。如果原标题已经是中文则保持不变。
2. **摘要** (summary): 4-6 句话的结构化摘要，让读者不点进原文也能了解核心内容。包含：
   - 文章讨论的核心问题或主题（1 句）
   - 关键论点、技术方案或发现（2-3 句）
   - 结论或作者的核心观点（1 句）
3. **推荐理由** (reason): 1 句话说明"为什么值得读"，区别于摘要（摘要说"是什么"，推荐理由说"为什么"）。

{lang_instruction}

摘要要求：
- 直接说重点，不要用"本文讨论了..."、"这篇文章介绍了..."这种开头
- 包含具体的技术名词、数据、方案名称或观点
- 保留关键数字和指标（如性能提升百分比、用户数、版本号等）
- 如果文章涉及对比或选型，要点出比较对象和结论

## 待摘要文章
{articles_list}

严格按 JSON 格式返回，不要包含 markdown 代码块或其他文字：
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
        if not top_articles:
            return "无精选文章。"
        article_list = "\n".join([f"{i + 1}. [{a.get('category')}] {a.get('titleZh', a['title'])} - {a.get('summary', '')[:100]}" for i, a in enumerate(top_articles[:10])])
        prompt = f"根据以下今日精选技术文章列表，写一段 3-5 句话的宏观趋势总结。直接返回纯文本。\n\n{article_list}"
        return self.call_ai(prompt).strip()

    def humanize_time(self, pub_date: datetime) -> str:
        now = datetime.now(timezone.utc)
        diff = now - pub_date
        diff_mins = int(diff.total_seconds() / 60)
        diff_hours = int(diff.total_seconds() / 3600)
        diff_days = diff.days

        if diff_mins < 60:
            return f"{diff_mins} 分钟前"
        if diff_hours < 24:
            return f"{diff_hours} 小时前"
        if diff_days < 7:
            return f"{diff_days} 天前"
        return pub_date.strftime('%Y-%m-%d')

    def generate_keyword_bar_chart(self, articles: List[Dict[str, Any]]) -> str:
        kw_count = {}
        for a in articles:
            for kw in a.get('keywords', []):
                norm = kw.lower()
                kw_count[norm] = kw_count.get(norm, 0) + 1

        sorted_kw = sorted(kw_count.items(), key=lambda x: x[1], reverse=True)[:12]
        if not sorted_kw:
            return ""

        labels = ", ".join([f'"{k}"' for k, v in sorted_kw])
        values = ", ".join([str(v) for k, v in sorted_kw])
        max_val = sorted_kw[0][1]

        chart = "```mermaid\nxychart-beta horizontal\n"
        chart += '    title "高频关键词"\n'
        chart += f"    x-axis [{labels}]\n"
        chart += f'    y-axis "出现次数" 0 --> {max_val + 2}\n'
        chart += f"    bar [{values}]\n"
        chart += "```\n"
        return chart

    def generate_category_pie_chart(self, articles: List[Dict[str, Any]]) -> str:
        cat_count = {}
        for a in articles:
            cat = a.get('category', 'other')
            cat_count[cat] = cat_count.get(cat, 0) + 1
        if not cat_count:
            return ""

        sorted_cat = sorted(cat_count.items(), key=lambda x: x[1], reverse=True)
        chart = "```mermaid\npie showData\n"
        chart += '    title "文章分类分布"\n'
        for cat, count in sorted_cat:
            meta = CATEGORY_META.get(cat, CATEGORY_META['other'])
            chart += f'    "{meta["emoji"]} {meta["label"]}" : {count}\n'
        chart += "```\n"
        return chart

    def generate_ascii_bar_chart(self, articles: List[Dict[str, Any]]) -> str:
        kw_count = {}
        for a in articles:
            for kw in a.get('keywords', []):
                norm = kw.lower()
                kw_count[norm] = kw_count.get(norm, 0) + 1

        sorted_kw = sorted(kw_count.items(), key=lambda x: x[1], reverse=True)[:10]
        if not sorted_kw:
            return ""

        max_val = sorted_kw[0][1]
        max_bar_width = 20
        max_label_len = max(len(k) for k, v in sorted_kw)

        chart = "```\n"
        for label, value in sorted_kw:
            bar_len = max(1, round((value / max_val) * max_bar_width))
            bar = '█' * bar_len + '░' * (max_bar_width - bar_len)
            chart += f"{label.ljust(max_label_len)} │ {bar} {value}\n"
        chart += "```\n"
        return chart

    def generate_tag_cloud(self, articles: List[Dict[str, Any]]) -> str:
        kw_count = {}
        for a in articles:
            for kw in a.get('keywords', []):
                norm = kw.lower()
                kw_count[norm] = kw_count.get(norm, 0) + 1

        sorted_kw = sorted(kw_count.items(), key=lambda x: x[1], reverse=True)[:20]
        if not sorted_kw:
            return ""

        tags = []
        for i, (word, count) in enumerate(sorted_kw):
            if i < 3:
                tags.append(f"**{word}**({count})")
            else:
                tags.append(f"{word}({count})")
        return " · ".join(tags)

    def build_report(self, top_articles: List[Dict[str, Any]], highlights: str) -> str:
        if not top_articles:
            msg = "未获取到任何有价值资讯。"
            if self.last_error:
                msg += f"\n\n> ⚠️ **诊断信息**: {self.last_error}\n> 请检查 API Key 是否有效，以及 `LITELLM_MODEL` 配置是否正确。"
            return msg

        now = datetime.now(timezone.utc)
        date_str = now.strftime('%Y-%m-%d')

        report = f"# 📰 AI 博客每日精选 — {date_str}\n\n"
        report += f"> 来自 Karpathy 推荐的顶级技术博客，AI 精选 Top {len(top_articles)}\n\n"

        if highlights:
            report += f"## 📝 今日看点\n\n{highlights}\n\n---\n\n"

        if len(top_articles) >= 3:
            report += "## 🏆 今日必读\n\n"
            medals = ['🥇', '🥈', '🥉']
            for i in range(min(3, len(top_articles))):
                a = top_articles[i]
                medal = medals[i]
                cat_meta = CATEGORY_META.get(a.get('category', 'other'), CATEGORY_META['other'])

                report += f"{medal} **{a.get('titleZh', a['title'])}**\n\n"
                report += f"[{a['title']}]({a['link']}) — {a['sourceName']} · {self.humanize_time(a['pubDate'])} · {cat_meta['emoji']} {cat_meta['label']}\n\n"
                report += f"> {a.get('summary', '')}\n\n"
                if a.get('reason'):
                    report += f"💡 **为什么值得读**: {a['reason']}\n\n"
                if a.get('keywords'):
                    report += f"🏷️ {', '.join(a['keywords'])}\n\n"
            report += "---\n\n"

        report += "## 📊 数据概览\n\n"

        pie_chart = self.generate_category_pie_chart(top_articles)
        if pie_chart:
            report += f"### 分类分布\n\n{pie_chart}\n"

        bar_chart = self.generate_keyword_bar_chart(top_articles)
        if bar_chart:
            report += f"### 高频关键词\n\n{bar_chart}\n"

        ascii_chart = self.generate_ascii_bar_chart(top_articles)
        if ascii_chart:
            report += f"<details>\n<summary>📈 纯文本关键词图（终端友好）</summary>\n\n{ascii_chart}\n</details>\n\n"

        tag_cloud = self.generate_tag_cloud(top_articles)
        if tag_cloud:
            report += f"### 🏷️ 话题标签\n\n{tag_cloud}\n\n"

        report += "---\n\n"

        grouped = {}
        for a in top_articles:
            cat = a.get('category', 'other')
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(a)

        sorted_categories = sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)
        global_index = 0
        for cat, cat_articles in sorted_categories:
            meta = CATEGORY_META.get(cat, CATEGORY_META['other'])
            report += f"## {meta['emoji']} {meta['label']}\n\n"

            for a in cat_articles:
                global_index += 1
                score_total = a.get('score', 0)
                report += f"### {global_index}. {a.get('titleZh', a['title'])}\n\n"
                report += f"[{a['title']}]({a['link']}) — **{a['sourceName']}** · {self.humanize_time(a['pubDate'])} · ⭐ {score_total}/30\n\n"
                report += f"> {a.get('summary', '')}\n\n"
                if a.get('keywords'):
                    report += f"🏷️ {', '.join(a['keywords'])}\n\n"
                report += "---\n\n"

        time_hm = now.strftime('%H:%M')
        report += f"*生成于 {date_str} {time_hm} | 精选 {len(top_articles)} 篇*\n"
        report += "*基于 [Hacker News Popularity Contest 2025](https://refactoringenglish.com/tools/hn-popularity/) RSS 源列表，由 [Andrej Karpathy](https://x.com/karpathy) 推荐*\n"
        report += "*由「懂点儿AI」制作，欢迎关注同名微信公众号获取更多 AI 实用技巧 💡*\n"

        return report

    def run(self) -> str:
        logger.info("[AIDigest] Starting AI Daily Digest pipeline...")
        articles = self.fetch_all_articles()
        if not articles:
            msg = "未获取到任何有价值资讯。"
            if self.last_error:
                msg += f"\n\n> ⚠️ **诊断信息**: {self.last_error}\n> 请检查 API Key 是否有效，以及 `LITELLM_MODEL` 配置是否正确。"
            return msg
        scored = self.score_articles(articles)
        top = self.summarize_top_articles(scored)
        highlights = self.generate_highlights(top)
        report = self.build_report(top, highlights)
        logger.info("[AIDigest] Pipeline finished.")
        return report
