#!/usr/bin/env python3
"""
测试多种 verify 参数组合，找到正确的格式
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
click_card_api = '/osg-web0004/open/c44/f07'

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
    async with aiohttp.ClientSession() as session:
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
            result = json.loads(await resp.text())
            if 'encryptData' in result:
                result = json.loads(sm4_decrypt(result['encryptData'], keyCode))
            keyCode = result['data']['keyCode']
            publicKey = result['data']['publicKey']
            print(f'1. keyCode: {keyCode[:16]}... ✅')

        # Step 2: Get captcha
        ts2 = int(time.time() * 1000)
        captcha_params = {'account': ACCOUNT, 'password': PASSWORD, 'canvasHeight': 200, 'canvasWidth': 310}
        req_data = encrypt_post_data(captcha_params, keyCode, publicKey, ts2)
        h2 = dict(base_headers)
        h2['timestamp'] = str(ts2)
        h2['sessionId'] = 'web' + str(ts2)
        h2['keyCode'] = keyCode
        async with session.post(baseApi + get_verify_code_api, json=req_data, headers=h2) as resp:
            result = json.loads(await resp.text())
            if 'encryptData' in result:
                result = json.loads(sm4_decrypt(result['encryptData'], keyCode))
            ticket = result['data']['ticket']
            has_block = 'blockSrc' in result['data']
            has_icon = 'iconSrc' in result['data'] or 'wordSrc' in result['data']
            print(f'2. ticket: {ticket[:20]}... blockSrc={has_block} iconSrc={has_icon}')

        # Step 3: Solve captcha (pixel algorithm for slider)
        from PIL import Image
        captcha_data = result['data']

        if has_block:
            # Slider captcha - use pixel algorithm
            canvas_b64 = captcha_data['canvasSrc']
            if canvas_b64.startswith('data:image'):
                canvas_b64 = canvas_b64.split(',', 1)[1]
            canvas_img = Image.open(io.BytesIO(base64.b64decode(canvas_b64)))
            block_y = int(captcha_data.get('blockY', 0))
            cw, ch = canvas_img.size

            # 获取滑块高度
            block_b64 = captcha_data['blockSrc']
            if block_b64.startswith('data:image'):
                block_b64 = block_b64.split(',', 1)[1]
            block_img = Image.open(io.BytesIO(base64.b64decode(block_b64)))
            bh = block_img.size[1]

            cropped = canvas_img.crop((0, block_y, cw, block_y + bh))
            binary = cropped.point(lambda p: 255 if p > 150 else 0)
            w, h = binary.width, binary.height
            matrix = [[0 for _ in range(h)] for _ in range(w)]
            for y in range(h):
                for x in range(w):
                    pixel = binary.getpixel((x, y))
                    if len(pixel) == 4:
                        rv, gv, bv, av = pixel
                        if av < 128: continue
                    else:
                        rv, gv, bv = pixel
                    if max(rv, gv, bv) < 100:
                        matrix[x][y] = 1

            # Find max rectangle (simplified)
            heights = [0] * h
            max_area = 0
            best_left = 0
            for row in range(w):
                for col in range(h):
                    heights[col] = heights[col] + 1 if matrix[row][col] == 1 else 0
                stack = []
                for col in range(h + 1):
                    cur_h = heights[col] if col < h else -1
                    while stack and cur_h < heights[stack[-1]]:
                        ht = heights[stack.pop()]
                        wd = col if not stack else col - stack[-1] - 1
                        if ht * wd > max_area:
                            max_area = ht * wd
                            best_left = row - ht + 1
            distance = best_left
            captcha_type = 'slider'
            print(f'3. Slider distance: {distance}px')
        else:
            # Click captcha - need LLM
            captcha_type = 'click'
            print(f'3. Click captcha detected, skipping for now')
            return

        # Step 4: Try multiple verify parameter combinations
        base_verify = {
            'loginKey': ticket,
            'code': distance,
            'params': {
                'uscInfo': {'devciceIp': '', 'tenant': 'state_grid', 'member': '0902', 'devciceId': ''},
                'quInfo': {'optSys': 'android', 'pushId': '000000', 'addressProvince': '110100', 'password': PASSWORD, 'addressRegion': '110101', 'account': ACCOUNT, 'addressCity': '330100'},
            },
            'Channels': 'web',
        }

        variants = [
            ('A: 原版(无extra)', dict(base_verify)),
            ('B: +complexSliderType=blockPuzzle', {**base_verify, 'complexSliderType': 'blockPuzzle'}),
            ('C: +complexSliderRet=0+complexSliderType=blockPuzzle', {**base_verify, 'complexSliderRet': 0, 'complexSliderType': 'blockPuzzle'}),
            ('D: +complexSliderRet=1+complexSliderType=blockPuzzle', {**base_verify, 'complexSliderRet': 1, 'complexSliderType': 'blockPuzzle'}),
            ('E: code=string', {**base_verify, 'complexSliderRet': 0, 'complexSliderType': 'blockPuzzle', 'code': str(distance)}),
            ('F: f07端点+clickImg', None),  # 特殊处理
        ]

        for variant_name, verify_params in variants:
            await asyncio.sleep(3)  # 间隔3秒

            ts = int(time.time() * 1000)

            if variant_name == 'F: f07端点+clickImg':
                # Try f07 endpoint
                verify_params = dict(base_verify)
                verify_params['complexSliderRet'] = 0
                verify_params['complexSliderType'] = 'clickImg'
                req_data = encrypt_post_data(verify_params, keyCode, publicKey, ts)
                h = dict(base_headers)
                h['timestamp'] = str(ts)
                h['sessionId'] = 'web' + str(ts)
                h['keyCode'] = keyCode
                try:
                    async with session.post(baseApi + click_card_api, json=req_data, headers=h) as resp:
                        text = await resp.text()
                        result2 = json.loads(text) if text.startswith('{') else {'raw': text[:200]}
                        if 'encryptData' in result2:
                            result2 = json.loads(sm4_decrypt(result2['encryptData'], keyCode))
                except Exception as ex:
                    result2 = {'error': str(ex)}
            else:
                req_data = encrypt_post_data(verify_params, keyCode, publicKey, ts)
                h = dict(base_headers)
                h['timestamp'] = str(ts)
                h['sessionId'] = 'web' + str(ts)
                h['keyCode'] = keyCode
                async with session.post(baseApi + verify_password_api, json=req_data, headers=h) as resp:
                    text = await resp.text()
                    result2 = json.loads(text) if text.startswith('{') else {'raw': text[:200]}
                    if 'encryptData' in result2:
                        result2 = json.loads(sm4_decrypt(result2['encryptData'], keyCode))

            code = result2.get('code', '?')
            msg = result2.get('message', '')
            if 'data' in result2 and result2['data'] and isinstance(result2['data'], dict) and 'srvrt' in result2['data']:
                msg = result2['data']['srvrt'].get('resultMessage', msg)
                rc = result2['data']['srvrt'].get('resultCode', '')
                if rc:
                    msg = f'{msg} (resultCode={rc})'
            print(f'4. [{variant_name}] code={code} msg={msg}')

asyncio.run(test())
