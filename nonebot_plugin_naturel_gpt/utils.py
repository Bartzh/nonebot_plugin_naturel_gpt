﻿import hashlib
from typing import Dict, Optional, Tuple, Union
import asyncio
import requests
import aiohttp

#import warnings

from logger import logger 

from plyer import notification # type: ignore

#from nonebot.matcher import Matcher
#from nonebot.adapters import Bot
#from nonebot.adapters import Event
#from nonebot.rule import Rule
#from nonebot.permission import SUPERUSER
#from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
#from nonebot.adapters.onebot.v11 import Message, MessageEvent, PrivateMessageEvent, GroupMessageEvent, MessageSegment, GroupIncreaseNoticeEvent

from config import config

#try:
#    import ujson as json
#except ImportError:
#    import json

import json, mss, re, base64, mimetypes # type: ignore

'''def to_me():
    warnings.warn("this function is deprecated", DeprecationWarning)
    if config.NG_TO_ME:
        from nonebot.rule import to_me

        return to_me()

    async def _to_me() -> bool:
        return True

    return Rule(_to_me)
'''
async def default_permission_check_func(user_id:str, chat_type:str, cmd:Optional[str], type:str = 'cmd') -> Tuple[bool, Optional[str]]:
    """默认权限检查函数"""
    if not cmd: # 非命令调用
        return (True, None)

    #if not hasattr(event, 'user_id'): # 获取不到 user_id 字段默认返回成功
    #    return (True, None)
    #else:
    #    user_id = str(getattr(event, 'user_id'))

    #if user_id == bot.self_id: # bot 在控制自己，永远有权限
    #    return (True, None)

    cmd_list = [c.strip() for c in cmd.split(' ') if c.strip()]
    if(len(cmd_list) == 0): # rg
        return (True, None)

    is_super_user = True#user_id in config.ADMIN_USERID# or await (SUPERUSER)(bot, event)
    is_admin = is_super_user or chat_type == 'private'# or await (GROUP_ADMIN | GROUP_OWNER)(bot, event) # 超级管理员，私聊，群主，群管理，均视为admin

    common_cmd = ['', '查询', 'query', '设定', 'set', '更新', 'update', 'edit', '添加', 'new', '开启', 'on', '关闭', 'off', '重置', 'reset']
    super_cmd = ['admin', '删除', 'del', 'delete', '锁定', 'lock', '解锁', 'unlock', '扩展', 'ext',  'debug', '会话', 'chats', '记忆', 'memory', 'get', 'upload', 'ph']

    cmd_0 = cmd_list[0]
    if cmd_0 in super_cmd or '-global' in cmd_list: # 超级命令或者命令中包含 `-global` 选项需要超级管理员权限
        return (is_super_user, None if is_super_user else '权限不足，只有超级管理员才允许使用此指令')
    elif cmd_0 in common_cmd:
        return (is_admin, None if is_admin else '权限不足，只有管理员才允许使用此指令')
    else:
        return (True, None)
'''
async def gen_chat_text(event: MessageEvent, bot:Bot) -> Tuple[str, bool]:
    warnings.warn("this function is deprecated", DeprecationWarning)
    """生成合适的会话消息内容(eg. 将cq at 解析为真实的名字)"""
    if not isinstance(event, GroupMessageEvent):
        return event.get_plaintext(), False
    else:
        wake_up = False
        msg = ''
        for seg in event.message:
            if seg.is_text():
                msg += seg.data.get('text', '')
            elif seg.type == 'at':
                qq = seg.data.get('qq', None)
                if qq:
                    if qq == 'all':
                        msg += '@全体成员'
                        wake_up = True
                    else:
                        user_name = await get_user_name(event=event, bot=bot,user_id=int(qq))
                        if user_name:
                            msg += f'@{user_name}' # 保持给bot看到的内容与真实用户看到的一致
        return msg, wake_up
    

async def get_user_name(event: Union[MessageEvent, GroupIncreaseNoticeEvent], bot:Bot, user_id:int) -> Optional[str]:
    warnings.warn("this function is deprecated", DeprecationWarning)
    """获取QQ用户名，如果GROUP_CARD为Ture优先群名片"""
    if isinstance(event, GroupMessageEvent) and event.sub_type == 'anonymous' and event.anonymous: # 匿名消息
        return f'[匿名]{event.anonymous.name}'

    if (isinstance(event, GroupMessageEvent) or isinstance(event, GroupIncreaseNoticeEvent)):
        user_info = await bot.get_group_member_info(group_id=event.group_id, user_id=user_id, no_cache=False)
        user_name = user_info.get('nickname', None)
        if config.GROUP_CARD:
            user_name = user_info.get('card', None) or user_name
    else:
        user_name = event.sender.nickname if event.sender else event.get_user_id()

    if user_name and config.NG_CHECK_USER_NAME_HYPHEN and ('-' in user_name): # 检查用户名中的连字符, 去掉第一个连字符之前的部分
        user_name = user_name.split('-', 1)[1].replace('-', '').strip()
        
    return user_name
'''
async def translate(text:str, from_:str="auto", to_:str="en") -> str:
    """翻译"""
    loop = asyncio.get_event_loop()
    try:
        r = await loop.run_in_executor(None, requests.post, "https://hf.space/embed/mikeee/gradio-gtr/+/api/predict", {"data": [text, from_, to_]})
        return r.json()["data"][0]
    except:
        raise Exception("翻译 API 请求失败")

async def async_fetch(
    url,
    method: str = "get",
    params: Optional[Dict] = None,
    data: Union[str, Dict] = "{}",
    headers: Optional[Dict] = None,
    proxy_server: str = "",
    timeout: int = 60,
) -> str:
    """发起异步请求"""

    if headers is None:
        headers = {}
    if params is None:
        params = {}
    if isinstance(data, dict):
        data = json.dumps(data)

    async with aiohttp.ClientSession(headers=headers) as session:
        if proxy_server:
            conn = aiohttp.TCPConnector(limit=10, verify_ssl=False)
            session = aiohttp.ClientSession(connector=conn)
            session._default_headers.update(  # noqa: SLF001
                {"Proxy-Switch-Ip": "yes"},
            )
            session._default_headers.update(  # noqa: SLF001
                {"Proxy-Server": proxy_server},
            )
        async with getattr(session, method)(
            url,
            params=params,
            data=data,
            timeout=timeout,
        ) as resp:
            return await resp.text()

def fetch(
    url,
    method: str = "get",
    params: Optional[Dict] = None,
    data: Union[str, Dict] = "{}",
    headers: Optional[Dict] = None,
    proxy_server: str = "",
    timeout: int = 60,
) -> str:
    """发起请求"""

    if headers is None:
        headers = {}
    if params is None:
        params = {}
    if isinstance(data, dict):
        data = json.dumps(data)

    if proxy_server:
        proxies = {
            "http": f"http://{proxy_server}",
            "https": f"https://{proxy_server}",
        }
    else:
        proxies = None

    resp = getattr(requests, method)(
        url,
        params=params,
        data=data,
        headers=headers,
        proxies=proxies,
        timeout=timeout,
    )
    return resp.text

def md5(s):
    m = hashlib.md5()
    m.update(s.encode("utf-8"))
    return m.hexdigest()

async def output_message(content, sender:str = '[system]') -> bool:
    """输出消息的统一方式"""
    if type(content) == str:
        #logger.info(content)
        try:
            if not (sender.startswith('[') and sender.endswith(']')):
                notification.notify(
                    title=sender,
                    message=content[0:23]+'...',
                    #timeout = 5,
                    app_name='Naturel GPT'
                )
            await async_fetch(
                url=config.FRONTEND_URL.rstrip('/') + "/notify",
                method="post",
                headers={"Content-Type": "application/json"},
                data={"message": content, "sender": sender}
            )
            return True
        except Exception as e:
            logger.warning(f"输出消息失败: {e}")
            return False
    return False

async def take_screenshot() -> str:
    try:
        with mss.mss() as sct:
            sct.__init__(with_cursor=True)
            #monitor = sct.monitors[0]
            screenshot = sct.shot(output="./data/naturel_gpt/logs/screenshot.png")
            logger.info(f"屏幕截图已保存到 {screenshot}")
            sct.close()
            return(screenshot)
    except Exception as e:
        logger.error(f"截图过程中发生错误: {e}")


def generate_image_url(image_url:str='')->Tuple[bool, str]:
    #image_url = custom.get('image_url', '')
    if image_url == '':
        return False, '获取不到 image_url'
    elif image_url.startswith('http'):
        try:
            url_pattern = r"https?://[^\s]+"
            url_match = re.search(url_pattern, image_url)
            return True, image_url
        except Exception as e:
            return False, f"图像地址解析错误: {e}"
    elif image_url.startswith('data:image/'):
        return True, image_url
    elif re.match(r'^(?:(?:[a-zA-Z]:|\.{1,2})?[\\/](?:[^\\?/*|<>:"]+[\\/])*)(?:(?:[^\\?/*|<>:"]+?)(?:\.[^.\\?/*|<>:"]+)?)?$', image_url):
        try:
            with open(image_url, "rb") as image_file:
                image_data = image_file.read()
                # 猜测图片类型
                mime_type, _ = mimetypes.guess_type(image_url)
                if not mime_type or not mime_type.startswith('image/'):
                    return False, f"文件不是图像: {image_url}"
                #image_format = mime_type.split('/')[-1]
        except Exception as e:#FileNotFoundError:
            return False, f"图像路径错误: {e}"
        # 将图像数据编码为Base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        image_url = f"data:{mime_type};base64,{base64_image}"
        return True, image_url
    else:
        return False, f"无法识别图像: {image_url}"