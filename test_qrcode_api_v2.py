#!/usr/bin/env python3
"""
95598 二维码登录 API 探索 v2
从 JS 文件中提取二维码相关 API
"""

import aiohttp
import asyncio
import re
import json

async def main():
    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        
        # 下载主JS文件
        js_url = 'https://www.95598.cn/osgweb/static/js/app.3a8b43af.js'
        print(f"下载JS: {js_url}")
        
        async with session.get(
            js_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            },
            ssl=False,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            js_text = await resp.text()
            print(f"  JS大小: {len(js_text)} bytes")
        
        # 搜索二维码/扫码相关的关键词
        print("\n" + "=" * 60)
        print("搜索JS中的二维码相关关键词")
        print("=" * 60)
        
        qr_keywords = [
            'qrCode', 'qrcode', 'QRCode', 'scanCode', 'scanLogin',
            'sweepCode', 'sweep_code', 'saoMa', 'erWeiMa',
            'getQrCode', 'createQrCode', 'generateQrCode',
            'checkScan', 'scanResult', 'scanStatus', 'queryScan',
            'loginByQr', 'qrLogin', 'qr_login',
            'getLoginQrCode', 'loginQrCode',
        ]
        
        for kw in qr_keywords:
            # 在JS中查找关键词（不区分大小写）
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            matches = list(pattern.finditer(js_text))
            if matches:
                print(f"\n  找到 '{kw}' ({len(matches)}次):")
                for m in matches[:5]:  # 只显示前5次
                    start = max(0, m.start() - 80)
                    end = min(len(js_text), m.end() + 120)
                    context = js_text[start:end].replace('\n', ' ').replace('\r', '')
                    print(f"    ...{context}...")

        # 搜索API路径中包含qr/scan/sweep的
        print("\n" + "=" * 60)
        print("搜索API路径模式")
        print("=" * 60)
        
        api_patterns = [
            r'["\'](/osg-web[^"\']*?)["\']',
            r'["\'](/oauth2[^"\']*?)["\']',
            r'["\'](/osg-open[^"\']*?)["\']',
            r'["\'](/api[^"\']*?)["\']',
        ]
        
        all_apis = set()
        for pattern in api_patterns:
            matches = re.findall(pattern, js_text)
            for m in matches:
                all_apis.add(m)
        
        # 按路径排序
        for api in sorted(all_apis):
            # 检查是否与扫码/二维码/登录相关
            lower = api.lower()
            if any(kw in lower for kw in ['qr', 'scan', 'sweep', 'login', 'auth', 'c44', 'f0']):
                print(f"  🔍 {api}")
            else:
                print(f"  {api}")

        # 搜索可能的API函数名
        print("\n" + "=" * 60)
        print("搜索可能的API端点函数名")
        print("=" * 60)
        
        func_patterns = [
            r'getLoginQr[A-Za-z]*',
            r'createQr[A-Za-z]*',
            r'queryScan[A-Za-z]*',
            r'checkScan[A-Za-z]*',
            r'scanLogin[A-Za-z]*',
            r'sweepCode[A-Za-z]*',
            r'qrCode[A-Za-z]*',
            r'f0\d+',
        ]
        
        for pat in func_patterns:
            matches = re.findall(pat, js_text, re.IGNORECASE)
            if matches:
                unique = list(set(matches))[:10]
                print(f"  {pat}: {unique}")

        # 搜索vue-router中的扫码登录路由
        print("\n" + "=" * 60)
        print("搜索Vue Router路由")
        print("=" * 60)
        
        route_patterns = [
            r'path:\s*["\']([^"\']*scan[^"\']*)["\']',
            r'path:\s*["\']([^"\']*qr[^"\']*)["\']',
            r'path:\s*["\']([^"\']*sweep[^"\']*)["\']',
            r'path:\s*["\']([^"\']*login[^"\']*)["\']',
            r'name:\s*["\']([^"\']*scan[^"\']*)["\']',
            r'name:\s*["\']([^"\']*qr[^"\']*)["\']',
            r'name:\s*["\']([^"\']*sweep[^"\']*)["\']',
        ]
        
        for pat in route_patterns:
            matches = re.findall(pat, js_text, re.IGNORECASE)
            if matches:
                print(f"  {pat}: {list(set(matches))[:10]}")

        # 搜索门店/国家电网App扫码登录相关
        print("\n" + "=" * 60)
        print("搜索App扫码登录相关代码")
        print("=" * 60)
        
        app_patterns = [
            r'sgapp[^"\']*',
            r'SGAPP[^"\']*',
            r'appScan[A-Za-z]*',
            r'appQr[A-Za-z]*',
        ]
        
        for pat in app_patterns:
            matches = re.findall(pat, js_text)
            if matches:
                unique = list(set(matches))[:5]
                print(f"  {pat}: {unique}")

        # 下载 vendors JS
        print("\n" + "=" * 60)
        print("下载vendors JS搜索更多API")
        print("=" * 60)
        
        vendors_url = 'https://www.95598.cn/osgweb/static/js/vendors~app.2b2bbea1.js'
        try:
            async with session.get(
                vendors_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                vendors_js = await resp.text()
                print(f"  vendors JS大小: {len(vendors_js)} bytes")
                
                # 搜索API路径
                v_apis = set()
                for pattern in api_patterns:
                    matches = re.findall(pattern, vendors_js)
                    for m in matches:
                        v_apis.add(m)
                
                for api in sorted(v_apis):
                    lower = api.lower()
                    if any(kw in lower for kw in ['qr', 'scan', 'sweep', 'login', 'auth', 'c44']):
                        print(f"  🔍 {api}")
        except Exception as ex:
            print(f"  下载失败: {ex}")

        # 尝试请求国家电网App的扫码登录接口
        print("\n" + "=" * 60)
        print("步骤6: 探索App端扫码登录API")
        print("=" * 60)
        
        # 很多国网App扫码登录使用不同的API组
        app_scan_apis = [
            '/osg-web0004/open/c01/f01',  # 不同的业务组
            '/osg-web0004/open/c02/f01',
            '/osg-web0004/open/c03/f01',
            '/osg-open-uc0001/open/c01/f01',  # 用户中心
            '/osg-open-uc0001/open/c01/f02',
            '/osg-open-uc0001/member/c9/f01',
            '/osg-open-uc0001/member/c9/f03',
            '/osg-open-uc0001/member/c9/f04',
        ]
        
        for api in app_scan_apis:
            try:
                ts = int(asyncio.get_event_loop().time() * 1000)
                async with session.get(
                    baseApi + api,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/json',
                        'appKey': appKey,
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    print(f"  GET {api}: HTTP {resp.status}")
            except Exception as ex:
                print(f"  GET {api}: 失败")


if __name__ == '__main__':
    appKey = '7e5b5e84ddad4994b0ebc68dedca4962'
    baseApi = 'https://www.95598.cn/api'
    asyncio.run(main())
