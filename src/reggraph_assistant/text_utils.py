"""文本处理工具

统一的分词和文本处理函数
"""
from __future__ import annotations

import re


# 统一的 token 正则表达式（支持英文、数字、下划线和中文）
TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+|[一-鿿]")


def tokenize(text: str) -> list[str]:
    """分词函数（支持中英文）

    Args:
        text: 输入文本

    Returns:
        token 列表（包含原始 token 和中文 bigram）

    Examples:
        >>> tokenize("hello 世界")
        ['hello', '世', '界', '世界']
    """
    raw_tokens = TOKEN_PATTERN.findall(text.lower())

    # 提取中文字符
    cjk_chars = [token for token in raw_tokens if len(token) == 1 and "一" <= token <= "鿿"]

    # 生成中文 bigram（提高中文检索精度）
    cjk_bigrams = [f"{left}{right}" for left, right in zip(cjk_chars, cjk_chars[1:])]

    return raw_tokens + cjk_bigrams
