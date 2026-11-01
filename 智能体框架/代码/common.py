"""公共配置：所有示例共用。

用法：
    from common import get_model, get_small_model, settings
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# 自动加载 代码/.env
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


@dataclass(frozen=True)
class Settings:
    api_key: str = _env("OPENAI_API_KEY")
    base_url: str = _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model: str = _env("OPENAI_MODEL", "gpt-4o-mini")
    small_model: str = _env("SMALL_MODEL", "gpt-4o-mini")

    embed_provider: str = _env("EMBED_PROVIDER", "local")
    embed_model: str = _env("EMBED_MODEL", "BAAI/bge-m3")

    pg_uri: str = _env("PG_URI", "")
    order_api: str = _env("ORDER_API", "http://localhost:8080/api")


settings = Settings()


def check_env() -> None:
    """运行前检查，给出比 ImportError 友好的提示。"""
    if not settings.api_key or settings.api_key.startswith("sk-your"):
        raise SystemExit(
            "\n[配置缺失] 请先把 代码/.env.example 复制成 代码/.env，并填入 OPENAI_API_KEY\n"
            "  cp .env.example .env   （在 智能体框架/代码 目录下执行）\n"
        )


def get_model(temperature: float = 0.0, **kwargs):
    """主模型。init_chat_model 会自动读 OPENAI_API_KEY / OPENAI_BASE_URL。"""
    check_env()
    from langchain.chat_models import init_chat_model

    return init_chat_model(settings.model, temperature=temperature, **kwargs)


def get_small_model(temperature: float = 0.0, **kwargs):
    """小模型：用于分类、摘要、改写这类"便宜活"。"""
    check_env()
    from langchain.chat_models import init_chat_model

    return init_chat_model(settings.small_model, temperature=temperature, **kwargs)


def print_divider(title: str = "") -> None:
    line = "=" * 60
    print(f"\n{line}")
    if title:
        print(f"  {title}")
        print(line)
    print()
