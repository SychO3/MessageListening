import asyncio
import json
import logging
from typing import Dict

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from db import get_messages, mark_as_pushed, is_user_blocked, block_user
from config import ADMIN_IDS

# 配置日志
logger = logging.getLogger(__name__)

PUSH_INTERVAL = 1  # 每1秒检查一次

# 匹配类型映射
MATCH_TYPE_MAP = {
    'exact': '🎯',
    'fuzzy': '🔍'
}

def get_callback_data(action: str, msg: Dict) -> str:
    """生成回调数据"""
    data = {
        "a": action,  # action
        "u": msg['sender_username'],  # username
        "c": msg['chat_id'],  # chat_id
        "m": msg['message_id']  # message_id
    }
    return json.dumps(data)

def get_keyboard(msg: Dict) -> InlineKeyboardMarkup:
    """获取键盘按钮"""
    buttons = []
    
    # 如果有用户名，添加发消息链接
    if msg['sender_username']:
        buttons.append(
            InlineKeyboardButton(
                "💬 发消息",
                url=f"https://t.me/{msg['sender_username']}"
            )
        )
    
    # 添加拉黑按钮
    buttons.append(
        InlineKeyboardButton(
            "⛔️ 拉黑",
            callback_data=f"block_{msg['sender_id']}"
        )
    )
    
    return InlineKeyboardMarkup([buttons])

async def format_message(msg: Dict) -> str:
    """格式化消息"""
    chat_link = f"https://t.me/{msg['chat_username']}/{msg['message_id']}" if msg['chat_username'] else None
    match_type = MATCH_TYPE_MAP.get(msg['match_type'], msg['match_type'])
    
    # 格式化发送者信息
    sender_info = msg['sender_name'] or '未知'
    if msg['sender_username']:
        sender_info += f" (@{msg['sender_username']})"
    
    # 格式化群组信息
    chat_info = msg['chat_title']
    if msg['chat_username']:
        chat_info += f" (@{msg['chat_username']})"
    
    lines = [
        f"🔍 **关键词**: `{msg['matched_keyword']}` __{match_type}__",
        f"👥 **来源**: {chat_info}",
        f"👤 **发送者**: {sender_info}",
        f"📝 **内容**:  \n <blockquote> {msg['message_text']}</blockquote>\n",
    ]
    
    if chat_link:
        lines.append(f"🔗 **链接**: {chat_link}")
    
    return "\n".join(lines)

async def push_task(client: Client):
    """推送任务"""
    try:
        # 获取未推送的消息
        messages = get_messages(is_pushed=False)
        if not messages:
            return
        
        # 推送消息
        for msg in messages:
            try:
                # 如果发送者在黑名单中，直接标记为已推送并跳过
                if msg['sender_id'] and is_user_blocked(msg['sender_id']):
                    mark_as_pushed(
                        client_id=msg['client_id'],
                        chat_id=msg['chat_id'],
                        message_id=msg['message_id']
                    )
                    continue
                
                text = await format_message(msg)
                keyboard = get_keyboard(msg)
                
                # 推送给所有管理员
                for admin_id in ADMIN_IDS:
                    try:
                        await client.send_message(
                            admin_id, 
                            text, 
                            disable_web_page_preview=True,
                            reply_markup=keyboard
                        )
                    except Exception as e:
                        logger.error(f"向管理员 {admin_id} 推送失败: {e}")
                        continue
                
                # 标记为已推送
                if mark_as_pushed(
                    client_id=msg['client_id'],
                    chat_id=msg['chat_id'],
                    message_id=msg['message_id']
                ):
                    logger.info(f"消息推送成功: {msg['chat_title']} - {msg['matched_keyword']}")
                
                # 避免频率限制
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"消息推送失败: {e}")
                await asyncio.sleep(5)  # 出错后多等待一会
                
    except Exception as e:
        logger.error(f"推送任务异常: {e}")