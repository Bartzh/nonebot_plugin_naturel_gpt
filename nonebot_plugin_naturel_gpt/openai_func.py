import re
import os
from typing import Tuple, Dict
from logger import logger
#from nonebot.utils import run_sync
from tiktoken import Encoding, encoding_for_model # type: ignore

import base64, mimetypes

import openai # type: ignore
# from transformers import GPT2TokenizerFast
from singleton import Singleton

enc_cache: Dict[str, Encoding] = {}
os.environ["TOKENIZERS_PARALLELISM"] = "false"


# tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

try:    # 检查openai版本是否高于0.27.0
    import pkg_resources
    openai_version = pkg_resources.get_distribution("openai").version
    if openai_version < '0.27.0':
        logger.warning(f"当前 openai 库版本为 {openai_version}，请更新至 0.27.0 版本以上，否则可能导致 gpt-3.5-turbo 模型无法使用")
except:
    logger.warning("无法获取 openai 库版本，请更新至 0.27.0 版本以上，否则 gpt-3.5-turbo 模型将无法使用")

class TextGenerator(Singleton["TextGenerator"]):
    def init(self, api_keys: list, api_keys_image: list, config: dict, proxy = None, base_url = '', base_url_image = ''):
        self.api_keys = api_keys
        self.key_index = 0
        self.api_keys_image = api_keys_image
        self.key_index_image = 0
        self.config = config
        if proxy:
            if not proxy.startswith('http'):
                proxy = 'http://' + proxy
        openai.proxy = proxy
        if base_url:
            self.base_url = base_url
            #openai.api_base = base_url
        if base_url_image == '':
            self.base_url_image = base_url
        else:
            self.base_url_image = base_url_image
    
#    @run_sync
    async def get_response(self, prompt, type: str = 'chat', custom: dict = {}) -> Tuple[str, bool]:
        """获取文本生成"""
        res, success, success_image = ('', False, None)
        api_keys_len = len(self.api_keys) if type != 'image' else len(self.api_keys_image)
        for _ in range(api_keys_len):
            if type == 'chat':
                res, success = self.get_chat_response(self.api_keys[self.key_index], prompt, custom)
            elif type == 'image':
                res, success_image = self.get_image_response(self.api_keys_image[self.key_index_image], prompt, custom)
            elif type == 'summarize':
                res, success = self.get_summarize_response(self.api_keys[self.key_index], prompt, custom)
            elif type == 'impression':
                res, success = self.get_impression_response(self.api_keys[self.key_index], prompt, custom)
            else:
                res, success = (f'未知类型:{type}', False)
            if success or success_image:
                return res, True

            # 请求错误处理
            if "Rate limit" in res:
                reason = res
                res = '超过每分钟请求次数限制，喝杯茶休息一下吧 (´；ω；`)'
                break
            elif "module 'openai' has no attribute 'ChatCompletion'" in res:
                reason = res
                res = '当前 openai 库版本过低，无法使用 gpt-3.5-turbo 模型 (´；ω；`)'
                break
            elif "Error communicating with OpenAI" in res:
                reason = res
                res = '与 OpenAi 通信时发生错误 (´；ω；`)'
            else:
                reason = res
                res = '哎呀，发生了未知错误 (´；ω；`)'
            if success_image is not None:
                self.key_index_image = (self.key_index_image + 1) % len(self.api_keys_image)
                logger.warning(f"当前 Api Key Image({self.key_index_image}): [{self.api_keys_image[self.key_index_image][:4]}...{self.api_keys_image[self.key_index_image][-4:]}] 请求错误，尝试使用下一个...")
            else:
                self.key_index = (self.key_index + 1) % len(self.api_keys)
                logger.warning(f"当前 Api Key({self.key_index}): [{self.api_keys[self.key_index][:4]}...{self.api_keys[self.key_index][-4:]}] 请求错误，尝试使用下一个...")
            logger.error(f"错误原因: {res} => {reason}")
        logger.error("请求 OpenAi 发生错误，请检查 Api Key 是否正确或者查看控制台相关日志")
        return res, False

    def get_chat_response(self, key:str, prompt, custom:dict = {})->Tuple[str, bool]:
        """对话文本生成"""
        openai.api_key = key
        openai.api_base = self.base_url
        try:
            #if self.config['model'].startswith('gpt-3.5-turbo') or self.config['model'].startswith('gpt-4'):
            if True:
                response = openai.ChatCompletion.create(
                    model=self.config['model'],
                    messages=prompt if isinstance(prompt, list) else [  # 如果是列表则直接使用，否则按照以下格式转换
                        {'role': 'system', 'content': f"You must strictly follow the user's instructions to give {custom.get('bot_name', 'bot')}'s response."},
                        {'role': 'user', 'content': prompt},
                    ],
                    temperature=self.config['temperature'],
                    max_tokens=self.config['max_tokens'],
                    top_p=self.config['top_p'],
                    #frequency_penalty=self.config['frequency_penalty'],
                    presence_penalty=self.config['presence_penalty'],
                    #timeout=self.config.get('timeout', 30),
                    #extra_body={"enable_search": True} if self.config['model'].startswith('qwen') else {},
                    stop=[f"\n{custom.get('bot_name', 'AI')}:", f"\n{custom.get('sender_name', 'Human')}:"]
                )
                res:str = ''
                for choice in response.choices: # type: ignore
                    res += choice.message.content
                res = res.strip()
                # 去掉头尾引号（如果有）
                if res.startswith('"') and res.endswith('"'):
                    res = res[1:-1]
                if res.startswith("'") and res.endswith("'"):
                    res = res[1:-1]
                # 去掉可能存在的开头起始标志
                if res.startswith(f"{custom.get('bot_name', 'AI')}:"):
                    res = res[len(f"{custom.get('bot_name', 'AI')}:"):]
                # 去掉可能存在的开头起始标志 (中文)
                if res.startswith(f"{custom.get('bot_name', 'AI')}："):
                    res = res[len(f"{custom.get('bot_name', 'AI')}："):]
                # 替换多段回应中的回复起始标志
                res = res.replace(f"\n\n{custom.get('bot_name', 'AI')}:", "*;")
                # 正则匹配去掉多余的诸如 "[hh:mm:ss aa] bot_name:" 的形式
                res = re.sub(r"\[\d{2}:\d{2}:\d{2} [AP]M\] ?" + custom.get('bot_name', 'AI') + r":", "", res)
            else:
                response = openai.Completion.create(
                    model=self.config['model'],
                    prompt=prompt,
                    temperature=self.config['temperature'],
                    max_tokens=self.config['max_tokens'],
                    top_p=self.config['top_p'],
                    #frequency_penalty=self.config['frequency_penalty'],
                    presence_penalty=self.config['presence_penalty'],
                    stop=[f"\n{custom.get('bot_name', 'AI')}:", f"\n{custom.get('sender_name', 'Human')}:"]
                )
                res = response['choices'][0]['text'].strip() # type: ignore
            return res, True
        except Exception as e:
            return f"请求 OpenAi Api 时发生错误: {e}", False

    def get_summarize_response(self, key:str, prompt:str, custom:dict = {})->Tuple[str, bool]:
        """总结文本生成"""
        openai.api_key = key
        openai.api_base = self.base_url
        try:
            response = openai.ChatCompletion.create(
                model=self.config['model'],
                messages=[
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.6,
                max_tokens=self.config.get('max_summary_tokens', 512),
                top_p=1,
                #frequency_penalty=0.2,
                presence_penalty=0.2,
                #timeout=self.config.get('timeout', 30),
            )
            res = ''
            for choice in response.choices: # type: ignore
                res += choice.message.content
            res = res.strip()
            # 去掉头尾引号（如果有）
            if res.startswith('"') and res.endswith('"'):
                res = res[1:-1]
            if res.startswith("'") and res.endswith("'"):
                res = res[1:-1]
            # if self.config['model'].startswith('gpt-3.5-turbo'):
            # else:
            #     response = openai.Completion.create(
            #         model="text-davinci-003",
            #         prompt=prompt,
            #         temperature=0.6,
            #         max_tokens=self.config.get('max_summary_tokens', 512),
            #         top_p=1,
            #         frequency_penalty=0,
            #         presence_penalty=0
            #     )
            #     res = response['choices'][0]['text'].strip() # type: ignore
            return res, True
        except Exception as e:
            return f"请求 OpenAi Api 时发生错误: {e}", False

    def get_impression_response(self, key:str, prompt:str, custom:dict = {})->Tuple[str, bool]:
        """印象文本生成"""
        openai.api_key = key
        openai.api_base = self.base_url
        try:
            response = openai.ChatCompletion.create(
                model=self.config['model'],
                messages=[
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.6,
                max_tokens=self.config.get('max_summary_tokens', 512),
                top_p=1,
                #frequency_penalty=0.2,
                presence_penalty=0.2,
                #timeout=self.config.get('timeout', 30),
            )
            res = ''
            for choice in response.choices: # type: ignore
                res += choice.message.content
            res = res.strip()
            # 去掉头尾引号（如果有）
            if res.startswith('"') and res.endswith('"'):
                res = res[1:-1]
            if res.startswith("'") and res.endswith("'"):
                res = res[1:-1]
            # if self.config['model'].startswith('gpt-3.5-turbo'):
            # else:
            #     response = openai.Completion.create(
            #         model="text-davinci-003",
            #         prompt=prompt,
            #         temperature=0.6,
            #         max_tokens=self.config.get('max_summary_tokens', 512),
            #         top_p=1,
            #         frequency_penalty=0,
            #         presence_penalty=0
            #     )
            #     res = response['choices'][0]['text'].strip() # type: ignore
            return res, True
        except Exception as e:
            return f"请求 OpenAi Api 时发生错误: {e}", False

    def get_image_response(self, key:str, prompt:str = '', custom:dict = {})->Tuple[str, bool]:
        """图像描述生成"""
        openai.api_key = key
        openai.api_base = self.base_url_image
        try:
            #if self.config['model'].startswith('gpt-3.5-turbo') or self.config['model'].startswith('gpt-4'):
            image_url = custom.get('image_url', '')
            if image_url == '':
                return '获取不到 image_url', False
            elif image_url.startswith('http'):
                try:
                    url_pattern = r"https?://[^\s]+"
                    url_match = re.search(url_pattern, image_url)
                except Exception as e:
                    return f"图像地址解析错误: {e}", False
            elif image_url.startswith('data:image/'):
                pass
            elif re.match(r'^(?:(?:[a-zA-Z]:|\.{1,2})?[\\/](?:[^\\?/*|<>:"]+[\\/])*)(?:(?:[^\\?/*|<>:"]+?)(?:\.[^.\\?/*|<>:"]+)?)?$', image_url):
                try:
                    with open(image_url, "rb") as image_file:
                        image_data = image_file.read()
                        # 猜测图片类型
                        mime_type, _ = mimetypes.guess_type(image_url)
                        if not mime_type or not mime_type.startswith('image/'):
                            return f"文件不是图像: {image_url}", False
                        #image_format = mime_type.split('/')[-1]
                except Exception as e:#FileNotFoundError:
                    return f"图像路径错误: {e}", False
                # 将图像数据编码为Base64
                base64_image = base64.b64encode(image_data).decode('utf-8')
                image_url = f"data:{mime_type};base64,{base64_image}"

            if prompt == '':
                prompt = '这张图里有些什么？'
            response = openai.ChatCompletion.create(
                model=self.config['model_image'],
                messages=[
                    {
                    "role": "user",
                    "content": [
                        {
                        "type": "text",
                        "text": prompt
                        },
                        {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                        }
                    ]
                    }
                ],
                temperature=0.6,
                max_tokens=self.config.get('max_summary_tokens', 512),
                top_p=1,
                #frequency_penalty=self.config['frequency_penalty'],
                presence_penalty=0.2,
                #timeout=self.config.get('timeout', 30),
                #stop=[f"\n{custom.get('bot_name', 'AI')}:", f"\n{custom.get('sender_name', 'Human')}:"]
            )
            res:str = ''
            for choice in response.choices: # type: ignore
                res += choice.message.content
            res = res.strip()
            # 去掉头尾引号（如果有）
            if res.startswith('"') and res.endswith('"'):
                res = res[1:-1]
            if res.startswith("'") and res.endswith("'"):
                res = res[1:-1]
            # 去掉可能存在的开头起始标志
            #if res.startswith(f"{custom.get('bot_name', 'AI')}:"):
            #    res = res[len(f"{custom.get('bot_name', 'AI')}:"):]
            # 去掉可能存在的开头起始标志 (中文)
            #if res.startswith(f"{custom.get('bot_name', 'AI')}："):
            #    res = res[len(f"{custom.get('bot_name', 'AI')}："):]
            # 替换多段回应中的回复起始标志
            #res = res.replace(f"\n\n{custom.get('bot_name', 'AI')}:", "*;")
            # 正则匹配去掉多余的诸如 "[hh:mm:ss aa] bot_name:" 的形式
            #res = re.sub(r"\[\d{2}:\d{2}:\d{2} [AP]M\] ?" + custom.get('bot_name', 'AI') + r":", "", res)
            return res, True
        except Exception as e:
            return f"请求 OpenAi Api 时发生错误: {e}", False

    @staticmethod
    def generate_msg_template(sender:str, msg: str, time_str: str='') -> str:
        """生成对话模板"""
        return f"{time_str}{sender}: {msg}"

    # @staticmethod
    # def cal_token_count(msg: str) -> int:
    #     """计算字符串的token数量"""
    #     try:
    #         return len(tokenizer.encode(msg))
    #     except:
    #         return 2048

    @staticmethod
    def cal_token_count(text: str, model: str = "gpt-3.5-turbo"):
        """计算字节对编码后的token数量

        Args:
            text (str): 文本
            model (str, optional): 模型. Defaults to "gpt-3.5-turbo".

        Returns:
            int: token 数量
        """

        if model in enc_cache:
            enc = enc_cache[model]
        else:
            enc = encoding_for_model(model)
            enc_cache[model] = enc

        return len(enc.encode(text))

