"""
95598 二维码扫码登录 - 轮询状态测试

核心发现：
- c8/f24 既能获取二维码(optType=01)，也能查询扫码状态(optType=02)
- 轮询时重复调用 c8/f24，检查响应中是否有 token 信息
"""
import asyncio
import sys
import os
import json
import time
import base64
import importlib.util

_crypt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
    'custom_components', 'state_grid', 'utils', 'crypt.py')
_spec = importlib.util.spec_from_file_location('crypt', _crypt_path)
_crypt_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_crypt_mod)
a, b, c, d, e = _crypt_mod.a, _crypt_mod.b, _crypt_mod.c, _crypt_mod.d, _crypt_mod.e

appKey = '7e5b5e84ddad4994b0ebc68dedca4962'
appSecret = '2bc37a881e1541aaa6e6e174658d150b'
baseApi = 'https://www.95598.cn/api'
DEFAULT_PUBLIC_KEY = '042D12DFBC179202AC4B7B7BADCDA6FF7B604339263F6AB732CE7107B7EA3830A2CA714DC303920D3CFF7647D898F1A8CC6C24E9EC3CC194E22D984AF7E16B42DC'

def json_dumps(data):
    return json.dumps(data, separators=(',', ':'), ensure_ascii=False)

import aiohttp

async def get_key():
    """获取加密密钥"""
    ts = int(time.time() * 1000)
    keyCode = e(32, 16, 2)
    payload = {'client_id': appKey, 'client_secret': appSecret}
    encrypted = a(json_dumps(payload), keyCode)
    data = {
        'data': encrypted + c(encrypted + str(ts)),
        'skey': d(keyCode, DEFAULT_PUBLIC_KEY),
        'client_id': appKey,
        'timestamp': str(ts),
    }
    headers = {
        'Accept': 'application/json;charset=UTF-8',
        'Content-Type': 'application/json;charset=UTF-8',
        'version': '1.0', 'source': '0901', 'timestamp': str(ts),
        'wsgwType': 'web', 'appKey': appKey,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(baseApi + '/oauth2/outer/c02/f02', json=data, headers=headers) as resp:
            text = await resp.text()
            result = json.loads(text)
            # 解密加密响应
            if 'encryptData' in result:
                decrypted = b(result['encryptData'], keyCode)
                result = json.loads(decrypted)
            if str(result.get('code')) == '1':
                return result['data']['keyCode'], result['data']['publicKey']
    return None, None

async def get_qr_code(keyCode, publicKey):
    """获取二维码"""
    import random
    serialNo = str(int(time.time() * 1000)) + str(random.randint(100000, 999999))
    ts = int(time.time() * 1000)
    
    data = {
        '_access_token': '',
        '_t': '',
        '_data': {
            'uscInfo': {'devciceIp': '', 'tenant': 'state_grid', 'member': '0902', 'devciceId': ''},
            'quInfo': {'optType': '01', 'serialNo': serialNo},
        },
        'timestamp': ts,
    }
    headers = {
        'Accept': 'application/json;charset=UTF-8',
        'Content-Type': 'application/json;charset=UTF-8',
        'version': '1.0', 'source': '0901', 'timestamp': str(ts),
        'wsgwType': 'web', 'appKey': appKey,
        'Origin': 'https://www.95598.cn', 'Referer': 'https://www.95598.cn/osgweb/login',
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(baseApi + '/osg-open-uc0001/member/c8/f24', json=data, headers=headers) as resp:
            result = json.loads(await resp.text())
            print(f"[c8/f24] code={result.get('code')}, message={result.get('message')}")
            
            if 'data' in result and isinstance(result['data'], dict):
                bizrt = result['data'].get('bizrt', {})
                if 'qrCode' in bizrt:
                    qr_bytes = base64.b64decode(bizrt['qrCode'])
                    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'download', 'qrcode_login.png')
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    with open(save_path, 'wb') as f:
                        f.write(qr_bytes)
                    print(f"✅ 二维码已保存: {save_path}")
                # 打印 bizrt 的所有字段
                print(f"  bizrt keys: {list(bizrt.keys())}")
                for k, v in bizrt.items():
                    if k != 'qrCode':
                        print(f"  {k}: {str(v)[:100]}")
            
            return serialNo, result

async def poll_qr_status_c8f24(keyCode, publicKey, serialNo, max_polls=30, interval=3):
    """使用 c8/f24 轮询扫码状态 (optType=02)"""
    print(f"\n[c8/f24] 轮询扫码状态 (optType=02)...")
    
    for i in range(max_polls):
        ts = int(time.time() * 1000)
        
        # 尝试 optType=02 (查询状态)
        data = {
            '_access_token': '',
            '_t': '',
            '_data': {
                'uscInfo': {'devciceIp': '', 'tenant': 'state_grid', 'member': '0902', 'devciceId': ''},
                'quInfo': {'optType': '02', 'serialNo': serialNo},
            },
            'timestamp': ts,
        }
        headers = {
            'Accept': 'application/json;charset=UTF-8',
            'Content-Type': 'application/json;charset=UTF-8',
            'version': '1.0', 'source': '0901', 'timestamp': str(ts),
            'wsgwType': 'web', 'appKey': appKey,
            'Origin': 'https://www.95598.cn', 'Referer': 'https://www.95598.cn/osgweb/login',
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(baseApi + '/osg-open-uc0001/member/c8/f24', json=data, headers=headers) as resp:
                result = json.loads(await resp.text())
        
        code = result.get('code')
        message = result.get('message', '')
        
        if 'data' in result and isinstance(result['data'], dict):
            srvrt = result['data'].get('srvrt', {})
            bizrt = result['data'].get('bizrt', {})
            rc = srvrt.get('resultCode', '')
            rm = srvrt.get('resultMessage', '')
            
            if rc == '0000':
                print(f"\n✅ 扫码成功!")
                print(f"  bizrt keys: {list(bizrt.keys())}")
                for k, v in bizrt.items():
                    print(f"  {k}: {str(v)[:100]}")
                return result
            elif rc:
                print(f"  [{i+1}/{max_polls}] rc={rc}, msg={rm}")
            else:
                # Print first 3 full responses for debugging
                if i < 3:
                    rstr = json.dumps(result, ensure_ascii=False)
                    print(f"  [{i+1}] 完整响应: {rstr[:400]}")
                else:
                    print(f"  [{i+1}/{max_polls}] code={code}, message={message}")
        else:
            if i < 3:
                rstr = json.dumps(result, ensure_ascii=False)
                print(f"  [{i+1}] 完整响应: {rstr[:400]}")
            else:
                print(f"  [{i+1}/{max_polls}] code={code}, message={message}")
        
        await asyncio.sleep(interval)
    
    print("❌ 轮询超时")
    return None

async def main():
    print("=" * 60)
    print("95598 二维码扫码登录 - c8/f24 轮询测试")
    print("=" * 60)
    
    keyCode, publicKey = await get_key()
    if not keyCode:
        print("❌ 获取密钥失败")
        return
    print(f"✅ 密钥获取成功")
    
    serialNo, _ = await get_qr_code(keyCode, publicKey)
    if not serialNo:
        print("❌ 二维码获取失败")
        return
    
    print(f"\n请用网上国网APP扫描二维码! serialNo: {serialNo}")
    await poll_qr_status_c8f24(keyCode, publicKey, serialNo, max_polls=30, interval=3)

if __name__ == '__main__':
    asyncio.run(main())
