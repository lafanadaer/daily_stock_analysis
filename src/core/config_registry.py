# -*- coding: utf-8 -*-
"""
===================================
AI News Digest - Config Registry
===================================

Configuration metadata for the system_config API endpoint.
Categories and field definitions for the remaining config fields.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "2026-07-02"

_CATEGORY_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "category": "ai_model",
        "label": "AI Model",
        "icon": "cpu",
        "description": "LLM model and API key configuration",
    },
    {
        "category": "notification",
        "label": "Notifications",
        "icon": "bell",
        "description": "Multi-channel notification configuration",
    },
    {
        "category": "ai_digest",
        "label": "AI Digest",
        "icon": "newspaper",
        "description": "AI Daily Digest settings",
    },
    {
        "category": "schedule",
        "label": "Schedule",
        "icon": "clock",
        "description": "Scheduling configuration",
    },
    {
        "category": "system",
        "label": "System",
        "icon": "settings",
        "description": "System settings",
    },
]

_FIELD_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # ===== AI Model =====
    "LITELLM_MODEL": {
        "key": "LITELLM_MODEL",
        "type": "string",
        "category": "ai_model",
        "label": "Primary LLM Model",
        "default": "",
        "description": "Primary model in provider/model format (e.g. gemini/gemini-3-flash-preview)",
    },
    "LITELLM_FALLBACK_MODELS": {
        "key": "LITELLM_FALLBACK_MODELS",
        "type": "string",
        "category": "ai_model",
        "label": "Fallback Models",
        "default": "",
        "description": "Comma-separated fallback models",
    },
    "GEMINI_API_KEY": {
        "key": "GEMINI_API_KEY",
        "type": "string",
        "category": "ai_model",
        "label": "Gemini API Key",
        "default": "",
        "sensitive": True,
        "description": "Google Gemini API key",
    },
    "GEMINI_MODEL": {
        "key": "GEMINI_MODEL",
        "type": "string",
        "category": "ai_model",
        "label": "Gemini Model",
        "default": "gemini-3-flash-preview",
        "description": "Gemini model name",
    },
    "ANTHROPIC_API_KEY": {
        "key": "ANTHROPIC_API_KEY",
        "type": "string",
        "category": "ai_model",
        "label": "Anthropic API Key",
        "default": "",
        "sensitive": True,
        "description": "Anthropic Claude API key",
    },
    "ANTHROPIC_MODEL": {
        "key": "ANTHROPIC_MODEL",
        "type": "string",
        "category": "ai_model",
        "label": "Anthropic Model",
        "default": "claude-3-5-sonnet-20241022",
        "description": "Claude model name",
    },
    "OPENAI_API_KEY": {
        "key": "OPENAI_API_KEY",
        "type": "string",
        "category": "ai_model",
        "label": "OpenAI API Key",
        "default": "",
        "sensitive": True,
        "description": "OpenAI API key",
    },
    "OPENAI_MODEL": {
        "key": "OPENAI_MODEL",
        "type": "string",
        "category": "ai_model",
        "label": "OpenAI Model",
        "default": "gpt-4o-mini",
        "description": "OpenAI model name",
    },
    "OPENAI_BASE_URL": {
        "key": "OPENAI_BASE_URL",
        "type": "string",
        "category": "ai_model",
        "label": "OpenAI Base URL",
        "default": "",
        "description": "Custom OpenAI-compatible API base URL",
    },
    "AIHUBMIX_KEY": {
        "key": "AIHUBMIX_KEY",
        "type": "string",
        "category": "ai_model",
        "label": "AIHubMix Key",
        "default": "",
        "sensitive": True,
        "description": "AIHubMix API key (auto-configures OpenAI-compatible base URL)",
    },
    "DEEPSEEK_API_KEY": {
        "key": "DEEPSEEK_API_KEY",
        "type": "string",
        "category": "ai_model",
        "label": "DeepSeek API Key",
        "default": "",
        "sensitive": True,
        "description": "DeepSeek API key",
    },
    "LLM_CHANNELS": {
        "key": "LLM_CHANNELS",
        "type": "string",
        "category": "ai_model",
        "label": "LLM Channels",
        "default": "",
        "description": "JSON array of LLM channel configs",
    },
    "LITELLM_CONFIG": {
        "key": "LITELLM_CONFIG",
        "type": "string",
        "category": "ai_model",
        "label": "LiteLLM Config Path",
        "default": "",
        "description": "Path to litellm_config.yaml",
    },

    # ===== AI Digest =====
    "AI_DAILY_DIGEST_ENABLED": {
        "key": "AI_DAILY_DIGEST_ENABLED",
        "type": "boolean",
        "category": "ai_digest",
        "label": "Enable AI Daily Digest",
        "default": "true",
        "description": "Enable/disable the AI daily tech news digest",
    },
    "AI_DAILY_DIGEST_DAYS": {
        "key": "AI_DAILY_DIGEST_DAYS",
        "type": "number",
        "category": "ai_digest",
        "label": "News Window (Days)",
        "default": 2,
        "min": 1,
        "max": 7,
        "description": "How many days back to fetch articles",
    },
    "AI_DAILY_DIGEST_TOP_N": {
        "key": "AI_DAILY_DIGEST_TOP_N",
        "type": "number",
        "category": "ai_digest",
        "label": "Top Articles",
        "default": 15,
        "min": 5,
        "max": 50,
        "description": "Number of top articles to include in the digest",
    },
    "AI_DAILY_DIGEST_LANGUAGE": {
        "key": "AI_DAILY_DIGEST_LANGUAGE",
        "type": "string",
        "category": "ai_digest",
        "label": "Digest Language",
        "default": "zh",
        "options": ["zh", "en"],
        "description": "Output language for the digest report",
    },
    "DIGEST_INTERVAL_HOURS": {
        "key": "DIGEST_INTERVAL_HOURS",
        "type": "number",
        "category": "ai_digest",
        "label": "Push Interval (Hours)",
        "default": 48,
        "min": 1,
        "max": 168,
        "description": "Hours between digest push runs (24=daily, 48=every 2 days)",
    },

    # ===== Schedule =====
    "SCHEDULE_ENABLED": {
        "key": "SCHEDULE_ENABLED",
        "type": "boolean",
        "category": "schedule",
        "label": "Enable Schedule",
        "default": "false",
        "description": "Enable scheduled digest runs",
    },
    "SCHEDULE_TIME": {
        "key": "SCHEDULE_TIME",
        "type": "string",
        "category": "schedule",
        "label": "Schedule Time",
        "default": "18:00",
        "description": "Daily execution time (HH:MM format)",
    },
    "SCHEDULE_RUN_IMMEDIATELY": {
        "key": "SCHEDULE_RUN_IMMEDIATELY",
        "type": "boolean",
        "category": "schedule",
        "label": "Run Immediately",
        "default": "true",
        "description": "Run task immediately when scheduler starts",
    },

    # ===== Notifications =====
    "WECHAT_WEBHOOK_URL": {
        "key": "WECHAT_WEBHOOK_URL",
        "type": "string",
        "category": "notification",
        "label": "WeChat Webhook URL",
        "default": "",
        "sensitive": True,
        "description": "Enterprise WeChat robot webhook URL",
    },
    "FEISHU_WEBHOOK_URL": {
        "key": "FEISHU_WEBHOOK_URL",
        "type": "string",
        "category": "notification",
        "label": "Feishu Webhook URL",
        "default": "",
        "sensitive": True,
        "description": "Feishu/Lark robot webhook URL",
    },
    "TELEGRAM_BOT_TOKEN": {
        "key": "TELEGRAM_BOT_TOKEN",
        "type": "string",
        "category": "notification",
        "label": "Telegram Bot Token",
        "default": "",
        "sensitive": True,
        "description": "Telegram bot token from @BotFather",
    },
    "TELEGRAM_CHAT_ID": {
        "key": "TELEGRAM_CHAT_ID",
        "type": "string",
        "category": "notification",
        "label": "Telegram Chat ID",
        "default": "",
        "description": "Target chat/channel ID",
    },
    "EMAIL_SENDER": {
        "key": "EMAIL_SENDER",
        "type": "string",
        "category": "notification",
        "label": "Email Sender",
        "default": "",
        "description": "Sender email address",
    },
    "EMAIL_PASSWORD": {
        "key": "EMAIL_PASSWORD",
        "type": "string",
        "category": "notification",
        "label": "Email Password",
        "default": "",
        "sensitive": True,
        "description": "Sender email password or app password",
    },
    "EMAIL_RECEIVERS": {
        "key": "EMAIL_RECEIVERS",
        "type": "string",
        "category": "notification",
        "label": "Email Receivers",
        "default": "",
        "description": "Comma-separated receiver email addresses",
    },
    "PUSHOVER_USER_KEY": {
        "key": "PUSHOVER_USER_KEY",
        "type": "string",
        "category": "notification",
        "label": "Pushover User Key",
        "default": "",
        "sensitive": True,
        "description": "Pushover user key",
    },
    "PUSHOVER_API_TOKEN": {
        "key": "PUSHOVER_API_TOKEN",
        "type": "string",
        "category": "notification",
        "label": "Pushover API Token",
        "default": "",
        "sensitive": True,
        "description": "Pushover application API token",
    },
    "PUSHPLUS_TOKEN": {
        "key": "PUSHPLUS_TOKEN",
        "type": "string",
        "category": "notification",
        "label": "PushPlus Token",
        "default": "",
        "sensitive": True,
        "description": "PushPlus push token",
    },
    "SERVERCHAN3_SENDKEY": {
        "key": "SERVERCHAN3_SENDKEY",
        "type": "string",
        "category": "notification",
        "label": "ServerChan3 SendKey",
        "default": "",
        "sensitive": True,
        "description": "ServerChan3 SendKey",
    },
    "CUSTOM_WEBHOOK_URLS": {
        "key": "CUSTOM_WEBHOOK_URLS",
        "type": "string",
        "category": "notification",
        "label": "Custom Webhook URLs",
        "default": "",
        "sensitive": True,
        "description": "Comma-separated custom webhook URLs",
    },
    "DISCORD_WEBHOOK_URL": {
        "key": "DISCORD_WEBHOOK_URL",
        "type": "string",
        "category": "notification",
        "label": "Discord Webhook URL",
        "default": "",
        "sensitive": True,
        "description": "Discord webhook URL",
    },
    "DISCORD_BOT_TOKEN": {
        "key": "DISCORD_BOT_TOKEN",
        "type": "string",
        "category": "notification",
        "label": "Discord Bot Token",
        "default": "",
        "sensitive": True,
        "description": "Discord bot token",
    },
    "SLACK_WEBHOOK_URL": {
        "key": "SLACK_WEBHOOK_URL",
        "type": "string",
        "category": "notification",
        "label": "Slack Webhook URL",
        "default": "",
        "sensitive": True,
        "description": "Slack incoming webhook URL",
    },
    "ASTRBOT_URL": {
        "key": "ASTRBOT_URL",
        "type": "string",
        "category": "notification",
        "label": "AstrBot URL",
        "default": "",
        "description": "AstrBot server URL",
    },
    "ASTRBOT_TOKEN": {
        "key": "ASTRBOT_TOKEN",
        "type": "string",
        "category": "notification",
        "label": "AstrBot Token",
        "default": "",
        "sensitive": True,
        "description": "AstrBot API token",
    },
    "MARKDOWN_TO_IMAGE_CHANNELS": {
        "key": "MARKDOWN_TO_IMAGE_CHANNELS",
        "type": "string",
        "category": "notification",
        "label": "Image Channels",
        "default": "",
        "description": "Comma-separated channels to send as image (telegram,wechat,custom,email)",
    },

    # ===== System =====
    "LOG_LEVEL": {
        "key": "LOG_LEVEL",
        "type": "string",
        "category": "system",
        "label": "Log Level",
        "default": "INFO",
        "options": ["DEBUG", "INFO", "WARNING", "ERROR"],
        "description": "Logging level",
    },
    "LOG_DIR": {
        "key": "LOG_DIR",
        "type": "string",
        "category": "system",
        "label": "Log Directory",
        "default": "./logs",
        "description": "Directory for log files",
    },
    "HTTP_PROXY": {
        "key": "HTTP_PROXY",
        "type": "string",
        "category": "system",
        "label": "HTTP Proxy",
        "default": "",
        "description": "HTTP proxy URL",
    },
    "HTTPS_PROXY": {
        "key": "HTTPS_PROXY",
        "type": "string",
        "category": "system",
        "label": "HTTPS Proxy",
        "default": "",
        "description": "HTTPS proxy URL",
    },
}


def get_category_definitions() -> List[Dict[str, Any]]:
    """Return a deep copy of the category definitions."""
    return deepcopy(_CATEGORY_DEFINITIONS)


def get_registered_field_keys() -> List[str]:
    """Return all known config field keys."""
    return sorted(_FIELD_DEFINITIONS.keys())


def _extract_option_values(options: List[Any]) -> List[str]:
    """Extract canonical option values from string/object style select options."""
    result: List[str] = []
    for opt in options:
        if isinstance(opt, str):
            result.append(opt)
        elif isinstance(opt, dict):
            val = opt.get("value") or opt.get("key") or ""
            if val:
                result.append(str(val))
    return result


def get_field_definition(key: str, value_hint: Optional[str] = None) -> Dict[str, Any]:
    """Return metadata for one config key, inferring missing fields."""
    existing = _FIELD_DEFINITIONS.get(key.upper())
    if existing:
        definition = deepcopy(existing)
    else:
        definition = {
            "key": key.upper(),
            "type": _infer_data_type(key.upper(), value_hint),
            "category": _infer_category(key.upper()),
            "label": key.upper(),
            "default": "",
            "sensitive": _is_sensitive_key(key.upper()),
            "description": "",
        }
    definition.setdefault("sensitive", _is_sensitive_key(key.upper()))
    definition.setdefault("ui_control", _infer_ui_control(definition.get("type", "string"), key.upper()))
    return definition


def build_schema_response() -> Dict[str, Any]:
    """Build the full schema response for the system_config API."""
    categories = get_category_definitions()
    fields_by_category: Dict[str, List[Dict[str, Any]]] = {}
    for cat in categories:
        fields_by_category[cat["category"]] = []

    for key, field_def in _FIELD_DEFINITIONS.items():
        cat = field_def.get("category", "uncategorized")
        if cat not in fields_by_category:
            fields_by_category[cat] = []
        definition = deepcopy(field_def)
        definition.setdefault("sensitive", _is_sensitive_key(key))
        definition.setdefault("ui_control", _infer_ui_control(definition.get("type", "string"), key))
        fields_by_category[cat].append(definition)

    result_categories: List[Dict[str, Any]] = []
    for cat in categories:
        cat_copy = deepcopy(cat)
        cat_name = cat_copy["category"]
        cat_copy["fields"] = fields_by_category.get(cat_name, [])
        result_categories.append(cat_copy)

    return {
        "version": SCHEMA_VERSION,
        "categories": result_categories,
    }


_SENSITIVE_PATTERNS = [
    "API_KEY", "API_KEYS", "TOKEN", "SECRET", "PASSWORD",
    "SENDKEY", "WEBHOOK_URL", "BEARER",
]


def _is_sensitive_key(key: str) -> bool:
    """Heuristic for marking sensitive keys."""
    normalized = key.upper()
    return any(pattern in normalized for pattern in _SENSITIVE_PATTERNS)


def _infer_category(key: str) -> str:
    """Guess category from key name."""
    key_upper = key.upper()
    if any(p in key_upper for p in ["GEMINI", "OPENAI", "ANTHROPIC", "DEEPSEEK", "LITELLM", "LLM_", "AIHUBMIX"]):
        return "ai_model"
    if any(p in key_upper for p in ["WECHAT", "FEISHU", "TELEGRAM", "EMAIL_", "PUSH", "DISCORD", "SLACK", "ASTRBOT", "CUSTOM_WEBHOOK", "NOTIFY", "MARKDOWN_TO_IMAGE"]):
        return "notification"
    if any(p in key_upper for p in ["DIGEST", "AI_DAILY"]):
        return "ai_digest"
    if any(p in key_upper for p in ["SCHEDULE"]):
        return "schedule"
    return "system"


def _infer_data_type(key: str, value_hint: Optional[str]) -> str:
    """Guess data type from key and optional value hint."""
    key_upper = key.upper()
    if key_upper.endswith("_ENABLED") or key_upper.endswith("_IMMEDIATELY"):
        return "boolean"
    if any(p in key_upper for p in ["HOURS", "DAYS", "TOP_N", "MAX_", "MIN_", "PORT", "_TTL"]):
        return "number"
    if value_hint is not None:
        lower = value_hint.strip().lower()
        if lower in ("true", "false"):
            return "boolean"
        try:
            int(value_hint.strip())
            return "number"
        except (ValueError, TypeError):
            pass
    return "string"


def _infer_ui_control(data_type: str, key: str) -> str:
    """Infer the appropriate UI control type."""
    if data_type == "boolean":
        return "toggle"
    key_upper = key.upper()
    if "URL" in key_upper or "WEBHOOK" in key_upper:
        return "url"
    return "text"
