#!/usr/bin/env python3
"""
95598 二维码登录 API 探索
尝试找到纯 API 方式的二维码登录流程
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

appKey = '7e5b5e84ddad4994b0ebc68dedca4962'
appSecret = '2bc37a881e1541aaa6e6e174658d150b'
baseApi = 'https://www.95598.cn/api'
HARDCODED_PUBLIC_KEY = '042D12DFBC179202AC4B7B7BADCDA6FF7B604339263F6AB732CE7107B7EA3830A2CA714DC303920D3CFF7647D898F1A8CC6C24E9EC3CC194E22D984AF7E16B42DC'

get_request_key_api = '/oauth2/outer/c02/f02'
sessionIdControlApiList = []
keyCodeControlApiList = []


def json_dumps(data):
    return json.dumps(data, separators=(',', ':'), ensure_ascii=False)


async def main():
    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        
        # ======== 步骤0: 先访问登录页获取Cookie和页面信息 ========
        print("=" * 60)
        print("步骤0: 访问95598登录页")
        print("=" * 60)
        try:
            async with session.get(
                'https://www.95598.cn/osgweb/login',
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                },
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                print(f"  主页响应: {resp.status}")
                cookies = {c.key: c.value for c in jar}
                print(f"  Cookies: {json.dumps(cookies, ensure_ascii=False)[:500]}")
        except Exception as ex:
            print(f"  访问主页失败: {ex}")

        # ======== 步骤1: 获取 keyCode ========
        print("\n" + "=" * 60)
        print("步骤1: 获取 keyCode")
        print("=" * 60)
        keyCode = e(32, 16, 2)
        ts1 = int(time.time() * 1000)
        
        payload = {'client_id': appKey, 'client_secret': appSecret}
        encrypted = a(json_dumps(payload), keyCode)
        req_payload = {
            'data': encrypted + c(encrypted + str(ts1)),
            'skey': d(keyCode, HARDCODED_PUBLIC_KEY),
            'client_id': appKey,
            'timestamp': str(ts1),
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'application/json;charset=UTF-8',
            'Content-Type': 'application/json;charset=UTF-8',
            'version': '1.0',
            'source': '0901',
            'timestamp': str(ts1),
            'wsgwType': 'web',
            'appKey': appKey,
            'Origin': 'https://www.95598.cn',
            'Referer': 'https://www.95598.cn/osgweb/login',
        }
        
        async with session.post(baseApi + '/oauth2/outer/c02/f02', json=req_payload, headers=headers, ssl=False) as resp:
            text = await resp.text()
            result = json.loads(text)
            if 'encryptData' in result:
                decrypted = b(result['encryptData'], keyCode)
                result = json.loads(decrypted)
        
        if str(result.get('code', '')) != '1':
            print(f"  获取keyCode失败: {json.dumps(result, ensure_ascii=False)[:300]}")
            return
        
        keyCode = result['data']['keyCode']
        publicKey = result['data']['publicKey']
        print(f"  keyCode: {keyCode[:16]}...")
        print(f"  publicKey: {publicKey[:20]}...")

        # ======== 步骤2: 探索二维码相关的 API 端点 ========
        print("\n" + "=" * 60)
        print("步骤2: 探索二维码登录API")
        print("=" * 60)
        
        # 可能的二维码API端点（根据95598 API命名规则推断）
        qr_api_candidates = [
            # c44 组（登录相关）
            '/osg-web0004/open/c44/f01',  # 可能是获取二维码
            '/osg-web0004/open/c44/f02',  # 可能是获取二维码
            '/osg-web0004/open/c44/f03',  # 可能是获取二维码
            '/osg-web0004/open/c44/f04',  # 可能是获取二维码
            # f08-f10（我们已知f05=验证码, f06=验证密码, f07=点选验证）
            '/osg-web0004/open/c44/f08',
            '/osg-web0004/open/c44/f09',
            '/osg-web0004/open/c44/f10',
            # 其他可能的端点
            '/osg-web0004/open/c44/f11',
            '/osg-web0004/open/c44/f12',
            '/osg-web0004/open/c44/f13',
            '/osg-web0004/open/c44/f14',
            '/osg-web0004/open/c44/f15',
            '/osg-web0004/open/c44/f16',
            '/osg-web0004/open/c44/f17',
            '/osg-web0004/open/c44/f18',
        ]
        
        for api in qr_api_candidates:
            ts = int(time.time() * 1000)
            
            # 尝试发送空参数
            wrapped = {'_access_token': '', '_t': '', '_data': {}, 'timestamp': ts}
            encrypted = a(json_dumps(wrapped), keyCode)
            req_payload = {
                'data': encrypted + c(encrypted + str(ts)),
                'skey': d(keyCode, publicKey),
                'timestamp': str(ts),
            }
            
            test_headers = dict(headers)
            test_headers['timestamp'] = str(ts)
            test_headers['sessionId'] = 'web' + str(ts)
            test_headers['keyCode'] = keyCode
            
            try:
                async with session.post(baseApi + api, json=req_payload, headers=test_headers, ssl=False) as resp:
                    text = await resp.text()
                    if text.startswith('{'):
                        result = json.loads(text)
                        if 'encryptData' in result:
                            decrypted = b(result['encryptData'], keyCode)
                            result = json.loads(decrypted)
                        
                        code = result.get('code', '?')
                        msg = ''
                        data_keys = []
                        if 'data' in result and result['data']:
                            if isinstance(result['data'], dict):
                                data_keys = list(result['data'].keys())
                                if 'srvrt' in result['data']:
                                    msg = result['data'].get('srvrt', {}).get('resultMessage', '')
                        elif 'message' in result:
                            msg = result['message']
                        
                        # 只打印有意义的响应
                        status = "✅" if str(code) == '1' else "⚠️" if str(code) != '0' else "❌"
                        print(f"  {status} {api}: code={code}, keys={data_keys}, msg={msg[:60]}")
                        
                        # 如果有成功响应，打印完整内容
                        if str(code) == '1':
                            print(f"      完整返回: {json.dumps(result, ensure_ascii=False)[:500]}")
                    else:
                        print(f"  ❌ {api}: 非JSON响应 ({len(text)} bytes)")
            except Exception as ex:
                print(f"  ❌ {api}: 异常 {ex}")
            
            # 避免限流
            await asyncio.sleep(0.5)

        # ======== 步骤3: 尝试带参数的二维码请求 ========
        print("\n" + "=" * 60)
        print("步骤3: 尝试带参数的二维码API请求")
        print("=" * 60)
        
        # 一些可能的二维码请求参数
        qr_params_variants = [
            # 方式1: 简单参数
            {'channelCode': '0902', 'source': 'SGAPP'},
            # 方式2: 带场景类型
            {'sceneType': 'login', 'channelCode': '0902'},
            # 方式3: 带 uscInfo
            {
                'uscInfo': {'member': '0902', 'devciceIp': '', 'devciceId': '', 'tenant': 'state_grid'},
                'channelCode': '0902',
                'source': 'SGAPP',
            },
            # 方式4: 获取二维码图片
            {'type': 'qrcode', 'channelCode': '0902'},
            # 方式5: 扫码登录
            {'loginType': 'qrcode', 'channelCode': '0902'},
        ]
        
        # 只测试之前发现可能有响应的端点
        interesting_apis = [
            '/osg-web0004/open/c44/f01',
            '/osg-web0004/open/c44/f02',
            '/osg-web0004/open/c44/f03',
            '/osg-web0004/open/c44/f04',
        ]
        
        for api in interesting_apis:
            for i, params in enumerate(qr_params_variants):
                ts = int(time.time() * 1000)
                
                wrapped = {'_access_token': '', '_t': '', '_data': params, 'timestamp': ts}
                encrypted = a(json_dumps(wrapped), keyCode)
                req_payload = {
                    'data': encrypted + c(encrypted + str(ts)),
                    'skey': d(keyCode, publicKey),
                    'timestamp': str(ts),
                }
                
                test_headers = dict(headers)
                test_headers['timestamp'] = str(ts)
                test_headers['sessionId'] = 'web' + str(ts)
                test_headers['keyCode'] = keyCode
                
                try:
                    async with session.post(baseApi + api, json=req_payload, headers=test_headers, ssl=False) as resp:
                        text = await resp.text()
                        if text.startswith('{'):
                            result = json.loads(text)
                            if 'encryptData' in result:
                                decrypted = b(result['encryptData'], keyCode)
                                result = json.loads(decrypted)
                            
                            code = result.get('code', '?')
                            msg = ''
                            data_keys = []
                            if 'data' in result and result['data']:
                                if isinstance(result['data'], dict):
                                    data_keys = list(result['data'].keys())
                                    if 'srvrt' in result['data']:
                                        msg = result['data'].get('srvrt', {}).get('resultMessage', '')
                            elif 'message' in result:
                                msg = result['message']
                            
                            status = "✅" if str(code) == '1' else "  "
                            print(f"  {status} {api} params#{i}: code={code}, keys={data_keys}, msg={msg[:80]}")
                            
                            if str(code) == '1':
                                print(f"      完整: {json.dumps(result, ensure_ascii=False)[:800]}")
                except Exception as ex:
                    print(f"  ❌ {api} params#{i}: {ex}")
                
                await asyncio.sleep(0.3)

        # ======== 步骤4: 尝试从95598网页JS中找二维码API ========
        print("\n" + "=" * 60)
        print("步骤4: 抓取95598登录页JS，寻找二维码API")
        print("=" * 60)
        
        js_urls = [
            'https://www.95598.cn/osgweb/static/js/app.js',
            'https://www.95598.cn/osgweb/static/js/chunk-vendors.js',
        ]
        
        # 先从登录页HTML中找JS文件
        try:
            async with session.get(
                'https://www.95598.cn/osgweb/login',
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                },
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                html = await resp.text()
                # 找JS文件路径
                js_matches = re.findall(r'src=["\'](/osgweb/static/js/[^"\']+\.js)["\']', html)
                js_matches += re.findall(r'src=["\']([^"\']+\.js)["\']', html)
                print(f"  找到JS文件: {js_matches[:10]}")
                
                # 在HTML中搜索二维码相关内容
                qr_keywords = ['qr', 'qrcode', 'sweep', 'scan', '扫码', '二维码', 'erweima', 'saoma']
                for kw in qr_keywords:
                    if kw.lower() in html.lower():
                        # 找到关键词周围的上下文
                        idx = html.lower().find(kw.lower())
                        context = html[max(0,idx-100):idx+200]
                        print(f"  HTML中找到 '{kw}': ...{context[:200]}...")
        except Exception as ex:
            print(f"  抓取登录页失败: {ex}")

        # ======== 步骤5: 尝试直接请求二维码页面 ========
        print("\n" + "=" * 60)
        print("步骤5: 尝试95598扫码登录页面")
        print("=" * 60)
        
        scan_urls = [
            'https://www.95598.cn/osgweb/scanlogin',
            'https://www.95598.cn/osgweb/qrlogin',
            'https://www.95598.cn/osgweb/saomalogn',
            'https://www.95598.cn/sc/app.html#/scanLogin',
            'https://www.95598.cn/sc/app.html#/qrcode',
        ]
        
        for url in scan_urls:
            try:
                async with session.get(
                    url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=10),
                    allow_redirects=False
                ) as resp:
                    print(f"  {url}: HTTP {resp.status}")
                    if resp.status == 200:
                        text = await resp.text()
                        # 搜索QR相关内容
                        for kw in ['qr', 'qrcode', 'scan', 'sweep']:
                            if kw in text.lower():
                                idx = text.lower().find(kw)
                                print(f"    找到 '{kw}': {text[max(0,idx-50):idx+100][:150]}")
            except Exception as ex:
                print(f"  {url}: 失败 {ex}")


if __name__ == '__main__':
    asyncio.run(main())
