# -*- coding: utf-8 -*-
"""
===================================
AI News Digest - Configuration
===================================

职责：
1. 使用单例模式管理全局配置
2. 从 .env 文件加载配置
3. 提供类型安全的配置访问接口
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_MANAGED_LITELLM_KEY_PROVIDERS = {"gemini", "vertex_ai", "anthropic", "openai", "deepseek"}
SUPPORTED_LLM_CHANNEL_PROTOCOLS = ("openai", "anthropic", "gemini", "vertex_ai", "deepseek", "ollama")
_FALSEY_ENV_VALUES = {"0", "false", "no", "off"}
NEWS_STRATEGY_WINDOWS: Dict[str, int] = {
    "ultra_short": 1,
    "short": 3,
    "medium": 7,
    "long": 30,
}


@dataclass
class ConfigIssue:
    """Structured configuration validation issue with a severity level."""

    severity: Literal["error", "warning", "info"]
    message: str
    field: str = ""

    def __str__(self) -> str:
        return self.message


def parse_env_bool(value: Optional[str], default: bool = False) -> bool:
    """Parse common truthy/falsey environment-style values."""
    if value is None:
        return default
    normalized = value.strip().lower()
    if not normalized:
        return default
    return normalized not in _FALSEY_ENV_VALUES


def parse_env_int(
    value: Optional[str],
    default: int,
    *,
    field_name: str,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> int:
    """Parse an integer env value with warning + fallback semantics."""
    raw_value = value
    if raw_value is None or not str(raw_value).strip():
        parsed = int(default)
    else:
        try:
            parsed = int(str(raw_value).strip())
        except (TypeError, ValueError):
            logger.warning(
                "%s=%r is not a valid integer; falling back to %s",
                field_name,
                raw_value,
                default,
            )
            parsed = int(default)

    if minimum is not None and parsed < minimum:
        logger.warning(
            "%s=%r is below minimum %s; clamping to %s",
            field_name,
            parsed,
            minimum,
            minimum,
        )
        parsed = minimum

    if maximum is not None and parsed > maximum:
        logger.warning(
            "%s=%r is above maximum %s; clamping to %s",
            field_name,
            parsed,
            maximum,
            maximum,
        )
        parsed = maximum

    return parsed


def parse_env_float(
    value: Optional[str],
    default: float,
    *,
    field_name: str,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
) -> float:
    """Parse a float env value with warning + fallback semantics."""
    if value is None or not str(value).strip():
        return float(default)
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        logger.warning("%s=%r is not a valid float; falling back to %s", field_name, value, default)
        return float(default)

    if minimum is not None and parsed < minimum:
        logger.warning("%s=%r is below minimum %s; clamping to %s", field_name, parsed, minimum, minimum)
        parsed = minimum
    if maximum is not None and parsed > maximum:
        logger.warning("%s=%r is above maximum %s; clamping to %s", field_name, parsed, maximum, maximum)
        parsed = maximum
    return parsed


def normalize_news_strategy_profile(value: Optional[str]) -> str:
    """Normalize news strategy profile to known values."""
    candidate = (value or "short").strip().lower()
    return candidate if candidate in NEWS_STRATEGY_WINDOWS else "short"


def resolve_news_window_days(news_max_age_days: int, news_strategy_profile: Optional[str]) -> int:
    """Resolve effective news window days from profile and global max-age."""
    profile = normalize_news_strategy_profile(news_strategy_profile)
    profile_days = NEWS_STRATEGY_WINDOWS.get(profile, NEWS_STRATEGY_WINDOWS["short"])
    return max(1, min(max(1, int(news_max_age_days)), profile_days))


def canonicalize_llm_channel_protocol(value: Optional[str]) -> str:
    """Normalize a protocol label into a LiteLLM provider identifier."""
    candidate = (value or "").strip().lower().replace("-", "_")
    aliases = {
        "openai_compatible": "openai",
        "openai_compat": "openai",
        "claude": "anthropic",
        "google": "gemini",
        "vertex": "vertex_ai",
        "vertexai": "vertex_ai",
    }
    return aliases.get(candidate, candidate)


def resolve_llm_channel_protocol(
    protocol: Optional[str],
    *,
    base_url: Optional[str] = None,
    models: Optional[List[str]] = None,
    channel_name: Optional[str] = None,
) -> str:
    """Resolve the effective protocol for a channel."""
    explicit = canonicalize_llm_channel_protocol(protocol)
    if explicit in SUPPORTED_LLM_CHANNEL_PROTOCOLS:
        return explicit

    for model in models or []:
        if "/" not in model:
            continue
        prefix = canonicalize_llm_channel_protocol(model.split("/", 1)[0])
        if prefix in SUPPORTED_LLM_CHANNEL_PROTOCOLS:
            return prefix

    if channel_name:
        name_protocol = canonicalize_llm_channel_protocol(channel_name)
        if name_protocol in SUPPORTED_LLM_CHANNEL_PROTOCOLS:
            return name_protocol

    if base_url:
        parsed = urlparse(base_url)
        if parsed.hostname in {"127.0.0.1", "localhost", "0.0.0.0"}:
            return "openai"
        return "openai"

    return ""


def channel_allows_empty_api_key(protocol: Optional[str], base_url: Optional[str]) -> bool:
    """Return True when a channel can run without an API key."""
    resolved_protocol = resolve_llm_channel_protocol(protocol, base_url=base_url)
    if resolved_protocol == "ollama":
        return True
    parsed = urlparse(base_url or "")
    return parsed.hostname in {"127.0.0.1", "localhost", "0.0.0.0"}


def normalize_llm_channel_model(model: str, protocol: Optional[str], base_url: Optional[str] = None) -> str:
    """Attach a provider prefix when the model omits it."""
    normalized_model = model.strip()
    if not normalized_model:
        return normalized_model

    resolved_protocol = resolve_llm_channel_protocol(protocol, base_url=base_url, models=[normalized_model])

    if "/" in normalized_model:
        raw_prefix, remainder = normalized_model.split("/", 1)
        prefix = raw_prefix.lower()
        canonical_prefix = canonicalize_llm_channel_protocol(prefix)
        known_providers = _MANAGED_LITELLM_KEY_PROVIDERS | set(SUPPORTED_LLM_CHANNEL_PROTOCOLS) | {
            "cohere", "huggingface", "bedrock", "sagemaker", "azure",
            "replicate", "together_ai", "palm", "text-completion-openai",
            "command-r", "groq", "cerebras", "fireworks_ai", "friendliai",
        }
        if prefix in known_providers:
            return normalized_model
        if canonical_prefix in known_providers:
            return f"{canonical_prefix}/{remainder}"
        if resolved_protocol:
            return f"{resolved_protocol}/{normalized_model}"
        return normalized_model

    if not resolved_protocol:
        return normalized_model
    return f"{resolved_protocol}/{normalized_model}"


def get_configured_llm_models(model_list: List[Dict[str, Any]]) -> List[str]:
    """Return non-legacy model names declared in Router model_list order."""
    models: List[str] = []
    seen: set = set()
    for entry in model_list or []:
        name = str(entry.get("model_name") or "").strip()
        if not name:
            params = entry.get("litellm_params", {}) or {}
            name = str(params.get("model") or "").strip()
        if not name or name.startswith("__legacy_") or name in seen:
            continue
        seen.add(name)
        models.append(name)
    return models


def resolve_unified_llm_temperature(model: str) -> float:
    """Resolve the unified LLM temperature with backward-compatible fallbacks."""
    llm_temperature_raw = os.getenv("LLM_TEMPERATURE")
    if llm_temperature_raw and llm_temperature_raw.strip():
        try:
            return float(llm_temperature_raw)
        except (ValueError, TypeError):
            pass

    provider_temperature_env = {
        "gemini": "GEMINI_TEMPERATURE",
        "vertex_ai": "GEMINI_TEMPERATURE",
        "anthropic": "ANTHROPIC_TEMPERATURE",
        "openai": "OPENAI_TEMPERATURE",
        "deepseek": "OPENAI_TEMPERATURE",
    }
    preferred_env = provider_temperature_env.get(_get_litellm_provider(model))
    if preferred_env:
        preferred_value = os.getenv(preferred_env)
        if preferred_value and preferred_value.strip():
            try:
                return float(preferred_value)
            except (ValueError, TypeError):
                pass

    for env_name in ("GEMINI_TEMPERATURE", "ANTHROPIC_TEMPERATURE", "OPENAI_TEMPERATURE"):
        env_value = os.getenv(env_name)
        if env_value and env_value.strip():
            try:
                return float(env_value)
            except (ValueError, TypeError):
                continue

    return 0.7


def _get_litellm_provider(model: str) -> str:
    """Extract the LiteLLM provider prefix from a model string."""
    if not model:
        return ""
    if "/" in model:
        return model.split("/", 1)[0]
    return "openai"


def _uses_direct_env_provider(model: str) -> bool:
    """Whether runtime handles the model via direct litellm env/provider resolution."""
    provider = _get_litellm_provider(model)
    return bool(provider) and provider not in _MANAGED_LITELLM_KEY_PROVIDERS


def setup_env(override: bool = False):
    """
    Initialize environment variables from .env file.
    """
    env_file = os.getenv("ENV_FILE")
    if env_file:
        env_path = Path(env_file)
    else:
        env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path, override=override)


@dataclass
class Config:
    """
    AI News Digest - 系统配置类（单例模式）

    设计说明：
    - 使用 dataclass 简化配置属性定义
    - 所有配置项从环境变量读取，支持默认值
    - 类方法 get_instance() 实现单例访问
    """

    # === AI / LLM 配置 ===
    litellm_model: str = ""
    litellm_fallback_models: List[str] = field(default_factory=list)
    llm_temperature: float = 0.7

    litellm_config_path: Optional[str] = None
    llm_models_source: str = "legacy_env"
    llm_channels: List[Dict[str, Any]] = field(default_factory=list)
    llm_model_list: List[Dict[str, Any]] = field(default_factory=list)

    gemini_api_keys: List[str] = field(default_factory=list)
    anthropic_api_keys: List[str] = field(default_factory=list)
    openai_api_keys: List[str] = field(default_factory=list)
    deepseek_api_keys: List[str] = field(default_factory=list)

    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3-flash-preview"
    gemini_model_fallback: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.7
    gemini_request_delay: float = 2.0
    gemini_max_retries: int = 5
    gemini_retry_delay: float = 5.0

    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_temperature: float = 0.7
    anthropic_max_tokens: int = 8192

    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: Optional[str] = None
    openai_temperature: float = 0.7

    # === AIHubMix ===
    # Handled via _resolve_aihubmix_env in _load_from_env; not stored as a dataclass field.

    # === AI Daily Digest 配置 ===
    ai_daily_digest_enabled: bool = True
    ai_daily_digest_days: int = 2
    ai_daily_digest_top_n: int = 15
    ai_daily_digest_language: str = "zh"
    ai_daily_digest_interval_hours: int = 48

    # === 通知配置（可同时配置多个，全部推送）===
    wechat_webhook_url: Optional[str] = None
    feishu_webhook_url: Optional[str] = None

    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_message_thread_id: Optional[str] = None

    email_sender: Optional[str] = None
    email_sender_name: str = "AI News Digest"
    email_password: Optional[str] = None
    email_receivers: List[str] = field(default_factory=list)

    pushover_user_key: Optional[str] = None
    pushover_api_token: Optional[str] = None

    custom_webhook_urls: List[str] = field(default_factory=list)
    custom_webhook_bearer_token: Optional[str] = None
    webhook_verify_ssl: bool = True

    discord_bot_token: Optional[str] = None
    discord_main_channel_id: Optional[str] = None
    discord_webhook_url: Optional[str] = None

    slack_webhook_url: Optional[str] = None
    slack_bot_token: Optional[str] = None
    slack_channel_id: Optional[str] = None

    astrbot_token: Optional[str] = None
    astrbot_url: Optional[str] = None

    pushplus_token: Optional[str] = None
    pushplus_topic: Optional[str] = None
    serverchan3_sendkey: Optional[str] = None

    feishu_max_bytes: int = 20000
    wechat_max_bytes: int = 4000
    discord_max_words: int = 2000
    wechat_msg_type: str = "markdown"

    markdown_to_image_channels: List[str] = field(default_factory=list)
    markdown_to_image_max_chars: int = 15000
    md2img_engine: str = "wkhtmltoimage"

    # === 定时任务配置 ===
    schedule_enabled: bool = False
    schedule_time: str = "18:00"
    schedule_run_immediately: bool = True
    run_immediately: bool = True

    # === 日志与系统配置 ===
    log_dir: str = "./logs"
    log_level: str = "INFO"
    debug: bool = False
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None

    # 单例实例存储
    _instance: Optional['Config'] = None

    @classmethod
    def get_instance(cls) -> 'Config':
        """获取配置单例实例"""
        if cls._instance is None:
            cls._instance = cls._load_from_env()
        return cls._instance

    @classmethod
    def _load_from_env(cls) -> 'Config':
        """从 .env 文件加载配置"""
        setup_env()

        # === LLM multi-key parsing ===
        _gemini_keys_raw = os.getenv('GEMINI_API_KEYS', '')
        gemini_api_keys = [k.strip() for k in _gemini_keys_raw.split(',') if k.strip()]
        _single_gemini = os.getenv('GEMINI_API_KEY', '').strip()
        if not gemini_api_keys and _single_gemini:
            gemini_api_keys = [_single_gemini]

        _anthropic_keys_raw = os.getenv('ANTHROPIC_API_KEYS', '')
        anthropic_api_keys = [k.strip() for k in _anthropic_keys_raw.split(',') if k.strip()]
        _single_anthropic = os.getenv('ANTHROPIC_API_KEY', '').strip()
        if not anthropic_api_keys and _single_anthropic:
            anthropic_api_keys = [_single_anthropic]

        _openai_keys_raw = os.getenv('OPENAI_API_KEYS', '')
        openai_api_keys = [k.strip() for k in _openai_keys_raw.split(',') if k.strip()]
        _single_openai = os.getenv('OPENAI_API_KEY', '').strip()
        if not openai_api_keys and _single_openai:
            openai_api_keys = [_single_openai]

        _deepseek_keys_raw = os.getenv('DEEPSEEK_API_KEYS', '')
        deepseek_api_keys = [k.strip() for k in _deepseek_keys_raw.split(',') if k.strip()]
        _single_deepseek = os.getenv('DEEPSEEK_API_KEY', '').strip()
        if not deepseek_api_keys and _single_deepseek:
            deepseek_api_keys = [_single_deepseek]

        # === LLM config ===
        litellm_model = os.getenv('LITELLM_MODEL', '').strip()
        litellm_fallback_models_str = os.getenv('LITELLM_FALLBACK_MODELS', '')
        litellm_fallback_models = [m.strip() for m in litellm_fallback_models_str.split(',') if m.strip()]
        llm_temperature = resolve_unified_llm_temperature(litellm_model)

        # Litellm config path
        litellm_config_path_raw = os.getenv('LITELLM_CONFIG')
        litellm_config_path = litellm_config_path_raw.strip() if litellm_config_path_raw and litellm_config_path_raw.strip() else None

        # LLM channels
        llm_channels_str = os.getenv('LLM_CHANNELS', '')
        llm_channels = cls._parse_llm_channels(llm_channels_str) if llm_channels_str.strip() else []

        # Build model list
        llm_model_list: List[Dict[str, Any]] = []
        llm_models_source = "legacy_env"

        if litellm_config_path:
            config_resolved = litellm_config_path
            if not os.path.isabs(config_resolved):
                config_resolved = os.path.join(Path(__file__).parent.parent, config_resolved.lstrip('./'))
            if os.path.isfile(config_resolved):
                try:
                    yaml_models = cls._parse_litellm_yaml(config_resolved)
                    if yaml_models:
                        llm_model_list = yaml_models
                        llm_models_source = "litellm_yaml"
                except Exception as e:
                    logger.warning("Failed to parse LITELLM_CONFIG YAML (%s): %s", config_resolved, e)

        if not llm_model_list and llm_channels:
            llm_model_list = cls._channels_to_model_list(llm_channels)
            llm_models_source = "llm_channels"

        if not llm_model_list:
            llm_model_list = cls._legacy_keys_to_model_list(
                gemini_api_keys=gemini_api_keys,
                anthropic_api_keys=anthropic_api_keys,
                openai_api_keys=openai_api_keys,
                deepseek_api_keys=deepseek_api_keys,
            )
            llm_models_source = "legacy_env"

        cls._resolve_aihubmix_env()

        # Auto-infer LITELLM_MODEL if empty
        if not litellm_model and llm_model_list:
            first_entry = llm_model_list[0]
            candidate = (
                first_entry.get("model_name")
                or first_entry.get("litellm_params", {}).get("model")
                or ""
            )
            candidate = str(candidate).strip()
            if candidate and not candidate.startswith("__legacy_"):
                litellm_model = candidate
                logger.info("LITELLM_MODEL 未设置，自动选择模型: %s", litellm_model)

        # === AI Daily Digest ===
        ai_daily_digest_enabled = parse_env_bool(os.getenv('AI_DAILY_DIGEST_ENABLED'), default=True)
        ai_daily_digest_days = parse_env_int(os.getenv('AI_DAILY_DIGEST_DAYS'), 2, field_name='AI_DAILY_DIGEST_DAYS', minimum=1, maximum=7)
        ai_daily_digest_top_n = parse_env_int(os.getenv('AI_DAILY_DIGEST_TOP_N'), 15, field_name='AI_DAILY_DIGEST_TOP_N', minimum=5, maximum=50)
        ai_daily_digest_language = os.getenv('AI_DAILY_DIGEST_LANGUAGE', 'zh').strip() or 'zh'
        ai_daily_digest_interval_hours = parse_env_int(os.getenv('DIGEST_INTERVAL_HOURS'), 48, field_name='DIGEST_INTERVAL_HOURS', minimum=1, maximum=168)

        # === Notifications ===
        wechat_webhook_url = os.getenv('WECHAT_WEBHOOK_URL', '').strip() or None
        feishu_webhook_url = os.getenv('FEISHU_WEBHOOK_URL', '').strip() or None
        telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip() or None
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip() or None
        telegram_message_thread_id = os.getenv('TELEGRAM_MESSAGE_THREAD_ID', '').strip() or None

        email_sender = os.getenv('EMAIL_SENDER', '').strip() or None
        email_sender_name = os.getenv('EMAIL_SENDER_NAME', 'AI News Digest').strip()
        email_password = os.getenv('EMAIL_PASSWORD', '').strip() or None
        email_receivers_str = os.getenv('EMAIL_RECEIVERS', '')
        email_receivers = [e.strip() for e in email_receivers_str.split(',') if e.strip()]

        pushover_user_key = os.getenv('PUSHOVER_USER_KEY', '').strip() or None
        pushover_api_token = os.getenv('PUSHOVER_API_TOKEN', '').strip() or None

        custom_webhook_urls_str = os.getenv('CUSTOM_WEBHOOK_URLS', '')
        custom_webhook_urls = [u.strip() for u in custom_webhook_urls_str.split(',') if u.strip()]
        custom_webhook_bearer_token = os.getenv('CUSTOM_WEBHOOK_BEARER_TOKEN', '').strip() or None
        webhook_verify_ssl = parse_env_bool(os.getenv('WEBHOOK_VERIFY_SSL'), default=True)

        discord_bot_token = os.getenv('DISCORD_BOT_TOKEN', '').strip() or None
        discord_main_channel_id = os.getenv('DISCORD_MAIN_CHANNEL_ID', '').strip() or None
        discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '').strip() or None

        slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL', '').strip() or None
        slack_bot_token = os.getenv('SLACK_BOT_TOKEN', '').strip() or None
        slack_channel_id = os.getenv('SLACK_CHANNEL_ID', '').strip() or None

        astrbot_token = os.getenv('ASTRBOT_TOKEN', '').strip() or None
        astrbot_url = os.getenv('ASTRBOT_URL', '').strip() or None

        pushplus_token = os.getenv('PUSHPLUS_TOKEN', '').strip() or None
        pushplus_topic = os.getenv('PUSHPLUS_TOPIC', '').strip() or None
        serverchan3_sendkey = os.getenv('SERVERCHAN3_SENDKEY', '').strip() or None

        feishu_max_bytes = parse_env_int(os.getenv('FEISHU_MAX_BYTES'), 20000, field_name='FEISHU_MAX_BYTES', minimum=1000)
        wechat_max_bytes = parse_env_int(os.getenv('WECHAT_MAX_BYTES'), 4000, field_name='WECHAT_MAX_BYTES', minimum=500)
        discord_max_words = parse_env_int(os.getenv('DISCORD_MAX_WORDS'), 2000, field_name='DISCORD_MAX_WORDS', minimum=100)
        wechat_msg_type = os.getenv('WECHAT_MSG_TYPE', 'markdown').strip()

        markdown_to_image_channels_str = os.getenv('MARKDOWN_TO_IMAGE_CHANNELS', '')
        markdown_to_image_channels = [c.strip() for c in markdown_to_image_channels_str.split(',') if c.strip()]
        markdown_to_image_max_chars = parse_env_int(os.getenv('MARKDOWN_TO_IMAGE_MAX_CHARS'), 15000, field_name='MARKDOWN_TO_IMAGE_MAX_CHARS', minimum=1000)
        md2img_engine = os.getenv('MD2IMG_ENGINE', 'wkhtmltoimage').strip()

        # === Schedule ===
        schedule_enabled = parse_env_bool(os.getenv('SCHEDULE_ENABLED'), default=False)
        schedule_time = os.getenv('SCHEDULE_TIME', '18:00').strip()
        schedule_run_immediately = parse_env_bool(os.getenv('SCHEDULE_RUN_IMMEDIATELY'), default=True)
        run_immediately = parse_env_bool(os.getenv('RUN_IMMEDIATELY'), default=True)

        # === Logging / System ===
        log_dir = os.getenv('LOG_DIR', './logs').strip()
        log_level = os.getenv('LOG_LEVEL', 'INFO').strip().upper()
        debug = parse_env_bool(os.getenv('DEBUG'), default=False)
        http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
        https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')

        return cls(
            # LLM
            litellm_model=litellm_model,
            litellm_fallback_models=litellm_fallback_models,
            llm_temperature=llm_temperature,
            litellm_config_path=litellm_config_path,
            llm_models_source=llm_models_source,
            llm_channels=llm_channels,
            llm_model_list=llm_model_list,
            gemini_api_keys=gemini_api_keys,
            anthropic_api_keys=anthropic_api_keys,
            openai_api_keys=openai_api_keys,
            deepseek_api_keys=deepseek_api_keys,
            gemini_api_key=_single_gemini if _single_gemini else None,
            anthropic_api_key=_single_anthropic if _single_anthropic else None,
            openai_api_key=_single_openai if _single_openai else None,
            # AI Digest
            ai_daily_digest_enabled=ai_daily_digest_enabled,
            ai_daily_digest_days=ai_daily_digest_days,
            ai_daily_digest_top_n=ai_daily_digest_top_n,
            ai_daily_digest_language=ai_daily_digest_language,
            ai_daily_digest_interval_hours=ai_daily_digest_interval_hours,
            # Notifications
            wechat_webhook_url=wechat_webhook_url,
            feishu_webhook_url=feishu_webhook_url,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            telegram_message_thread_id=telegram_message_thread_id,
            email_sender=email_sender,
            email_sender_name=email_sender_name,
            email_password=email_password,
            email_receivers=email_receivers,
            pushover_user_key=pushover_user_key,
            pushover_api_token=pushover_api_token,
            custom_webhook_urls=custom_webhook_urls,
            custom_webhook_bearer_token=custom_webhook_bearer_token,
            webhook_verify_ssl=webhook_verify_ssl,
            discord_bot_token=discord_bot_token,
            discord_main_channel_id=discord_main_channel_id,
            discord_webhook_url=discord_webhook_url,
            slack_webhook_url=slack_webhook_url,
            slack_bot_token=slack_bot_token,
            slack_channel_id=slack_channel_id,
            astrbot_token=astrbot_token,
            astrbot_url=astrbot_url,
            pushplus_token=pushplus_token,
            pushplus_topic=pushplus_topic,
            serverchan3_sendkey=serverchan3_sendkey,
            feishu_max_bytes=feishu_max_bytes,
            wechat_max_bytes=wechat_max_bytes,
            discord_max_words=discord_max_words,
            wechat_msg_type=wechat_msg_type,
            markdown_to_image_channels=markdown_to_image_channels,
            markdown_to_image_max_chars=markdown_to_image_max_chars,
            md2img_engine=md2img_engine,
            # Schedule
            schedule_enabled=schedule_enabled,
            schedule_time=schedule_time,
            schedule_run_immediately=schedule_run_immediately,
            run_immediately=run_immediately,
            # System
            log_dir=log_dir,
            log_level=log_level,
            debug=debug,
            http_proxy=http_proxy,
            https_proxy=https_proxy,
        )

    @classmethod
    def _resolve_aihubmix_env(cls) -> None:
        """Resolve AIHubMix configuration into OPENAI-compatible env vars."""
        aih_key = os.getenv('AIHUBMIX_KEY', '').strip()
        if not aih_key:
            return
        if not os.getenv('OPENAI_API_KEY', '').strip():
            os.environ['OPENAI_API_KEY'] = aih_key
        base_url = os.getenv('AIHUBMIX_BASE_URL', '').strip()
        if base_url and not os.getenv('OPENAI_BASE_URL', '').strip():
            os.environ['OPENAI_BASE_URL'] = base_url

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（主要用于测试）"""
        cls._instance = None

    # === LLM Config parsing helpers ===

    @classmethod
    def _parse_litellm_yaml(cls, config_path: str) -> List[Dict[str, Any]]:
        """Parse a litellm config.yaml and return model_list entries."""
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed, cannot parse LITELLM_CONFIG YAML")
            return []
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            logger.warning("Failed to read LITELLM_CONFIG YAML: %s", e)
            return []
        if not isinstance(data, dict):
            return []
        model_list = data.get('model_list') or data.get('models') or []
        if not isinstance(model_list, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for entry in model_list:
            if not isinstance(entry, dict):
                continue
            model_name = str(entry.get('model_name') or entry.get('model', '')).strip()
            if not model_name:
                continue
            litellm_params = entry.get('litellm_params', {})
            if not isinstance(litellm_params, dict):
                litellm_params = {}
            wire_model = str(litellm_params.get('model', model_name)).strip()
            if not wire_model:
                wire_model = model_name
            normalized.append({
                'model_name': model_name,
                'litellm_params': {'model': wire_model},
            })
        return normalized

    @classmethod
    def _parse_llm_channels(cls, channels_str: str) -> List[Dict[str, Any]]:
        """Parse LLM_CHANNELS JSON string into a list of channel dicts."""
        try:
            channels = json.loads(channels_str)
        except json.JSONDecodeError as e:
            logger.warning("LLM_CHANNELS JSON 解析失败: %s", e)
            return []
        if not isinstance(channels, list):
            return []
        result: List[Dict[str, Any]] = []
        for ch in channels:
            if not isinstance(ch, dict):
                continue
            name = str(ch.get('name', '')).strip()
            base_url = str(ch.get('base_url', '')).strip() or None
            api_keys_raw = ch.get('api_keys') or ch.get('api_key') or ''
            if isinstance(api_keys_raw, list):
                api_keys = [str(k).strip() for k in api_keys_raw if str(k).strip()]
            elif isinstance(api_keys_raw, str) and api_keys_raw.strip():
                api_keys = [api_keys_raw.strip()]
            else:
                api_keys = []
            protocol = str(ch.get('protocol', '')).strip() or None
            models_raw = ch.get('models') or ch.get('model') or []
            if isinstance(models_raw, list):
                models = [str(m).strip() for m in models_raw if str(m).strip()]
            elif isinstance(models_raw, str) and models_raw.strip():
                models = [m.strip() for m in models_raw.split(',') if m.strip()]
            else:
                models = []
            result.append({
                'name': name or 'unnamed',
                'base_url': base_url,
                'api_keys': api_keys,
                'protocol': protocol,
                'models': models,
                '_raw': ch,
            })
        return result

    @classmethod
    def _channels_to_model_list(cls, channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert LLM_CHANNELS entries into litellm model_list format."""
        model_list: List[Dict[str, Any]] = []
        for ch in channels:
            protocol = ch.get('protocol')
            base_url = ch.get('base_url')
            api_keys = ch.get('api_keys', [])
            models = ch.get('models', [])
            name = ch.get('name', '')
            has_key = any(k and len(k) >= 8 for k in api_keys)
            allows_empty = channel_allows_empty_api_key(protocol, base_url)
            if not has_key and not allows_empty:
                logger.info("LLM channel '%s': no API key configured, skipping", name or 'unnamed')
                continue
            if not models:
                logger.info("LLM channel '%s': no models configured, skipping", name or 'unnamed')
                continue
            for model in models:
                normalized_model = normalize_llm_channel_model(model, protocol, base_url)
                entry: Dict[str, Any] = {
                    'model_name': normalized_model,
                    'litellm_params': {'model': normalized_model},
                }
                if base_url:
                    entry['litellm_params']['api_base'] = base_url
                if api_keys:
                    entry['litellm_params']['api_key'] = api_keys[0]
                model_list.append(entry)
        return model_list

    @classmethod
    def _legacy_keys_to_model_list(
        cls,
        gemini_api_keys: List[str],
        anthropic_api_keys: List[str],
        openai_api_keys: List[str],
        deepseek_api_keys: List[str],
    ) -> List[Dict[str, Any]]:
        """Build model_list from legacy per-provider API keys."""
        model_list: List[Dict[str, Any]] = []
        gemini_model_str = os.getenv('GEMINI_MODEL', 'gemini-3-flash-preview').strip()
        for key in gemini_api_keys:
            if key and len(key) >= 8:
                model_list.append({
                    'model_name': f'gemini/{gemini_model_str}',
                    'litellm_params': {
                        'model': f'gemini/{gemini_model_str}',
                        'api_key': key,
                    },
                })
        anthropic_model_str = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022').strip()
        for key in anthropic_api_keys:
            if key and len(key) >= 8:
                model_list.append({
                    'model_name': f'anthropic/{anthropic_model_str}',
                    'litellm_params': {
                        'model': f'anthropic/{anthropic_model_str}',
                        'api_key': key,
                    },
                })
        openai_model_str = os.getenv('OPENAI_MODEL', 'gpt-4o-mini').strip()
        for key in openai_api_keys:
            if key and len(key) >= 8:
                model_list.append({
                    'model_name': f'openai/{openai_model_str}',
                    'litellm_params': {
                        'model': f'openai/{openai_model_str}',
                        'api_key': key,
                    },
                })
        deepseek_model_str = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat').strip()
        for key in deepseek_api_keys:
            if key and len(key) >= 8:
                model_list.append({
                    'model_name': f'deepseek/{deepseek_model_str}',
                    'litellm_params': {
                        'model': f'deepseek/{deepseek_model_str}',
                        'api_key': key,
                    },
                })
        return model_list

    @classmethod
    def _parse_md2img_engine(cls, value: str) -> str:
        """Parse MD2IMG_ENGINE, fallback to wkhtmltoimage for invalid values."""
        v = (value or 'wkhtmltoimage').strip().lower()
        if v in ('wkhtmltoimage', 'markdown-to-file'):
            return v
        if v:
            logger.warning(
                f"MD2IMG_ENGINE '{value}' invalid, fallback to 'wkhtmltoimage' "
                "(valid: wkhtmltoimage | markdown-to-file)"
            )
        return 'wkhtmltoimage'

    def validate_structured(self) -> List[ConfigIssue]:
        """Return structured validation issues with severity levels."""
        issues: List[ConfigIssue] = []

        # LLM availability
        has_direct_env_model = bool(self.litellm_model) and _uses_direct_env_provider(self.litellm_model)
        if not self.llm_model_list and not has_direct_env_model:
            issues.append(ConfigIssue(
                severity="error",
                message=(
                    "未配置任何 LLM（LITELLM_CONFIG / LLM_CHANNELS / *_API_KEY），"
                    "AI Digest 功能将不可用"
                ),
                field="LITELLM_CONFIG",
            ))
        elif not self.litellm_model:
            issues.append(ConfigIssue(
                severity="info",
                message=(
                    "LITELLM_MODEL 未配置，将自动从可用 API Key 推断模型。"
                    "建议尽早配置 LITELLM_MODEL（格式如 gemini/gemini-2.5-flash）"
                ),
                field="LITELLM_MODEL",
            ))

        available_router_models = get_configured_llm_models(self.llm_model_list)
        if available_router_models and self.litellm_model and not _uses_direct_env_provider(self.litellm_model) and self.litellm_model not in set(available_router_models):
            issues.append(ConfigIssue(
                severity="error",
                message=(
                    "LITELLM_MODEL 已配置，但当前渠道/配置文件中不存在该模型。"
                    f" 当前可用模型：{', '.join(available_router_models[:6])}"
                ),
                field="LITELLM_MODEL",
            ))

        # Notification channel check
        has_notification = any([
            self.wechat_webhook_url, self.feishu_webhook_url,
            (self.telegram_bot_token and self.telegram_chat_id),
            (self.email_sender and self.email_password),
            (self.pushover_user_key and self.pushover_api_token),
            self.pushplus_token, self.serverchan3_sendkey,
            self.custom_webhook_urls,
            (self.discord_webhook_url or (self.discord_bot_token and self.discord_main_channel_id)),
            (self.slack_webhook_url or (self.slack_bot_token and self.slack_channel_id)),
            (self.astrbot_token and self.astrbot_url),
        ])
        if not has_notification:
            issues.append(ConfigIssue(
                severity="warning",
                message="未配置任何通知渠道，将不会推送消息",
                field="WECHAT_WEBHOOK_URL",
            ))

        # Digest interval
        if self.ai_daily_digest_interval_hours < 1:
            issues.append(ConfigIssue(
                severity="error",
                message=f"DIGEST_INTERVAL_HOURS={self.ai_daily_digest_interval_hours} 无效，至少为 1 小时",
                field="DIGEST_INTERVAL_HOURS",
            ))

        return issues

    def validate(self) -> List[str]:
        """Return human-readable validation messages (backward compatible)."""
        return [str(issue) for issue in self.validate_structured()]


def get_config() -> Config:
    """获取配置单例实例（便捷函数）"""
    return Config.get_instance()
