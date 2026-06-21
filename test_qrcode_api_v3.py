#!/usr/bin/env python3
"""
95598 二维码登录 API 探索 v3
直接访问登录页获取完整HTML，分析前端二维码登录逻辑
"""

import aiohttp
import asyncio
import re
import json

async def main():
    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        
        # 获取登录页完整HTML
        print("=" * 60)
        print("获取95598登录页完整HTML")
        print("=" * 60)
        
        async with session.get(
            'https://www.95598.cn/osgweb/login',
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            },
            ssl=False,
            timeout=aiohttp.ClientTimeout(total=20)
        ) as resp:
            html = await resp.text()
            print(f"  HTML大小: {len(html)} bytes")
            print(f"  HTTP状态: {resp.status}")
        
        # 保存HTML
        with open('/home/z/my-project/download/95598_login.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("  已保存到 /home/z/my-project/download/95598_login.html")
        
        # 提取所有JS路径
        js_files = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html)
        print(f"\n  找到JS文件: {js_files}")
        
        # 提取CSS路径
        css_files = re.findall(r'href=["\']([^"\']+\.css[^"\']*)["\']', html)
        print(f"  找到CSS文件: {css_files}")
        
        # 搜索HTML中的QR相关内容
        print("\n" + "=" * 60)
        print("HTML中的QR/扫码相关内容")
        print("=" * 60)
        
        for kw in ['qr', 'QR', 'scan', 'Scan', 'sweep', 'Sweep', '扫码', '二维码']:
            idx = 0
            count = 0
            while True:
                idx = html.find(kw, idx)
                if idx == -1:
                    break
                count += 1
                start = max(0, idx - 100)
                end = min(len(html), idx + 150)
                context = html[start:end].replace('\n', ' ').replace('\r', '')
                if count <= 5:
                    print(f"  '{kw}' 位置{idx}: ...{context}...")
                idx += len(kw)
            if count > 5:
                print(f"  '{kw}' 共出现 {count} 次")
            elif count == 0:
                pass  # 不打印没找到的
        
        # 下载每个JS文件并搜索
        print("\n" + "=" * 60)
        print("下载JS文件搜索二维码API")
        print("=" * 60)
        
        for js_file in js_files:
            # 处理相对路径
            if js_file.startswith('../'):
                js_url = 'https://www.95598.cn/osgweb/' + js_file.replace('../', '')
            elif js_file.startswith('/'):
                js_url = 'https://www.95598.cn' + js_file
            elif js_file.startswith('http'):
                js_url = js_file
            else:
                js_url = 'https://www.95598.cn/osgweb/static/' + js_file
            
            print(f"\n  下载: {js_url}")
            try:
                async with session.get(
                    js_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': '*/*',
                        'Referer': 'https://www.95598.cn/osgweb/login',
                    },
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        js_text = await resp.text()
                        print(f"    大小: {len(js_text)} bytes")
                        
                        # 搜索二维码相关关键词
                        qr_found = False
                        for kw in ['qrCode', 'qrcode', 'QRCode', 'scanLogin', 'sweepCode', 'sweep_code', 
                                   'getQrCode', 'checkScan', 'scanResult', 'qrLogin', 'loginByQr',
                                   'saoMa', 'erWeiMa', '扫码', '二维码']:
                            matches = list(re.finditer(re.escape(kw), js_text, re.IGNORECASE))
                            if matches:
                                qr_found = True
                                print(f"    🔍 '{kw}' 出现{len(matches)}次")
                                for m in matches[:3]:
                                    start = max(0, m.start() - 120)
                                    end = min(len(js_text), m.end() + 200)
                                    context = js_text[start:end].replace('\n', ' ')
                                    print(f"      ...{context[:300]}...")
                        
                        # 搜索API路径
                        api_matches = re.findall(r'["\'](/osg[^"\']{5,50})["\']', js_text)
                        if api_matches:
                            unique_apis = list(set(api_matches))
                            for api in sorted(unique_apis):
                                lower = api.lower()
                                marker = "🔍" if any(k in lower for kw in ['qr', 'scan', 'sweep', 'login', 'c44', 'f0'] for k in [kw]) else "  "
                                print(f"    {marker} API: {api}")
                        
                        # 如果文件很大且有内容，保存到文件
                        if len(js_text) > 5000:
                            fname = js_url.split('/')[-1]
                            with open(f'/home/z/my-project/download/95598_{fname}', 'w', encoding='utf-8') as f:
                                f.write(js_text)
                            print(f"    已保存到 /home/z/my-project/download/95598_{fname}")
                    else:
                        print(f"    HTTP {resp.status}")
            except Exception as ex:
                print(f"    失败: {ex}")


if __name__ == '__main__':
    asyncio.run(main())
