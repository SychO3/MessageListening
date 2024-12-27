import os

from pyrogram import Client, filters, types, helpers, errors, enums
import logging
from config import (
    API_ID, API_HASH, BOT_TOKEN,ADMIN_IDS,
    SESSIONS_FILE, KEYWORDS_FILE, load_json, save_json
)
from db import block_user

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_text():
    return "欢迎使用关键词监听机器人！"

async def start_markup():
    return helpers.ikb(
        [
            [
                ("添加监听号", "user_add"),
                ("删除监听号", "user_del"),
                ("查看监听号", "user_list"),

            ],
            [
                ("添加关键词", "keyword_add"),
                ("删除关键词", "keyword_del"),
                ("查看关键词", "keyword_list"),
            ]
        ]
    )

@Client.on_message(filters.command("start")&filters.private)
async def start(client:Client,message:types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    text = await start_text()
    markup = await start_markup()
    await message.reply_text(text,reply_markup=markup,quote=False)


@Client.on_callback_query(filters.regex("user"))
async def handle_user(client: Client, callback: types.CallbackQuery):
    command = callback.data.split("_")
    try:
        if not command:
            await callback.edit_message_text(
                text=await start_text(),
                reply_markup=await start_markup()
            )
            return

        markup_cancel = helpers.ikb([[("🚫 取消", "user_start")]])
        # 返回
        markup_return = helpers.ikb([[("🔙 返回", "user_start")]])

        if command[1] == "add":
            # 1. 请求输入手机号
            message = await callback.edit_message_text(
                text="请输入要添加的监听号**手机号码**\n格式示例：+8612345678901",
                reply_markup=markup_cancel
            )

            phone_input = await client.listen(
                chat_id=callback.from_user.id,
                filters=filters.text,
                timeout=120
            )
            phone_number = phone_input.text.strip()

            await phone_input.delete()
            await message.edit_text("正在发送验证码，请稍候...", reply_markup=None)

            # 2. 创建新的客户端实例
            account = Client(
                name=f"user_{phone_number.replace('+', '')}",
                api_id=API_ID,
                api_hash=API_HASH,
                workdir="data",
                phone_number=phone_number
            )

            # 3. 连接并发送验证码
            await account.connect()
            try:
                sent_code = await account.send_code(phone_number)
                logger.info(f"验证码已发送: {sent_code.type}")

                # 4. 等待输入验证码
                await message.edit_text(
                    text=f"已发送验证码到 **{phone_number}**\n请在2分钟内输入验证码",
                    reply_markup=markup_cancel
                )

                code_input = await client.listen(
                    chat_id=callback.from_user.id,
                    filters=filters.text,
                    timeout=120
                )

                phone_code = code_input.text.strip()
                await code_input.delete()


                # 5. 尝试登录
                try:
                    signed_in = await account.sign_in(
                        phone_number=phone_number,
                        phone_code_hash=sent_code.phone_code_hash,
                        phone_code=phone_code
                    )

                    # 保存会话信息
                    sessions = load_json(SESSIONS_FILE, default=[])
                    session_info = {
                        "phone": phone_number,
                        "user_id": signed_in.id,
                        "username": signed_in.username,
                        "name": signed_in.full_name,
                        "session_file": f"data/user_{phone_number.replace('+', '')}.session"
                    }
                    
                    # 如果已存在相同手机号，则更新信息
                    for i, session in enumerate(sessions):
                        if session["phone"] == phone_number:
                            sessions[i] = session_info
                            break
                    else:
                        sessions.append(session_info)
                    
                    save_json(SESSIONS_FILE, sessions)

                    user_info = f"**用户信息**\n\n"
                    user_info += f"ID: `{signed_in.id}`\n"
                    if signed_in.username:
                        user_info += f"用户名: @{signed_in.username}\n"
                    user_info += f"姓名: {signed_in.full_name}\n"

                    await message.edit_text(
                        text=f"✅ 监听号 **{phone_number}** 添加成功！\n\n{user_info}",
                        reply_markup=markup_return
                    )

                    # await account.disconnect()
                    return

                except errors.SessionPasswordNeeded:
                    # 6. 处理两步验证
                    await message.edit_text(
                        text=f"需要两步验证密码\n提示：{await account.get_password_hint() or '无提示'}",
                        reply_markup=markup_cancel
                    )

                    password_input = await client.listen(
                        chat_id=callback.from_user.id,
                        filters=filters.text,
                        timeout=120
                    )

                    password = password_input.text.strip()
                    await password_input.delete()

                    try:
                        signed_in = await account.check_password(password)
                        
                        # 保存会话信息
                        sessions = load_json(SESSIONS_FILE, default=[])
                        session_info = {
                            "phone": phone_number,
                            "user_id": signed_in.id,
                            "username": signed_in.username,
                            "name": signed_in.full_name,
                            "session_file": f"data/user_{phone_number.replace('+', '')}.session"
                        }
                        
                        # 如果已存在相同手机号，则更新信息
                        for i, session in enumerate(sessions):
                            if session["phone"] == phone_number:
                                sessions[i] = session_info
                                break
                        else:
                            sessions.append(session_info)
                        
                        save_json(SESSIONS_FILE, sessions)

                        user_info = f"**用户信息**\n\n"
                        user_info += f"ID: `{signed_in.id}`\n"
                        if signed_in.username:
                            user_info += f"用户名: @{signed_in.username}\n"
                        user_info += f"姓名: {signed_in.full_name}\n"
                        await message.edit_text(
                            text=f"✅ 监听号 **{phone_number}** 添加成功！\n\n{user_info}",
                            reply_markup=markup_return
                        )
                        await account.disconnect()
                        return
                    except errors.BadRequest:
                        await message.edit_text(
                            text=f"⚠️ 输入超时、或密码错误，请重新尝试",
                            reply_markup=markup_return
                        )
                        os.remove(f"data/user_{phone_number.replace('+', '')}.session")

                except errors.PhoneCodeExpired:
                    await message.edit_text(
                        text="⚠️ 验证码已过期，请重新获取",
                        reply_markup=markup_return
                    )
                    os.remove(f"data/user_{phone_number.replace('+', '')}.session")
                except errors.PhoneCodeInvalid:
                    await message.edit_text(
                        text="⚠️ 验证码错误，请检查后重试",
                        reply_markup=markup_return
                    )
                    os.remove(f"data/user_{phone_number.replace('+', '')}.session")
                except errors.BadRequest as e:
                    await message.edit_text(
                        text=f"⚠️ 登录失败：{str(e)}",
                        reply_markup=markup_return
                    )
                    os.remove(f"data/user_{phone_number.replace('+', '')}.session")

            except Exception as e:
                logger.error(f"登录过程错误: {str(e)}")
                await message.edit_text(
                    text=f"❌ 错误：{str(e)}",
                    reply_markup=markup_return
                )
                os.remove(f"data/user_{phone_number.replace('+', '')}.session")
            finally:
                if account and account.is_connected:
                    await account.disconnect()

                
        elif command[1] == "del":
            # 加载现有会话
            sessions = load_json(SESSIONS_FILE, default=[])
            if not sessions:
                await callback.answer(
                    text="📱 暂无监听号",
                    show_alert=True
                )
                return

            # 创建删除按钮
            buttons = []
            for session in sessions:
                phone = session["phone"]
                name = session.get("name", "未命名")
                username = f" (@{session['username']})" if session.get("username") else ""
                buttons.append(
                    [(f"📱 {name}{username}", f"user_delok_{phone}")]
                )
            buttons.append([("🔙 返回", "user_start")])

            await callback.edit_message_text(
                text="选择要删除的监听号：",
                reply_markup=helpers.ikb(buttons)
            )
            return

        elif command[1] == "delok":
            # 处理删除确认
            phone = command[2]
            sessions = load_json(SESSIONS_FILE, default=[])
            
            # 查找要删除的会话
            session_to_delete = None
            for session in sessions:
                if session["phone"] == phone:
                    session_to_delete = session
                    break
            
            if not session_to_delete:
                await callback.edit_message_text(
                    text="❌ 未找到该监听号",
                    reply_markup=markup_return
                )
                return

            # 创建确认按钮
            name = session_to_delete.get("name", "未命名")
            username = f" (@{session_to_delete['username']})" if session_to_delete.get("username") else ""
            confirm_buttons = [
                [("⚠️ 确认删除", f"user_delconfirm_{phone}"), ("🔙 返回", "user_del")]
            ]

            await callback.edit_message_text(
                text=f"确认删除以下监听号？\n\n"
                     f"📱 {name}{username}\n",
                     # f"☎️ {phone}",
                reply_markup=helpers.ikb(confirm_buttons)
            )
            return

        elif command[1] == "delconfirm":
            # 执行删除操作
            phone = command[2]
            sessions = load_json(SESSIONS_FILE, default=[])
            
            # 删除 session 文件
            session_file = f"data/user_{phone.replace('+', '')}.session"
            if os.path.exists(session_file):
                os.remove(session_file)
                logger.info(f"已删除会话文件：{session_file}")

            # 更新 sessions.json
            sessions = [s for s in sessions if s["phone"] != phone]
            save_json(SESSIONS_FILE, sessions)
            
            await callback.edit_message_text(
                text=f"✅ 监听号 {phone} 已删除",
                reply_markup=markup_return
            )
            return

        elif command[1] == "list":
            sessions = load_json(SESSIONS_FILE, default=[])
            if not sessions:
                await callback.answer(
                    text="📱 暂无监听号",
                    show_alert=True
                )
                return

            # 生成监听号列表
            text = "**当前监听号列表**\n\n"
            for i, session in enumerate(sessions, 1):
                name = session.get("name", "未命名")
                username = f" (@{session['username']})" if session.get("username") else ""
                phone = session["phone"]
                text += f"{i}. {name}{username}\n"
                # text += f"   ☎️ {phone}\n"
                text += f"   🆔 `{session['user_id']}`\n\n"

            await callback.edit_message_text(
                text=text,
                reply_markup=markup_return
            )
            return
        elif command[1] == "start":
            await client.stop_listening(chat_id=callback.from_user.id)
            await callback.edit_message_text(
                text=await start_text(),
                reply_markup=await start_markup()
            )
            
    except Exception as e:
        logger.error(f"处理用户命令错误: {str(e)}")

@Client.on_callback_query(filters.regex("keyword"))
async def handle_keyword(client: Client, callback: types.CallbackQuery):
    command = callback.data.split("_")
    try:
        if not command:
            await callback.edit_message_text(
                text=await start_text(),
                reply_markup=await start_markup()
            )
            return

        markup_cancel = helpers.ikb([[("🚫 取消", "keyword_start")]])
        markup_return = helpers.ikb([[("🔙 返回", "keyword_start")]])

        if command[1] == "add":
            # 1. 选择匹配模式
            match_buttons = [
                [("🎯 完全匹配", "keyword_addtype_exact")],
                [("🔍 模糊匹配", "keyword_addtype_fuzzy")],
                [("🔙 返回", "keyword_start")]
            ]
            await callback.edit_message_text(
                text="请选择关键词匹配模式：\n\n"
                     "🎯 完全匹配：必须与消息内容完全一致\n"
                     "🔍 模糊匹配：消息内容包含关键词即可",
                reply_markup=helpers.ikb(match_buttons)
            )
            return

        elif command[1] == "addtype":
            match_type = command[2]  # exact 或 fuzzy
            await callback.edit_message_text(
                text="请输入要添加的关键词：",
                reply_markup=markup_cancel
            )

            try:
                keyword_input = await client.listen(
                    chat_id=callback.from_user.id,
                    filters=filters.text,
                    timeout=120
                )

                keyword = keyword_input.text.strip()
                await keyword_input.delete()

                # 加载现有关键词
                keywords = load_json(KEYWORDS_FILE, default={"exact": [], "fuzzy": []})
                
                # 检查关键词是否已存在
                if keyword in keywords["exact"] or keyword in keywords["fuzzy"]:
                    await callback.edit_message_text(
                        text="⚠️ 该关键词已存在",
                        reply_markup=markup_return
                    )
                    return

                # 添加关键词
                keywords[match_type].append(keyword)
                save_json(KEYWORDS_FILE, keywords)

                await callback.edit_message_text(
                    text=f"✅ 关键词添加成功！\n"
                         f"关键词：{keyword}\n"
                         f"匹配模式：{'完全匹配' if match_type == 'exact' else '模糊匹配'}",
                    reply_markup=markup_return
                )

            except TimeoutError:
                await callback.edit_message_text(
                    text="⏰ 操作超时，请重新开始",
                    reply_markup=markup_return
                )

        elif command[1] == "del":
            # 加载关键词列表
            keywords = load_json(KEYWORDS_FILE, default={"exact": [], "fuzzy": []})
            
            if not keywords["exact"] and not keywords["fuzzy"]:
                await callback.answer(
                    text="📝 暂无关键词",
                    show_alert=True
                )
                return

            # 创建删除按钮
            buttons = []
            for keyword in keywords["exact"]:
                buttons.append([(f"🎯 {keyword}", f"keyword_delok_exact_{keyword}")])
            for keyword in keywords["fuzzy"]:
                buttons.append([(f"🔍 {keyword}", f"keyword_delok_fuzzy_{keyword}")])
            buttons.append([("🔙 返回", "keyword_start")])

            await callback.edit_message_text(
                text="选择要删除的关键词：\n"
                     "🎯 完全匹配  🔍 模糊匹配",
                reply_markup=helpers.ikb(buttons)
            )
            return

        elif command[1] == "delok":
            # 处理删除确认
            match_type = command[2]
            keyword = command[3]
            
            confirm_buttons = [
                [("⚠️ 确认删除", f"keyword_delconfirm_{match_type}_{keyword}"), 
                 ("🔙 返回", "keyword_del")]
            ]

            match_type_text = "完全匹配" if match_type == "exact" else "模糊匹配"
            await callback.edit_message_text(
                text=f"确认删除以下关键词？\n\n"
                     f"关键词：{keyword}\n"
                     f"匹配模式：{match_type_text}",
                reply_markup=helpers.ikb(confirm_buttons)
            )
            return

        elif command[1] == "delconfirm":
            # 执行删除操作
            match_type = command[2]
            keyword = command[3]
            
            keywords = load_json(KEYWORDS_FILE, default={"exact": [], "fuzzy": []})
            if keyword in keywords[match_type]:
                keywords[match_type].remove(keyword)
                save_json(KEYWORDS_FILE, keywords)
            
            await callback.edit_message_text(
                text=f"✅ 关键词已删除",
                reply_markup=markup_return
            )
            return

        elif command[1] == "list":
            keywords = load_json(KEYWORDS_FILE, default={"exact": [], "fuzzy": []})
            
            if not keywords["exact"] and not keywords["fuzzy"]:
                await callback.answer(
                    text="📝 暂无关键词",
                    show_alert=True
                )
                return

            # 生成关键词列表
            text = "**当前关键词列表**\n\n"
            
            if keywords["exact"]:
                text += "🎯 **完全匹配**\n"
                for i, keyword in enumerate(keywords["exact"], 1):
                    text += f"{i}. {keyword}\n"
                text += "\n"
            
            if keywords["fuzzy"]:
                text += "🔍 **模糊匹配**\n"
                for i, keyword in enumerate(keywords["fuzzy"], 1):
                    text += f"{i}. {keyword}\n"

            await callback.edit_message_text(
                text=text,
                reply_markup=markup_return
            )
            return

        elif command[1] == "start":
            await client.stop_listening(chat_id=callback.from_user.id)
            await callback.edit_message_text(
                text=await start_text(),
                reply_markup=await start_markup()
            )

    except Exception as e:
        logger.error(f"处理关键词命令错误: {str(e)}")

@Client.on_callback_query()
async def handle_callback(client: Client, callback_query: types.CallbackQuery):
    """处理回调查询"""
    data = callback_query.data
    
    # 处理拉黑操作
    if data.startswith('block_'):
        try:
            user_id = int(data.split('_')[1])
            if block_user(user_id):
                await callback_query.answer("✅ 已将该用户加入黑名单")
                # 编辑消息，移除按钮
                await callback_query.edit_message_reply_markup(None)
            else:
                await callback_query.answer("❌ 加入黑名单失败")
        except Exception as e:
            logger.error(f"处理拉黑回调失败: {e}")
            await callback_query.answer("❌ 操作失败")
    else:
        await callback_query.answer()
