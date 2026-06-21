"""
95598 二维码扫码登录 API 测试脚本

研究发现的 API 流程:
1. POST /api/oauth2/outer/c02/f02 - 获取加密密钥 (keyCode + publicKey)
2. POST /api/osg-web0004/open/c1/f01 - 创建二维码会话 (加密格式)
3. POST /api/osg-open-uc0001/member/c8/f24 - 获取二维码图片 (明文格式)
4. POST /api/osg-web0004/open/c50/f02 - 轮询扫码状态 (加密格式)
5. 扫码成功后 → authorize → getWebToken (与密码登录相同)
"""

import asyncio
import sys
import os
import json
import time
import base64
import importlib.util

# 直接导入 crypt 模块（避免触发 homeassistant 依赖）
_crypt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom_components', 'state_grid', 'utils', 'crypt.py')
_spec = importlib.util.spec_from_file_location('crypt', _crypt_path)
_crypt_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_crypt_mod)

a = _crypt_mod.a
b = _crypt_mod.b
c = _crypt_mod.c
d = _crypt_mod.d
e = _crypt_mod.e

# ─── API 常量 ───
appKey = '7e5b5e84ddad4994b0ebc68dedca4962'
appSecret = '2bc37a881e1541aaa6e6e174658d150b'
baseApi = 'https://www.95598.cn/api'

get_request_key_api = '/oauth2/outer/c02/f02'
get_request_authorize_api = '/oauth2/oauth/authorize'
get_web_token_api = '/oauth2/outer/getWebToken'

# 二维码登录新增 API
qr_code_session_api = '/osg-web0004/open/c1/f01'        # 创建二维码会话
qr_code_image_api = '/osg-open-uc0001/member/c8/f24'    # 获取二维码图片
qr_code_poll_api = '/osg-web0004/open/c50/f02'           # 轮询扫码状态

# 公钥 (f02 接口返回的默认公钥)
DEFAULT_PUBLIC_KEY = '042D12DFBC179202AC4B7B7BADCDA6FF7B604339263F6AB732CE7107B7EA3830A2CA714DC303920D3CFF7647D898F1A8CC6C24E9EC3CC194E22D984AF7E16B42DC'


def json_dumps(data):
    return json.dumps(data, separators=(',', ':'), ensure_ascii=False)


class QRCodeLoginTester:
    def __init__(self):
        self.keyCode = None
        self.publicKey = None
        self.timestamp = None
        self.accessToken = ''
        self.token = ''
        self.serialNo = ''  # 二维码会话的序列号
        
    async def _post(self, api, payload, headers_extra=None):
        """发送 POST 请求"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            url = baseApi + api
            async with session.post(url, json=payload, headers=headers_extra or {}) as resp:
                text = await resp.text()
                if text.startswith('{'):
                    result = json.loads(text)
                    # 解密加密响应
                    if 'encryptData' in result:
                        decrypted = b(result['encryptData'], self.keyCode)
                        result = json.loads(decrypted)
                    return result
                return {'raw': text[:500]}
    
    async def get_request_key(self):
        """步骤1: 获取加密密钥"""
        self.timestamp = int(time.time() * 1000)
        self.keyCode = e(32, 16, 2)  # 生成随机 keyCode
        
        payload = {'client_id': appKey, 'client_secret': appSecret}
        encrypted = a(json_dumps(payload), self.keyCode)
        
        data = {
            'data': encrypted + c(encrypted + str(self.timestamp)),
            'skey': d(self.keyCode, DEFAULT_PUBLIC_KEY),
            'client_id': appKey,
            'timestamp': str(self.timestamp),
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'application/json;charset=UTF-8',
            'Content-Type': 'application/json;charset=UTF-8',
            'version': '1.0',
            'source': '0901',
            'timestamp': str(self.timestamp),
            'wsgwType': 'web',
            'appKey': appKey,
        }
        
        result = await self._post(get_request_key_api, data, headers)
        print(f"[f02] 获取密钥结果: code={result.get('code')}")
        
        if str(result.get('code', '')) == '1':
            self.keyCode = result['data']['keyCode']
            self.publicKey = result['data']['publicKey']
            print(f"  keyCode: {self.keyCode}")
            print(f"  publicKey: {self.publicKey[:40]}...")
            return True
        else:
            print(f"  错误: {result}")
            return False
    
    def _encrypt_payload(self, data):
        """加密请求数据 (标准加密格式)"""
        self.timestamp = int(time.time() * 1000)
        wrapped = {
            '_access_token': self.accessToken[len(self.accessToken) // 2:] if self.accessToken else '',
            '_t': self.token[len(self.token) // 2:] if self.token else '',
            '_data': data,
            'timestamp': self.timestamp,
        }
        encrypted = a(json_dumps(wrapped), self.keyCode)
        return {
            'data': encrypted + c(encrypted + str(self.timestamp)),
            'skey': d(self.keyCode, self.publicKey),
            'timestamp': str(self.timestamp),
        }
    
    def _get_headers(self, api):
        """获取请求头"""
        self.timestamp = int(time.time() * 1000)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'application/json;charset=UTF-8',
            'Content-Type': 'application/json;charset=UTF-8',
            'version': '1.0',
            'source': '0901',
            'timestamp': str(self.timestamp),
            'wsgwType': 'web',
            'appKey': appKey,
            'Origin': 'https://www.95598.cn',
            'Referer': 'https://www.95598.cn/osgweb/login',
        }
        if api in (qr_code_session_api,):
            headers['keyCode'] = self.keyCode
        return headers
    
    async def create_qr_session(self):
        """步骤2: 创建二维码会话 (c1/f01)"""
        print("\n[c1/f01] 创建二维码会话...")
        
        # 根据浏览器抓包，c1/f01 使用加密格式
        # 请求数据应该是创建二维码会话的参数
        import random
        serial_no = str(int(time.time() * 1000)) + str(random.randint(100000, 999999))
        self.serialNo = serial_no
        
        data = {
            'uscInfo': {
                'devciceIp': '',
                'tenant': 'state_grid',
                'member': '0902',
                'devciceId': '',
            },
            'quInfo': {
                'optType': '01',
                'serialNo': serial_no,
            },
        }
        
        payload = self._encrypt_payload(data)
        headers = self._get_headers(qr_code_session_api)
        headers['keyCode'] = self.keyCode
        
        result = await self._post(qr_code_session_api, payload, headers)
        print(f"  结果: {json.dumps(result, ensure_ascii=False)[:500]}")
        return result
    
    async def get_qr_code_image(self):
        """步骤3: 获取二维码图片 (c8/f24)"""
        print("\n[c8/f24] 获取二维码图片...")
        
        # c8/f24 使用明文格式 (不加密)，与 c9/f02 等成员API类似
        self.timestamp = int(time.time() * 1000)
        
        data = {
            '_access_token': '',
            '_t': '',
            '_data': {
                'uscInfo': {
                    'devciceIp': '',
                    'tenant': 'state_grid',
                    'member': '0902',
                    'devciceId': '',
                },
                'quInfo': {
                    'optType': '01',
                    'serialNo': self.serialNo,
                },
            },
            'timestamp': self.timestamp,
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'application/json;charset=UTF-8',
            'Content-Type': 'application/json;charset=UTF-8',
            'version': '1.0',
            'source': '0901',
            'timestamp': str(self.timestamp),
            'wsgwType': 'web',
            'appKey': appKey,
            'Origin': 'https://www.95598.cn',
            'Referer': 'https://www.95598.cn/osgweb/login',
        }
        
        # 注意：c8/f24 可能有两种调用方式
        # 方式1: 直接明文 POST
        # 方式2: 加密后 POST (像其他 member API)
        
        # 先试加密方式 (与浏览器实际抓包对比，c8/f24 走的是加密格式)
        # 实际从浏览器抓包来看，c8/f24 的请求体是明文JSON
        # 但经过仔细查看，响应中返回了 qrCode base64 数据
        
        result = await self._post(qr_code_image_api, data, headers)
        print(f"  结果 keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
        
        if isinstance(result, dict):
            if 'code' in result:
                print(f"  code: {result['code']}, message: {result.get('message', '')}")
            if 'data' in result and isinstance(result['data'], dict):
                bizrt = result['data'].get('bizrt', {})
                if 'qrCode' in bizrt:
                    qr_base64 = bizrt['qrCode']
                    print(f"  ✅ 获取到二维码! base64长度: {len(qr_base64)}")
                    # 保存二维码图片
                    try:
                        qr_bytes = base64.b64decode(qr_base64)
                        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'download', 'qrcode_login.png')
                        os.makedirs(os.path.dirname(save_path), exist_ok=True)
                        with open(save_path, 'wb') as f:
                            f.write(qr_bytes)
                        print(f"  ✅ 二维码已保存到: {save_path}")
                    except Exception as ex:
                        print(f"  ❌ 保存二维码失败: {ex}")
                    return True
                else:
                    print(f"  bizrt keys: {list(bizrt.keys())}")
            else:
                print(f"  完整结果: {json.dumps(result, ensure_ascii=False)[:500]}")
        else:
            print(f"  结果: {str(result)[:500]}")
        
        return False
    
    async def poll_qr_status(self, max_polls=30, interval=3):
        """步骤4: 轮询扫码状态 (c50/f02)"""
        print(f"\n[c50/f02] 开始轮询扫码状态 (最多{max_polls}次, 间隔{interval}秒)...")
        
        for i in range(max_polls):
            # 尝试两种数据格式
            data = {
                'uscInfo': {
                    'devciceIp': '',
                    'tenant': 'state_grid',
                    'member': '0902',
                    'devciceId': '',
                },
                'quInfo': {
                    'optType': '01',
                    'serialNo': self.serialNo,
                },
            }
            
            payload = self._encrypt_payload(data)
            headers = self._get_headers(qr_code_poll_api)
            
            result = await self._post(qr_code_poll_api, payload, headers)
            
            # 打印完整响应用于调试 (前3次)
            if i < 3:
                result_str = json.dumps(result, ensure_ascii=False)
                print(f"  [{i+1}] 完整响应: {result_str[:500]}")
            
            if isinstance(result, dict):
                code = result.get('code')
                message = result.get('message', '')
                
                # 检查扫码状态
                if 'data' in result and isinstance(result['data'], dict):
                    srvrt = result['data'].get('srvrt', {})
                    result_code = srvrt.get('resultCode', '')
                    result_msg = srvrt.get('resultMessage', '')
                    bizrt = result['data'].get('bizrt', {})
                    
                    if result_code == '0000':
                        print(f"\n  ✅ 扫码成功! bizrt keys: {list(bizrt.keys())}")
                        
                        # 检查是否有 token 信息
                        if 'accessToken' in bizrt:
                            self.accessToken = bizrt['accessToken']
                            print(f"  accessToken: {self.accessToken[:30]}...")
                        if 'token' in bizrt:
                            self.token = bizrt['token']
                            print(f"  token: {self.token[:30]}...")
                        
                        return result
                    
                    elif result_code in ('1001', '1002'):
                        status = "等待扫码" if result_code == '1001' else "已扫码,待确认"
                        print(f"  [{i+1}/{max_polls}] {status} - {result_msg}")
                    else:
                        print(f"  [{i+1}/{max_polls}] resultCode={result_code}, msg={result_msg}, bizrt={list(bizrt.keys())}")
                else:
                    print(f"  [{i+1}/{max_polls}] code={code}, message={message}")
                    if code == 1 and '成功' in message:
                        return result
            else:
                print(f"  [{i+1}/{max_polls}] 非预期响应: {str(result)[:200]}")
            
            await asyncio.sleep(interval)
        
        print("  ❌ 轮询超时，二维码可能已失效")
        return None
    
    async def test_full_flow(self):
        """测试完整的二维码登录流程"""
        print("=" * 60)
        print("95598 二维码扫码登录 API 测试")
        print("=" * 60)
        
        # 步骤1: 获取加密密钥
        if not await self.get_request_key():
            print("❌ 获取密钥失败，终止测试")
            return
        
        # 步骤2: 创建二维码会话
        await self.create_qr_session()
        
        # 步骤3: 获取二维码图片
        qr_ok = await self.get_qr_code_image()
        
        if qr_ok:
            print("\n" + "=" * 60)
            print("✅ 二维码获取成功！请用网上国网APP扫描二维码")
            print("=" * 60)
            
            # 步骤4: 轮询扫码状态
            result = await self.poll_qr_status(max_polls=30, interval=3)
            
            if result:
                print("\n✅ 扫码登录成功！")
                print(f"完整结果: {json.dumps(result, ensure_ascii=False)[:1000]}")
            else:
                print("\n❌ 扫码登录超时")
        else:
            print("\n❌ 二维码获取失败")
            # 尝试直接用 c8/f24 (不先调 c1/f01)
            print("\n--- 尝试跳过 c1/f01，直接调用 c8/f24 ---")
            import random
            self.serialNo = str(int(time.time() * 1000)) + str(random.randint(100000, 999999))
            await self.get_qr_code_image()


async def main():
    tester = QRCodeLoginTester()
    await tester.test_full_flow()


if __name__ == '__main__':
    asyncio.run(main())
