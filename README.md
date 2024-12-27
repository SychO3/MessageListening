# Telegram 关键词监听机器人

这是一个基于 Pyrogram 开发的 Telegram 关键词监听机器人。它可以帮助授权用户在群组中监听特定关键词，并将包含关键词的消息转发给用户。

## 功能特点

- 支持管理员授权用户
- 支持用户自定义关键词
- 实时监听群组消息
- 智能消息转发

## 安装

1. 克隆项目并安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置环境变量：
复制 `.env.example` 文件为 `.env`，并填入以下信息：
- API_ID：你的 Telegram API ID
- API_HASH：你的 Telegram API Hash
- BOT_TOKEN：你的机器人 Token
- ADMIN_ID：管理员的 Telegram 用户 ID

## 使用方法

### 管理员命令
- `/authorize [user_id]` - 授权用户使用机器人
- `/unauthorize [user_id]` - 取消用户授权

### 用户命令
- `/add_keyword [关键词]` - 添加监听关键词
- `/remove_keyword [关键词]` - 删除监听关键词
- `/list_keywords` - 查看所有监听的关键词

## 运行

```bash
python main.py
```
