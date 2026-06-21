#!/usr/bin/env python3
"""
测试 sessionId 一致性 + cookie 跟踪
"""
import asyncio, aiohttp, hashlib, json, time, urllib.parse, sys, os, re, base64, io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components', 'state_grid'))
from utils.crypt import a as sm4_encrypt, b as sm4_decrypt, c as sm3_hash, d as sm2_encrypt, e as random_key

ACCOUNT = '18982135872'
PASSWORD = hashlib.md5('Abcd=1234'.encode()).hexdigest().upper()
appKey = '7e5b5e84ddad4994b0ebc68dedca4962'
appSecret = '2bc37a881e1541aaa6e6e174658d150b'
baseApi = 'https://www.95598.cn/api'
HARDCODED_PUBLIC_KEY = '042D12DFBC179202AC4B7B7BADCDA6FF7B604339263F6AB732CE7107B7EA3830A2CA714DC303920D3CFF7647D898F1A8CC6C24E9EC3CC194E22D984AF7E16B42DC'

get_request_key_api = '/oauth2/outer/c02/f02'
get_verify_code_api = '/osg-web0004/open/c44/f05'
verify_password_api = '/osg-web0004/open/c44/f06'

def json_dumps(data):
    return json.dumps(data, separators=(',', ':'), ensure_ascii=False)

def encrypt_post_data(data, keyCode, publicKey, timestamp, accessToken='', token=''):
    wrapped = {
        '_access_token': accessToken[len(accessToken) // 2:] if accessToken else '',
        '_t': token[len(token) // 2:] if token else '',
        '_data': data,
        'timestamp': timestamp,
    }
    encrypted = sm4_encrypt(json_dumps(wrapped), keyCode)
    return {
        'data': encrypted + sm3_hash(encrypted + str(timestamp)),
        'skey': sm2_encrypt(keyCode, publicKey),
        'timestamp': str(timestamp),
    }

async def test():
    # 使用 cookie_jar 来跟踪 cookies
    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'application/json;charset=UTF-8',
            'Content-Type': 'application/json;charset=UTF-8',
            'version': '1.0', 'source': '0901',
            'wsgwType': 'web', 'appKey': appKey,
            'Origin': 'https://www.95598.cn',
            'Referer': 'https://www.95598.cn/osgweb/login',
        }

        # Step 1: Get key
        ts1 = int(time.time() * 1000)
        keyCode = random_key(32, 16, 2)
        payload = {'client_id': appKey, 'client_secret': appSecret}
        encrypted = sm4_encrypt(json_dumps(payload), keyCode)
        req_data = {
            'data': encrypted + sm3_hash(encrypted + str(ts1)),
            'skey': sm2_encrypt(keyCode, HARDCODED_PUBLIC_KEY),
            'client_id': appKey,
            'timestamp': str(ts1),
        }
        h1 = dict(base_headers)
        h1['timestamp'] = str(ts1)
        async with session.post(baseApi + get_request_key_api, json=req_data, headers=h1) as resp:
            # 打印 cookies
            print(f'1. Cookies after f02: {dict(resp.cookies)}')
            result = json.loads(await resp.text())
            if 'encryptData' in result:
                result = json.loads(sm4_decrypt(result['encryptData'], keyCode))
            keyCode = result['data']['keyCode']
            publicKey = result['data']['publicKey']
            print(f'1. keyCode: {keyCode[:16]}... ✅')

        # Step 2: Get captcha - 保存 sessionId
        ts2 = int(time.time() * 1000)
        session_id = 'web' + str(ts2)  # 保存这个 sessionId
        captcha_params = {'account': ACCOUNT, 'password': PASSWORD, 'canvasHeight': 200, 'canvasWidth': 310}
        req_data = encrypt_post_data(captcha_params, keyCode, publicKey, ts2)
        h2 = dict(base_headers)
        h2['timestamp'] = str(ts2)
        h2['sessionId'] = session_id
        h2['keyCode'] = keyCode
        async with session.post(baseApi + get_verify_code_api, json=req_data, headers=h2) as resp:
            print(f'2. Cookies after f05: {dict(resp.cookies)}')
            result = json.loads(await resp.text())
            if 'encryptData' in result:
                result = json.loads(sm4_decrypt(result['encryptData'], keyCode))
            ticket = result['data']['ticket']
            print(f'2. ticket: {ticket[:20]}... sessionId: {session_id}')

        # Step 3: Solve with LLM
        from openai import OpenAI
        from PIL import Image

        captcha_data = result['data']
        canvas_b64 = captcha_data['canvasSrc']
        if canvas_b64.startswith('data:image'):
            canvas_b64 = canvas_b64.split(',', 1)[1]
        canvas_img = Image.open(io.BytesIO(base64.b64decode(canvas_b64)))
        bg_w, bg_h = canvas_img.size
        buf = io.BytesIO()
        canvas_img.save(buf, format='PNG')
        canvas_uri = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

        client = OpenAI(base_url='https://ark.cn-beijing.volces.com/api/v3', api_key='ark-4075d744-788e-4131-a98d-c5dc1b2b8af1-2d4d1')
        response = client.chat.completions.create(
            model='doubao-seed-2-0-pro-260215',
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": canvas_uri}},
                    {"type": "text", "text": f"这是一个滑块拼图验证码的背景图（{bg_w}x{bg_h}像素）。\n图中有一个矩形缺口，缺口边缘有轻微阴影或颜色差异。\n请找到这个缺口，返回缺口左侧边缘的X坐标比例（0~1之间）。\n输出格式（仅一个数字）：0.XX"},
                ],
            }],
            max_tokens=50,
        )
        output = response.choices[0].message.content or ""
        nums = re.findall(r'(\d+\.?\d*)', output)
        ratio = float(nums[0]) if nums else 0.5
        if ratio > 1.5:
            ratio = ratio / bg_w
        ratio = max(0.0, min(1.0, ratio))
        distance = int(ratio * 310)
        print(f'3. LLM slider: ratio={ratio:.3f} distance={distance}px')

        # Step 4: 验证 - 测试不同的 sessionId 策略
        verify_params = {
            'loginKey': ticket,
            'code': distance,
            'params': {
                'uscInfo': {'devciceIp': '', 'tenant': 'state_grid', 'member': '0902', 'devciceId': ''},
                'quInfo': {'optSys': 'android', 'pushId': '000000', 'addressProvince': '110100', 'password': PASSWORD, 'addressRegion': '110101', 'account': ACCOUNT, 'addressCity': '330100'},
            },
            'Channels': 'web',
        }

        for variant_name, use_same_session, extra in [
            ('同sessionId(f05的)', True, {}),
            ('新sessionId', False, {}),
            ('同sessionId+complexSliderType', True, {'complexSliderRet': 0, 'complexSliderType': 'blockPuzzle'}),
        ]:
            await asyncio.sleep(3)
            ts = int(time.time() * 1000)
            vp = dict(verify_params)
            vp.update(extra)
            req_data = encrypt_post_data(vp, keyCode, publicKey, ts)
            h = dict(base_headers)
            h['timestamp'] = str(ts)
            if use_same_session:
                h['sessionId'] = session_id  # 使用 f05 的 sessionId
            else:
                h['sessionId'] = 'web' + str(ts)  # 新 sessionId
            h['keyCode'] = keyCode

            print(f'4. [{variant_name}] sessionId={h["sessionId"][:30]}...')
            async with session.post(baseApi + verify_password_api, json=req_data, headers=h) as resp:
                text = await resp.text()
                result2 = json.loads(text) if text.startswith('{') else {'raw': text[:200]}
                if 'encryptData' in result2:
                    result2 = json.loads(sm4_decrypt(result2['encryptData'], keyCode))
                code = result2.get('code', '?')
                msg = result2.get('message', '')
                if 'data' in result2 and result2['data'] and isinstance(result2['data'], dict) and 'srvrt' in result2['data']:
                    msg = result2['data']['srvrt'].get('resultMessage', msg)
                print(f'   code={code} msg={msg}')

asyncio.run(test())
