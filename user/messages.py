import os
from typing import Optional, List, Dict, Tuple

from pyrogram import Client, filters, types, helpers, errors, enums
import logging
from config import (
    API_ID, API_HASH, BOT_TOKEN,
    SESSIONS_FILE, KEYWORDS_FILE, load_json, save_json
)
from db import save_message

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_keywords() -> Tuple[List[str], List[str]]:
    """获取关键词列表，返回 (精确匹配列表, 模糊匹配列表)"""
    keywords = load_json(KEYWORDS_FILE, default={"exact": [], "fuzzy": []})
    return keywords.get("exact", []), keywords.get("fuzzy", [])

def match_keywords(text: str) -> Optional[Tuple[str, str]]:
    """匹配关键词，返回 (匹配到的关键词, 匹配模式)"""
    if not text:
        return None
        
    text = text.lower()
    exact_keywords, fuzzy_keywords = get_keywords()
    
    # 1. 先尝试精确匹配
    for keyword in exact_keywords:
        if keyword.lower() == text:
            return keyword, "exact"
    
    # 2. 再尝试模糊匹配
    for keyword in fuzzy_keywords:
        if keyword.lower() in text:
            return keyword, "fuzzy"
    
    return None

@Client.on_message(filters.group | filters.channel)
async def on_group_message(client:Client, message: types.Message):
    """群组消息处理"""
    # 忽略自己的消息
    if message.from_user and message.from_user.is_self:
        return

    # 获取消息文本
    text = message.text or message.caption or ""
    if not text:
        return

    # 匹配关键词
    match = match_keywords(text)
    if not match:
        return
    
    keyword, match_type = match

    # 保存匹配的消息
    chat_title = message.chat.title or str(message.chat.id)
    chat_username = message.chat.username if hasattr(message.chat, 'username') else None
    
    # 获取发送者信息
    sender = message.from_user
    if sender:
        sender_id = sender.id
        sender_username = sender.username
        sender_name = sender.full_name
    else:
        sender_id = None
        sender_username = None
        sender_name = None

    # 保存消息，如果已存在则跳过
    if save_message(
        client_id=client.me.id,
        chat_id=message.chat.id,
        chat_title=chat_title,
        chat_type=message.chat.type.value,
        chat_username=chat_username,
        sender_id=sender_id,
        sender_username=sender_username,
        sender_name=sender_name,
        message_id=message.id,
        message_text=text,
        matched_keyword=keyword,
        match_type=match_type,
        message_date=message.date
    ):
        logger.info(f"关键词匹配成功[{match_type}]: {chat_title} - {keyword} - {text[:5]}...")