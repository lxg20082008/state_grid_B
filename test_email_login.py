#!/usr/bin/env python3
"""
95598 邮箱登录测试
探索邮箱账号是否能走通和手机号同一套 API
"""

import hashlib
import base64
import json
import time
import urllib.parse
import sys
import os
import re
import io as _io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components', 'state_grid'))
from utils.crypt import a, b, c, d, e

import aiohttp
import asyncio
from PIL import Image
from openai import OpenAI

# ─── 配置 ───
EMAIL_ACCOUNT = 'tiejiang29@163.com'
# 密码和手机号登录的密码一样
PASSWORD = 'Abcd=1234'
LLM_API_KEY = 'ark-4075d744-788e-4131-a98d-c5dc1b2b8af1-2d4d1'
LLM_BASE_URL = 'https://ark.cn-beijing.volces.com/api/v3'
LLM_MODEL = 'doubao-seed-2-0-pro-260215'

appKey = '7e5b5e84ddad4994b0ebc68dedca4962'
appSecret = '2bc37a881e1541aaa6e6e174658d150b'
baseApi = 'https://www.95598.cn/api'
HARDCODED_PUBLIC_KEY = '042D12DFBC179202AC4B7B7BADCDA6FF7B604339263F6AB732CE7107B7EA3830A2CA714DC303920D3CFF7647D898F1A8CC6C24E9EC3CC194E22D984AF7E16B42DC'

get_request_key_api = '/oauth2/outer/c02/f02'
get_request_authorize_api = '/oauth2/oauth/authorize'
get_web_token_api = '/oauth2/outer/getWebToken'
get_verify_code_api = '/osg-web0004/open/c44/f05'
verify_password_api = '/osg-web0004/open/c44/f06'
click_card_api = '/osg-web0004/open/c44/f07'

sessionIdControlApiList = [verify_password_api, get_verify_code_api, click_card_api]
keyCodeControlApiList = [
    verify_password_api, get_verify_code_api, get_request_authorize_api,
    get_web_token_api, click_card_api
]


def json_dumps(data):
    return json.dumps(data, separators=(',', ':'), ensure_ascii=False)

def md5_upper(s):
    return hashlib.md5(s.encode()).hexdigest().upper()

def b64_to_img(b64):
    if b64.startswith('data:image'):
        b64 = b64.split(',', 1)[1]
    return Image.open(_io.BytesIO(base64.b64decode(b64)))


class EmailLoginTester:
    def __init__(self):
        self.keyCode = None
        self.publicKey = None
        self.accessToken = None
        self.refreshToken = None
        self.token = None
        self.timestamp = int(time.time() * 1000)
        self.ticket = None
        self.authorizeCode = None
        self.session = None

    async def init_session(self):
        jar = aiohttp.CookieJar(unsafe=True)
        self.session = aiohttp.ClientSession(cookie_jar=jar)

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def fetch(self, api, data, header=None):
        self.timestamp = int(time.time() * 1000)
        ts = self.timestamp

        if self.keyCode is None:
            self.keyCode = e(32, 16, 2)

        key = self.keyCode
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'application/json;charset=UTF-8',
            'Content-Type': 'application/json;charset=UTF-8',
            'version': '1.0',
            'source': '0901',
            'timestamp': str(ts),
            'wsgwType': 'web',
            'appKey': appKey,
            'Origin': 'https://www.95598.cn',
            'Referer': 'https://www.95598.cn/osgweb/login',
        }
        payload = data

        if api == get_request_key_api:
            payload = {'client_id': appKey, 'client_secret': appSecret}
            encrypted = a(json_dumps(payload), key)
            payload = {
                'data': encrypted + c(encrypted + str(ts)),
                'skey': d(key, HARDCODED_PUBLIC_KEY),
                'client_id': appKey,
                'timestamp': str(ts),
            }
        elif api == get_request_authorize_api:
            payload = {
                'client_id': appKey, 'response_type': 'code',
                'redirect_url': '/test', 'timestamp': ts, 'rsi': self.token,
            }
            payload = urllib.parse.urlencode(payload)
            headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
            headers['keyCode'] = key
            async with self.session.post(baseApi + api, data=payload, headers=headers, ssl=False) as resp:
                text = await resp.text()
                print(f"  [get_request_authorize] HTTP {resp.status}")
                result = json.loads(text)
                result = b(result['data'], self.token)
                result = json.loads(result)
                return result
        elif api == get_web_token_api:
            payload = {
                'grant_type': 'authorization_code',
                'sign': c(appKey + str(ts)),
                'client_secret': appSecret,
                'state': '464606a4-184c-4beb-b442-2ab7761d0796',
                'key_code': key,
                'client_id': appKey,
                'timestamp': ts,
                'code': payload['code'],
            }
            encrypted = a(json_dumps(payload), key)
            payload = {
                'data': encrypted + c(encrypted + str(ts)),
                'skey': d(key, self.publicKey),
                'timestamp': str(ts),
            }
        else:
            wrapped = {
                '_access_token': self.accessToken[len(self.accessToken) // 2:] if self.accessToken else '',
                '_t': self.token[len(self.token) // 2:] if self.token else '',
                '_data': data,
                'timestamp': self.timestamp,
            }
            encrypted = a(json_dumps(wrapped), key)
            payload = {
                'data': encrypted + c(encrypted + str(self.timestamp)),
                'skey': d(key, self.publicKey),
                'timestamp': str(self.timestamp),
            }

        if header is not None:
            headers.update(header)
        if api in sessionIdControlApiList:
            headers['sessionId'] = 'web' + str(ts)
        if api in keyCodeControlApiList:
            headers['keyCode'] = key

        async with self.session.post(baseApi + api, json=payload, headers=headers, ssl=False) as resp:
            text = await resp.text()
            if text.startswith('{'):
                result = json.loads(text)
                if 'encryptData' in result:
                    decrypted = b(result['encryptData'], key)
                    result = json.loads(decrypted)
                    return result
                return result
            else:
                return {'error': 'non_json', 'text': text[:500]}

    async def step1_get_request_key(self):
        print("\n" + "=" * 60)
        print("步骤1: 获取加密密钥 (f02)")
        print("=" * 60)
        result = await self.fetch(get_request_key_api, {})
        if 'code' in result and str(result['code']) == '1':
            self.keyCode = result['data']['keyCode']
            self.publicKey = result['data']['publicKey']
            print(f"  keyCode: {self.keyCode[:16]}...")
            print(f"  publicKey: {self.publicKey[:20]}...")
            return True
        else:
            print(f"  失败: {json.dumps(result, ensure_ascii=False)[:500]}")
            return False

    async def step2_get_verify_code(self, account, password):
        print("\n" + "=" * 60)
        print(f"步骤2: 获取验证码 (f05) - 账号: {account}")
        print("=" * 60)
        params = {
            'account': account,
            'password': password,
            'canvasHeight': 200,
            'canvasWidth': 310,
        }
        result = await self.fetch(get_verify_code_api, params)

        if 'code' in result and str(result['code']) == '1' and 'data' in result:
            data = result['data']
            self.ticket = data.get('ticket', '')
            print(f"  ticket: {self.ticket[:30]}...")
            print(f"  返回字段: {list(data.keys())}")

            # 检测验证码类型
            has_iconSrc = 'iconSrc' in data
            has_wordSrc = 'wordSrc' in data
            has_iconSrcs = 'iconSrcs' in data
            has_blockSrc = 'blockSrc' in data
            has_canvasSrc = 'canvasSrc' in data

            print(f"  iconSrc: {has_iconSrc}, wordSrc: {has_wordSrc}, iconSrcs: {has_iconSrcs}")
            print(f"  blockSrc: {has_blockSrc}, canvasSrc: {has_canvasSrc}")

            if has_iconSrc or has_wordSrc or has_iconSrcs:
                captcha_type = 'click'
                print(f"  验证码类型: 点选 (click)")
            elif has_blockSrc:
                captcha_type = 'slider'
                print(f"  验证码类型: 滑块 (slider)")
            else:
                captcha_type = 'slider'
                print(f"  验证码类型: 滑块 (默认)")

            captcha_data = {
                'captcha_type': captcha_type,
                'ticket': self.ticket,
            }
            for key in data:
                if key in ('canvasSrc', 'blockSrc', 'blockY', 'iconSrc', 'wordSrc', 'iconSrcs'):
                    val = data[key]
                    if isinstance(val, str) and len(val) > 100:
                        print(f"  {key}: (base64, len={len(val)})")
                    else:
                        print(f"  {key}: {val}")
                    captcha_data[key] = val

            return captcha_data
        else:
            code = result.get('code', '?')
            msg = ''
            if 'data' in result and result['data'] and 'srvrt' in result['data']:
                msg = result['data']['srvrt'].get('resultMessage', '')
            elif 'message' in result:
                msg = result['message']
            print(f"  获取验证码失败: code={code}, msg={msg}")
            print(f"  完整返回: {json.dumps(result, ensure_ascii=False)[:800]}")
            return None

    async def step3_solve_captcha(self, captcha_data):
        print("\n" + "=" * 60)
        print(f"步骤3: 解算验证码 ({captcha_data['captcha_type']})")
        print("=" * 60)

        captcha_type = captcha_data['captcha_type']

        if captcha_type == 'click':
            return await self._solve_click_captcha(captcha_data)
        else:
            return await self._solve_slider_captcha(captcha_data)

    async def _solve_click_captcha(self, captcha_data):
        ref_base64 = captcha_data.get('iconSrc', '') or captcha_data.get('wordSrc', '')
        main_base64 = captcha_data.get('canvasSrc', '')

        if not ref_base64 or not main_base64:
            print(f"  缺少参考图标或主图")
            return None

        if ref_base64.startswith('data:image'):
            ref_base64_clean = ref_base64.split(',', 1)[1]
        else:
            ref_base64_clean = ref_base64

        if main_base64.startswith('data:image'):
            main_base64_clean = main_base64.split(',', 1)[1]
        else:
            main_base64_clean = main_base64

        main_bytes = base64.b64decode(main_base64_clean)
        main_img = Image.open(_io.BytesIO(main_bytes))
        main_w, main_h = main_img.size
        print(f"  主图尺寸: {main_w}x{main_h}")

        ref_bytes = base64.b64decode(ref_base64_clean)
        ref_img = Image.open(_io.BytesIO(ref_bytes))
        ref_w, ref_h = ref_img.size
        print(f"  参考图标条尺寸: {ref_w}x{ref_h}")

        # 拆分参考图标
        part_w = ref_w // 3
        icon_uris = []
        for i in range(3):
            left = i * part_w
            right = (i + 1) * part_w if i < 2 else ref_w
            icon = ref_img.crop((left, 0, right, ref_h))
            icon = icon.resize((icon.width * 3, icon.height * 3), Image.LANCZOS)
            buf = _io.BytesIO()
            icon.save(buf, format='PNG')
            b64 = base64.b64encode(buf.getvalue()).decode('ascii')
            icon_uris.append(f"data:image/png;base64,{b64}")

        buf = _io.BytesIO()
        main_img.save(buf, format='PNG')
        main_b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        main_uri = f"data:image/png;base64,{main_b64}"

        # 保存图片供调试
        ref_img.save('/home/z/my-project/download/email_captcha_ref.png')
        main_img.save('/home/z/my-project/download/email_captcha_main.png')
        print("  已保存验证码图片到 download/email_captcha_*.png")

        print(f"  正在调用 LLM ({LLM_MODEL})...")
        client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

        prompt = (
            f"大图（{main_w}×{main_h}像素）是一个图标网格。\n"
            "找到3个参考图标(A, B, C)各自在大图网格中的位置。\n"
            "匹配规则：形状和颜色必须一致，空心/实心、线条粗细是关键区分点，允许旋转。\n\n"
            '输出JSON：{"coords":[[xA,yA],[xB,yB],[xC,yC]]}\n'
            "其中x、y为图标中心的比例坐标（0~1）。"
        )

        content = []
        labels = ["A", "B", "C"]
        for i, uri in enumerate(icon_uris[:3]):
            content.append({"type": "image_url", "image_url": {"url": uri}})
            content.append({"type": "text", "text": f"参考图标{labels[i]}"})
        content.append({"type": "image_url", "image_url": {"url": main_uri}})
        content.append({"type": "text", "text": prompt})

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "Output valid JSON only. No markdown, no explanation."},
                {"role": "user", "content": content},
            ],
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        output = response.choices[0].message.content or ""
        print(f"  LLM 响应: {output[:400]}")

        match = re.search(r'\{.*"coords"\s*:\s*\[.*?\]\s*\}', output, re.DOTALL)
        if match:
            data = json.loads(match.group())
            coords = []
            for x, y in data["coords"]:
                x, y = float(x), float(y)
                if max(x, y) <= 1.5:
                    coords.append((round(x * main_w), round(y * main_h)))
                else:
                    coords.append((round(x), round(y)))
            coord_str = "|".join([f"{x},{y}" for x, y in coords])
            print(f"  点选坐标: {coord_str}")
            return coord_str
        else:
            print(f"  无法解析 LLM 响应")
            return None

    async def _solve_slider_captcha(self, captcha_data):
        canvas_base64 = captcha_data.get('canvasSrc', '')
        if not canvas_base64:
            print("  缺少背景图")
            return None

        if canvas_base64.startswith('data:image'):
            canvas_base64_clean = canvas_base64.split(',', 1)[1]
        else:
            canvas_base64_clean = canvas_base64

        canvas_bytes = base64.b64decode(canvas_base64_clean)
        canvas_img = Image.open(_io.BytesIO(canvas_bytes))
        bg_w, bg_h = canvas_img.size
        print(f"  背景图尺寸: {bg_w}x{bg_h}")

        canvas_img.save('/home/z/my-project/download/email_captcha_slider.png')

        buf = _io.BytesIO()
        canvas_img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        canvas_uri = f"data:image/png;base64,{b64}"

        print(f"  正在调用 LLM ({LLM_MODEL})...")
        client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": canvas_uri}},
                        {
                            "type": "text",
                            "text": (
                                f"这是一个滑块拼图验证码的背景图（{bg_w}x{bg_h}像素）。\n"
                                "图中有一个矩形缺口（拼图块被挖掉的位置），缺口边缘有轻微阴影或颜色差异。\n"
                                "请找到这个缺口，返回缺口左侧边缘的X坐标比例（0~1之间）。\n"
                                "输出格式（仅一个数字）：0.XX"
                            ),
                        },
                    ],
                }
            ],
            max_tokens=50,
        )

        output = response.choices[0].message.content or ""
        print(f"  LLM 响应: {output[:100]}")

        nums = re.findall(r'(\d+\.?\d*)', output)
        if nums:
            ratio = float(nums[0])
            if ratio > 1.5:
                ratio = ratio / bg_w
            ratio = max(0.0, min(1.0, ratio))
            distance = int(ratio * 310)
            print(f"  滑块距离: {distance}px (比例: {ratio:.3f})")
            return distance
        else:
            print(f"  无法解析 LLM 响应")
            return 0

    async def step4_verify(self, account, password, code, ticket, captcha_type='slider'):
        """验证登录 - 尝试多种模式"""
        print("\n" + "=" * 60)
        print(f"步骤4: 验证登录")
        print("=" * 60)

        params = {
            'loginKey': ticket,
            'code': code,
            'params': {
                'uscInfo': {
                    'devciceIp': '', 'tenant': 'state_grid',
                    'member': '0902', 'devciceId': '',
                },
                'quInfo': {
                    'optSys': 'android', 'pushId': '000000',
                    'addressProvince': '110100', 'password': password,
                    'addressRegion': '110101', 'account': account,
                    'addressCity': '330100',
                },
            },
            'Channels': 'web',
        }

        # 尝试多种模式
        modes = [
            ('f06 + complexSliderType', verify_password_api, {
                'complexSliderRet': 0,
                'complexSliderType': 'clickImg' if captcha_type == 'click' else 'blockPuzzle',
            }),
            ('f06 无额外字段', verify_password_api, {}),
            ('f07 clickCard', click_card_api, {}),
        ]

        for mode_name, api, extra in modes:
            print(f"\n  尝试模式: {mode_name}")
            test_params = dict(params)
            test_params.update(extra)

            print(f"    account={account}, ticket={ticket[:20]}...")
            print(f"    complexSliderType={test_params.get('complexSliderType', '无')}")
            print(f"    code={code}")

            result = await self.fetch(api, test_params)
            code_val = result.get('code', '?')
            print(f"    返回 code: {code_val}")

            if 'code' in result and str(result['code']) == '1':
                if result.get('data') and result['data'].get('srvrt') and result['data']['srvrt'].get('resultCode') == '0000':
                    self.token = result['data']['bizrt']['token']
                    user_info = result['data']['bizrt'].get('userInfo', [])
                    print(f"    登录成功! token: {self.token[:20]}...")
                    if user_info:
                        print(f"    userInfo: {json.dumps(user_info[0], ensure_ascii=False)[:300]}")
                    return {'errcode': 0, 'mode': mode_name}

            msg = ''
            if 'data' in result and result['data'] and 'srvrt' in result['data']:
                msg = result['data']['srvrt'].get('resultMessage', '')
            elif 'message' in result:
                msg = result['message']
            print(f"    失败: {msg}")
            print(f"    完整返回: {json.dumps(result, ensure_ascii=False)[:500]}")

        return {'errcode': 1}

    async def step5_get_authorize(self):
        print("\n" + "=" * 60)
        print("步骤5: 获取授权码")
        print("=" * 60)
        result = await self.fetch(get_request_authorize_api, {})
        if 'code' in result and result['code'] == '1':
            redirect_url = result['data']['redirect_url']
            idx = redirect_url.rfind('code=')
            self.authorizeCode = redirect_url[idx + 5:idx + 5 + 32]
            print(f"  authorizeCode: {self.authorizeCode}")
            return True
        return False

    async def step6_get_web_token(self):
        print("\n" + "=" * 60)
        print("步骤6: 获取 Web Token")
        print("=" * 60)
        params = {'code': self.authorizeCode}
        result = await self.fetch(get_web_token_api, params)
        if 'code' in result and result['code'] == '1':
            self.accessToken = result['data']['access_token']
            self.refreshToken = result['data']['refresh_token']
            print(f"  accessToken: {self.accessToken[:30]}...")
            print(f"  refreshToken: {self.refreshToken[:30]}...")
            return True
        return False


async def main():
    tester = EmailLoginTester()
    await tester.init_session()

    pwd = md5_upper(PASSWORD)
    print(f"=" * 60)
    print(f"95598 邮箱登录测试")
    print(f"=" * 60)
    print(f"账号: {EMAIL_ACCOUNT}")
    print(f"密码 MD5: {pwd}")

    try:
        # 步骤1: 获取密钥
        if not await tester.step1_get_request_key():
            print("\n步骤1失败，终止")
            return

        # 步骤2: 获取验证码（用邮箱作为 account）
        captcha_data = await tester.step2_get_verify_code(EMAIL_ACCOUNT, pwd)
        if not captcha_data:
            print("\n步骤2失败，终止")
            return

        # 步骤3: 解算验证码
        verify_code = await tester.step3_solve_captcha(captcha_data)
        if verify_code is None:
            print("\n步骤3失败，终止")
            return

        # 步骤4: 提交验证
        captcha_type = captcha_data['captcha_type']
        ticket = captcha_data['ticket']

        result = await tester.step4_verify(EMAIL_ACCOUNT, pwd, verify_code, ticket, captcha_type)

        if result['errcode'] == 0:
            # 步骤5: 获取授权码
            if await tester.step5_get_authorize():
                # 步骤6: 获取 token
                if await tester.step6_get_web_token():
                    print("\n" + "=" * 60)
                    print("邮箱登录完全成功!")
                    print("=" * 60)
                else:
                    print("\n步骤6失败")
            else:
                print("\n步骤5失败")
        else:
            print(f"\n验证失败: {result}")

    except Exception as ex:
        import traceback
        print(f"\n异常: {ex}")
        traceback.print_exc()
    finally:
        await tester.close_session()


if __name__ == '__main__':
    asyncio.run(main())
