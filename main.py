import logging
import asyncio
from typing import Dict, List

from pyrogram import Client, idle
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from config import (
    API_ID, API_HASH, BOT_TOKEN,
    SESSIONS_FILE, load_json
)
from bot.push import push_task, PUSH_INTERVAL


import os
os.environ['TZ'] = 'Asia/Shanghai'

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 活动的客户端
active_clients: Dict[str, Client] = {}

# 定时任务调度器
scheduler = AsyncIOScheduler(
    jobstores={'default': MemoryJobStore()},
    job_defaults={'misfire_grace_time': 30},
    timezone='Asia/Shanghai'
)

async def start_client(phone: str, name: str = None) -> bool:
    """启动单个客户端"""
    try:
        if phone in active_clients:
            logger.warning(f"监听号 {phone} 已经在运行中")
            return True

        client = Client(
            name=f"user_{phone.replace('+', '')}",
            api_id=API_ID,
            api_hash=API_HASH,
            workdir="data",
            plugins=dict(root="user")
        )
        await client.start()
        active_clients[phone] = client
        logger.info(f"监听号 {phone} ({name or '未命名'}) 已启动")
        return True
    except Exception as e:
        logger.error(f"启动监听号 {phone} 失败: {str(e)}")
        return False

async def stop_client(phone: str) -> bool:
    """停止单个客户端"""
    try:
        if phone not in active_clients:
            logger.warning(f"监听号 {phone} 未在运行")
            return True

        client = active_clients[phone]
        await client.stop()
        del active_clients[phone]
        logger.info(f"监听号 {phone} 已停止")
        return True
    except Exception as e:
        logger.error(f"停止监听号 {phone} 失败: {str(e)}")
        return False

async def check_sessions() -> None:
    """检查 sessions.json 的变化"""
    try:
        # 读取当前配置的监听号
        sessions = load_json(SESSIONS_FILE, default=[])
        configured_phones = {s['phone']: s.get('name') for s in sessions}
        active_phones = set(active_clients.keys())

        # 停止已删除的监听号
        for phone in active_phones - configured_phones.keys():
            await stop_client(phone)

        # 启动新添加的监听号
        for phone, name in configured_phones.items():
            if phone not in active_phones:
                await start_client(phone, name)

    except Exception as e:
        logger.error(f"检查监听号状态失败: {str(e)}")

async def main():
    # 创建所有客户端
    bot = Client(
        "bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        workdir="data",
        plugins=dict(root="bot")
    )

    # 启动机器人
    await bot.start()
    logger.info("机器人已启动")

    # 启动所有监听号
    await check_sessions()

    # 启动定时任务
    scheduler.add_job(
        check_sessions,
        trigger=IntervalTrigger(seconds=30),
        id='check_sessions',
        name='检查监听号状态',
        replace_existing=True,
        coalesce=True,
        max_instances=1
    )
    
    # 添加推送任务
    scheduler.add_job(
        push_task,
        trigger=IntervalTrigger(seconds=PUSH_INTERVAL),
        id='push_messages',
        name='推送匹配消息',
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        args=[bot]  # 传入机器人客户端
    )
    
    scheduler.start()
    logger.info("定时任务已启动")

    try:
        await idle()
    finally:
        # 停止定时任务
        scheduler.shutdown(wait=False)
        logger.info("定时任务已停止")

        # 停止所有监听号
        for phone in list(active_clients.keys()):
            await stop_client(phone)
        logger.info("所有监听号已停止")

        # 停止机器人
        await bot.stop()
        logger.info("机器人已停止")

if __name__ == "__main__":
    asyncio.run(main())
