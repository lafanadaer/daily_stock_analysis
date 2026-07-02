# -*- coding: utf-8 -*-
"""
===================================
AI News Digest
===================================

职责：
1. 抓取技术博客 RSS，LLM 评分/摘要，生成日报
2. 通过配置的通知渠道推送
3. 支持定时调度（默认每 48 小时）

使用方式：
    python main.py                    # 单次运行
    python main.py --debug            # 调试模式
    python main.py --no-notify        # 不发送推送通知
    python main.py --schedule         # 定时任务模式
    python main.py --serve            # 启动 API 服务
"""
import os
from src.config import setup_env
setup_env()

# 代理配置
if os.getenv("GITHUB_ACTIONS") != "true" and os.getenv("USE_PROXY", "false").lower() == "true":
    proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
    proxy_port = os.getenv("PROXY_PORT", "10809")
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url

import argparse
import logging
import sys
import time
from datetime import datetime

from src.config import get_config, Config
from src.logging_config import setup_logging

logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='AI News Digest',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python main.py                    # 单次运行
  python main.py --debug            # 调试模式
  python main.py --no-notify        # 不发送推送通知
  python main.py --schedule         # 定时任务模式
        '''
    )

    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--no-notify', action='store_true', help='不发送推送通知')
    parser.add_argument('--schedule', action='store_true', help='启用定时任务模式')
    parser.add_argument('--no-run-immediately', action='store_true', help='定时任务启动时不立即执行')

    parser.add_argument('--serve', action='store_true', help='启动 FastAPI 后端服务')
    parser.add_argument('--serve-only', action='store_true', help='仅启动 FastAPI 服务')
    parser.add_argument('--port', type=int, default=8000, help='服务端口（默认 8000）')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址（默认 0.0.0.0）')

    return parser.parse_args()


def run_ai_daily_digest(config: Config, args: argparse.Namespace) -> None:
    """Run the AI Daily Digest pipeline and send notifications."""
    logger.info("Starting AI Daily Digest...")
    from src.services.ai_daily_digest import AIDailyDigestService
    from src.notification import NotificationService

    digest_service = AIDailyDigestService()
    report = digest_service.run()

    if report and not getattr(args, 'no_notify', False):
        notifier = NotificationService()
        if notifier.is_available():
            notifier.send(report)
            logger.info("AI Daily Digest sent successfully")
        else:
            logger.warning("No notification channels configured, report not sent")
    elif not report:
        logger.warning("AI Daily Digest produced no report")

    return report or ""


def start_api_server(host: str, port: int, config: Config) -> None:
    """在后台线程启动 FastAPI 服务"""
    import threading
    import uvicorn

    def run_server():
        level_name = (config.log_level or "INFO").lower()
        uvicorn.run(
            "api.app:app",
            host=host,
            port=port,
            log_level=level_name,
            log_config=None,
        )

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    logger.info(f"FastAPI 服务已启动: http://{host}:{port}")


def main() -> int:
    """主入口函数"""
    args = parse_arguments()
    config = get_config()

    # 配置日志
    setup_logging(log_prefix="ai_news_digest", debug=args.debug, log_dir=config.log_dir)

    logger.info("=" * 60)
    logger.info("AI News Digest")
    logger.info(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"推送间隔: {config.ai_daily_digest_interval_hours}h")
    logger.info("=" * 60)

    # 验证配置
    warnings = config.validate()
    for warning in warnings:
        logger.warning(warning)

    # 仅 Web 服务模式
    if args.serve_only:
        start_api_server(host=args.host, port=args.port, config=config)
        logger.info(f"API 服务运行中: http://{args.host}:{args.port}")
        logger.info(f"API 文档: http://{args.host}:{args.port}/docs")
        logger.info("按 Ctrl+C 退出...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n用户中断，程序退出")
        return 0

    try:
        # 启动 API 服务（如果启用）
        if args.serve:
            start_api_server(host=args.host, port=args.port, config=config)

        # 定时任务模式
        if args.schedule or config.schedule_enabled:
            logger.info("模式: 定时任务")
            should_run_immediately = config.schedule_run_immediately
            if getattr(args, 'no_run_immediately', False):
                should_run_immediately = False

            from src.scheduler import run_with_schedule
            run_with_schedule(
                task=lambda: run_ai_daily_digest(config, args),
                schedule_time=config.schedule_time,
                run_immediately=should_run_immediately,
                interval_hours=config.ai_daily_digest_interval_hours,
            )
            return 0

        # 单次运行
        logger.info("模式: 单次运行")
        run_ai_daily_digest(config, args)
        logger.info("\n程序执行完成")

        # 如果启用了 API 且非定时模式，保持运行
        if args.serve and not (args.schedule or config.schedule_enabled):
            logger.info("API 服务运行中 (按 Ctrl+C 退出)...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

        return 0

    except KeyboardInterrupt:
        logger.info("\n用户中断，程序退出")
        return 130
    except Exception as e:
        logger.exception(f"程序执行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
