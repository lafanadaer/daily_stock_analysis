# -*- coding: utf-8 -*-
"""
===================================
API 依赖注入模块
===================================

职责：
1. 提供配置依赖
2. 提供服务层依赖
"""

from fastapi import Request
from src.config import get_config, Config
from src.services.system_config_service import SystemConfigService


def get_config_dep() -> Config:
    """获取配置依赖"""
    return get_config()


def get_system_config_service(request: Request) -> SystemConfigService:
    """Get app-lifecycle shared SystemConfigService instance."""
    service = getattr(request.app.state, "system_config_service", None)
    if service is None:
        service = SystemConfigService()
        request.app.state.system_config_service = service
    return service
