# -*- coding: utf-8 -*-
"""
===================================
AI News Digest - Notification Layer
===================================

职责：
1. 多渠道推送（自动识别）：
   - 企业微信 Webhook
   - 飞书 Webhook
   - Telegram Bot
   - 邮件 SMTP
   - Pushover（手机/桌面推送）
   - PushPlus（国内推送服务）
   - Server酱3（手机APP推送服务）
   - 自定义 Webhook
   - Discord
   - Slack
   - AstrBot
2. 支持 Markdown 格式输出
3. 支持 Markdown 转图片发送
"""
import logging
from datetime import datetime
from typing import List, Optional
from enum import Enum

from src.config import get_config
from src.notification_sender import (
    AstrbotSender,
    CustomWebhookSender,
    DiscordSender,
    EmailSender,
    FeishuSender,
    PushoverSender,
    PushplusSender,
    Serverchan3Sender,
    SlackSender,
    TelegramSender,
    WechatSender,
    WECHAT_IMAGE_MAX_BYTES
)

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """通知渠道类型"""
    WECHAT = "wechat"      # 企业微信
    FEISHU = "feishu"      # 飞书
    TELEGRAM = "telegram"  # Telegram
    EMAIL = "email"        # 邮件
    PUSHOVER = "pushover"  # Pushover（手机/桌面推送）
    PUSHPLUS = "pushplus"  # PushPlus（国内推送服务）
    SERVERCHAN3 = "serverchan3"  # Server酱3（手机APP推送服务）
    CUSTOM = "custom"      # 自定义 Webhook
    DISCORD = "discord"    # Discord 机器人 (Bot)
    SLACK = "slack"        # Slack
    ASTRBOT = "astrbot"
    UNKNOWN = "unknown"    # 未知


class ChannelDetector:
    """
    渠道检测器 - 简化版

    根据配置直接判断渠道类型（不再需要 URL 解析）
    """

    @staticmethod
    def get_channel_name(channel: NotificationChannel) -> str:
        """获取渠道中文名称"""
        names = {
            NotificationChannel.WECHAT: "企业微信",
            NotificationChannel.FEISHU: "飞书",
            NotificationChannel.TELEGRAM: "Telegram",
            NotificationChannel.EMAIL: "邮件",
            NotificationChannel.PUSHOVER: "Pushover",
            NotificationChannel.PUSHPLUS: "PushPlus",
            NotificationChannel.SERVERCHAN3: "Server酱3",
            NotificationChannel.CUSTOM: "自定义Webhook",
            NotificationChannel.DISCORD: "Discord机器人",
            NotificationChannel.SLACK: "Slack",
            NotificationChannel.ASTRBOT: "ASTRBOT机器人",
            NotificationChannel.UNKNOWN: "未知渠道",
        }
        return names.get(channel, "未知渠道")


class NotificationService(
    AstrbotSender,
    CustomWebhookSender,
    DiscordSender,
    EmailSender,
    FeishuSender,
    PushoverSender,
    PushplusSender,
    Serverchan3Sender,
    SlackSender,
    TelegramSender,
    WechatSender
):
    """
    通知服务

    职责：
    1. 向所有已配置的渠道推送消息（多渠道并发）
    2. 支持 Markdown 转图片发送
    3. 支持本地保存报告

    注意：所有已配置的渠道都会收到推送
    """

    def __init__(self):
        """
        初始化通知服务

        检测所有已配置的渠道，推送时会向所有渠道发送
        """
        config = get_config()

        # Markdown 转图片（Issue #289）
        self._markdown_to_image_channels = set(
            getattr(config, 'markdown_to_image_channels', []) or []
        )
        self._markdown_to_image_max_chars = getattr(
            config, 'markdown_to_image_max_chars', 15000
        )

        # 初始化各渠道
        AstrbotSender.__init__(self, config)
        CustomWebhookSender.__init__(self, config)
        DiscordSender.__init__(self, config)
        EmailSender.__init__(self, config)
        FeishuSender.__init__(self, config)
        PushoverSender.__init__(self, config)
        PushplusSender.__init__(self, config)
        Serverchan3Sender.__init__(self, config)
        SlackSender.__init__(self, config)
        TelegramSender.__init__(self, config)
        WechatSender.__init__(self, config)

        # 检测所有已配置的渠道
        self._available_channels = self._detect_all_channels()

        if not self._available_channels:
            logger.warning("未配置有效的通知渠道，将不发送推送通知")
        else:
            channel_names = [ChannelDetector.get_channel_name(ch) for ch in self._available_channels]
            logger.info(f"已配置 {len(channel_names)} 个通知渠道：{', '.join(channel_names)}")

    def _detect_all_channels(self) -> List[NotificationChannel]:
        """
        检测所有已配置的渠道

        Returns:
            已配置的渠道列表
        """
        channels = []

        # 企业微信
        if self._wechat_url:
            channels.append(NotificationChannel.WECHAT)

        # 飞书
        if self._feishu_url:
            channels.append(NotificationChannel.FEISHU)

        # Telegram
        if self._is_telegram_configured():
            channels.append(NotificationChannel.TELEGRAM)

        # 邮件
        if self._is_email_configured():
            channels.append(NotificationChannel.EMAIL)

        # Pushover
        if self._is_pushover_configured():
            channels.append(NotificationChannel.PUSHOVER)

        # PushPlus
        if self._pushplus_token:
            channels.append(NotificationChannel.PUSHPLUS)

        # Server酱3
        if self._serverchan3_sendkey:
            channels.append(NotificationChannel.SERVERCHAN3)

        # 自定义 Webhook
        if self._custom_webhook_urls:
            channels.append(NotificationChannel.CUSTOM)

        # Discord
        if self._is_discord_configured():
            channels.append(NotificationChannel.DISCORD)

        # Slack
        if self._is_slack_configured():
            channels.append(NotificationChannel.SLACK)

        # AstrBot
        if self._is_astrbot_configured():
            channels.append(NotificationChannel.ASTRBOT)

        return channels

    def is_available(self) -> bool:
        """检查通知服务是否可用（至少有一个渠道）"""
        return len(self._available_channels) > 0

    def get_available_channels(self) -> List[NotificationChannel]:
        """获取所有已配置的渠道"""
        return self._available_channels

    def get_channel_names(self) -> str:
        """获取所有已配置渠道的名称"""
        names = [ChannelDetector.get_channel_name(ch) for ch in self._available_channels]
        return ', '.join(names)

    def _should_use_image_for_channel(
        self, channel: NotificationChannel, image_bytes: Optional[bytes]
    ) -> bool:
        """
        Decide whether to send as image for the given channel (Issue #289).

        Fallback rules (send as Markdown text instead of image):
        - image_bytes is None: conversion failed / imgkit not installed / content over max_chars
        - WeChat: image exceeds ~2MB limit
        """
        if channel.value not in self._markdown_to_image_channels or image_bytes is None:
            return False
        if channel == NotificationChannel.WECHAT and len(image_bytes) > WECHAT_IMAGE_MAX_BYTES:
            logger.warning(
                "企业微信图片超限 (%d bytes)，回退为 Markdown 文本发送",
                len(image_bytes),
            )
            return False
        return True

    def send(self, content: str) -> bool:
        """
        统一发送接口 - 向所有已配置的渠道发送

        遍历所有已配置的渠道，逐一发送消息

        Fallback rules (Markdown-to-image, Issue #289):
        - When image_bytes is None (conversion failed / imgkit not installed /
          content over max_chars): all channels configured for image will send
          as Markdown text instead.
        - When WeChat image exceeds ~2MB: that channel falls back to Markdown text.

        Args:
            content: 消息内容（Markdown 格式）

        Returns:
            是否至少有一个渠道发送成功
        """
        if not self._available_channels:
            logger.warning("通知服务不可用，跳过推送")
            return False

        # Markdown to image (Issue #289): convert once if any channel needs it.
        # Per-channel decision via _should_use_image_for_channel (see send() docstring for fallback rules).
        image_bytes = None
        channels_needing_image = {
            ch for ch in self._available_channels
            if ch.value in self._markdown_to_image_channels
        }
        if channels_needing_image:
            from src.md2img import markdown_to_image
            image_bytes = markdown_to_image(
                content, max_chars=self._markdown_to_image_max_chars
            )
            if image_bytes:
                logger.info("Markdown 已转换为图片，将向 %s 发送图片",
                            [ch.value for ch in channels_needing_image])
            elif channels_needing_image:
                try:
                    from src.config import get_config
                    engine = getattr(get_config(), "md2img_engine", "wkhtmltoimage")
                except Exception:
                    engine = "wkhtmltoimage"
                hint = (
                    "npm i -g markdown-to-file" if engine == "markdown-to-file"
                    else "wkhtmltopdf (apt install wkhtmltopdf / brew install wkhtmltopdf)"
                )
                logger.warning(
                    "Markdown 转图片失败，将回退为文本发送。请检查 MARKDOWN_TO_IMAGE_CHANNELS 配置并安装 %s",
                    hint,
                )

        channel_names = self.get_channel_names()
        logger.info(f"正在向 {len(self._available_channels)} 个渠道发送通知：{channel_names}")

        success_count = 0
        fail_count = 0

        for channel in self._available_channels:
            channel_name = ChannelDetector.get_channel_name(channel)
            use_image = self._should_use_image_for_channel(channel, image_bytes)
            try:
                if channel == NotificationChannel.WECHAT:
                    if use_image:
                        result = self._send_wechat_image(image_bytes)
                    else:
                        result = self.send_to_wechat(content)
                elif channel == NotificationChannel.FEISHU:
                    result = self.send_to_feishu(content)
                elif channel == NotificationChannel.TELEGRAM:
                    if use_image:
                        result = self._send_telegram_photo(image_bytes)
                    else:
                        result = self.send_to_telegram(content)
                elif channel == NotificationChannel.EMAIL:
                    if use_image:
                        result = self._send_email_with_inline_image(
                            image_bytes, receivers=None
                        )
                    else:
                        result = self.send_to_email(content, receivers=None)
                elif channel == NotificationChannel.PUSHOVER:
                    result = self.send_to_pushover(content)
                elif channel == NotificationChannel.PUSHPLUS:
                    result = self.send_to_pushplus(content)
                elif channel == NotificationChannel.SERVERCHAN3:
                    result = self.send_to_serverchan3(content)
                elif channel == NotificationChannel.CUSTOM:
                    if use_image:
                        result = self._send_custom_webhook_image(
                            image_bytes, fallback_content=content
                        )
                    else:
                        result = self.send_to_custom(content)
                elif channel == NotificationChannel.DISCORD:
                    result = self.send_to_discord(content)
                elif channel == NotificationChannel.SLACK:
                    if use_image:
                        result = self._send_slack_image(
                            image_bytes, fallback_content=content
                        )
                    else:
                        result = self.send_to_slack(content)
                elif channel == NotificationChannel.ASTRBOT:
                    result = self.send_to_astrbot(content)
                else:
                    logger.warning(f"不支持的通知渠道: {channel}")
                    result = False

                if result:
                    success_count += 1
                else:
                    fail_count += 1

            except Exception as e:
                logger.error(f"{channel_name} 发送失败: {e}")
                fail_count += 1

        logger.info(f"通知发送完成：成功 {success_count} 个，失败 {fail_count} 个")
        return success_count > 0

    def save_report_to_file(
        self,
        content: str,
        filename: Optional[str] = None
    ) -> str:
        """
        保存日报到本地文件

        Args:
            content: 日报内容
            filename: 文件名（可选，默认按日期生成）

        Returns:
            保存的文件路径
        """
        from pathlib import Path

        if filename is None:
            date_str = datetime.now().strftime('%Y%m%d')
            filename = f"digest_{date_str}.md"

        # 确保 reports 目录存在（使用项目根目录下的 reports）
        reports_dir = Path(__file__).parent.parent / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)

        filepath = reports_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"报告已保存到: {filepath}")
        return str(filepath)


# 便捷函数
def get_notification_service() -> NotificationService:
    """获取通知服务实例"""
    return NotificationService()


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)

    service = NotificationService()

    # 显示检测到的渠道
    print("=== 通知渠道检测 ===")
    print(f"当前渠道: {service.get_channel_names()}")
    print(f"渠道列表: {service.get_available_channels()}")
    print(f"服务可用: {service.is_available()}")

    # 发送测试消息
    if service.is_available():
        test_content = "# 🧪 AI News Digest 测试\n\n这是一条测试消息。"
        print(f"\n=== 推送测试（{service.get_channel_names()}）===")
        success = service.send(test_content)
        print(f"推送结果: {'成功' if success else '失败'}")
    else:
        print("\n通知渠道未配置，跳过推送测试")
