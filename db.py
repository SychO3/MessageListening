import os
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict

def get_conn():
    db_path = os.path.join("data", "messages.db")
    return sqlite3.connect(db_path)

def init_db():
    """初始化数据库"""
    conn = get_conn()
    c = conn.cursor()
    
    # 创建消息表
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            chat_title TEXT,
            chat_type TEXT NOT NULL,
            chat_username TEXT,
            sender_id INTEGER,
            sender_username TEXT,
            sender_name TEXT,
            message_id INTEGER NOT NULL,
            message_text TEXT,
            matched_keyword TEXT NOT NULL,
            match_type TEXT NOT NULL,
            message_date DATETIME NOT NULL,
            is_pushed BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(client_id, chat_id, message_id)
        )
    ''')
    
    # 创建黑名单表
    c.execute('''
        CREATE TABLE IF NOT EXISTS blacklist (
            user_id INTEGER PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_message(
    client_id: int, chat_id: int, chat_title: str,
    chat_type: str, chat_username: Optional[str],
    sender_id: Optional[int], sender_username: Optional[str],
    sender_name: Optional[str], message_id: int,
    message_text: str, matched_keyword: str,
    match_type: str, message_date: datetime,
    is_pushed: bool = False
) -> bool:
    """保存匹配的消息到数据库，返回是否保存成功"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT INTO messages (
            client_id, chat_id, chat_title, chat_type,
            chat_username, sender_id, sender_username, sender_name,
            message_id, message_text, matched_keyword, match_type,
            message_date, is_pushed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            client_id, chat_id, chat_title, chat_type,
            chat_username, sender_id, sender_username, sender_name,
            message_id, message_text, matched_keyword, match_type,
            message_date.isoformat(), is_pushed
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # 消息已存在
        return False
    finally:
        conn.close()

def mark_as_pushed(client_id: int, chat_id: int, message_id: int) -> bool:
    """标记消息为已推送"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        UPDATE messages SET is_pushed = 1
        WHERE client_id = ? AND chat_id = ? AND message_id = ?
        ''', (client_id, chat_id, message_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def get_messages(
    keyword: Optional[str] = None,
    match_type: Optional[str] = None,
    chat_id: Optional[int] = None,
    sender_id: Optional[int] = None,
    is_pushed: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100
) -> List[Dict]:
    """查询匹配的消息"""
    conn = get_conn()
    cursor = conn.cursor()
    
    query = "SELECT * FROM messages WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND matched_keyword = ?"
        params.append(keyword)
    
    if match_type:
        query += " AND match_type = ?"
        params.append(match_type)
    
    if chat_id:
        query += " AND chat_id = ?"
        params.append(chat_id)
    
    if sender_id:
        query += " AND sender_id = ?"
        params.append(sender_id)
    
    if is_pushed is not None:
        query += " AND is_pushed = ?"
        params.append(1 if is_pushed else 0)
    
    if start_date:
        query += " AND message_date >= ?"
        params.append(start_date.isoformat())
    
    if end_date:
        query += " AND message_date <= ?"
        params.append(end_date.isoformat())
    
    query += " ORDER BY message_date DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    # 获取列名
    columns = [description[0] for description in cursor.description]
    
    # 转换为字典列表
    results = []
    for row in rows:
        result = dict(zip(columns, row))
        # 转换时间字符串为datetime对象
        result['message_date'] = datetime.fromisoformat(result['message_date'])
        result['created_at'] = datetime.fromisoformat(result['created_at'])
        # 转换布尔值
        result['is_pushed'] = bool(result['is_pushed'])
        results.append(result)
    
    conn.close()
    return results

def is_user_blocked(user_id: int) -> bool:
    """检查用户是否在黑名单中"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT 1 FROM blacklist WHERE user_id = ?', (user_id,))
    result = c.fetchone() is not None
    conn.close()
    return result

def block_user(user_id: int) -> bool:
    """将用户加入黑名单"""
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO blacklist (user_id) VALUES (?)', (user_id,))
        
        # 标记该用户的所有未推送消息为已推送
        c.execute('''
            UPDATE messages 
            SET is_pushed = 1 
            WHERE sender_id = ? AND is_pushed = 0
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"加入黑名单失败: {e}")
        return False

# 初始化数据库
init_db()
