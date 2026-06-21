#!/usr/bin/env python3
"""
95598 二维码登录 API 探索 v4
使用 Playwright 浏览器自动化来观察 95598 扫码登录的网络请求
"""

import asyncio
import json
import re

async def main():
    from playwright.async_api import async_playwright
    
    print("=" * 60)
    print("使用 Playwright 探索 95598 扫码登录 API")
    print("=" * 60)
    
    api_calls = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        page = await context.new_page()
        
        # 拦截所有网络请求
        async def handle_request(request):
            url = request.url
            if '95598.cn' in url and '/api/' in url:
                api_calls.append({
                    'url': url,
                    'method': request.method,
                    'post_data': request.post_data[:200] if request.post_data else None,
                })
                print(f"  REQUEST: {request.method} {url}")
                if request.post_data:
                    print(f"    body: {request.post_data[:200]}")
        
        async def handle_response(response):
            url = response.url
            if '95598.cn' in url and '/api/' in url:
                try:
                    text = await response.text()
                    # 尝试解析
                    if text.startswith('{'):
                        result = json.loads(text)
                        # 检查是否有二维码相关内容
                        result_str = json.dumps(result, ensure_ascii=False)[:300]
                        # 搜索QR相关关键词
                        if any(kw in result_str.lower() for kw in ['qr', 'scan', 'sweep', 'code', 'serial', 'ticket']):
                            print(f"  RESPONSE (QR相关): {url}")
                            print(f"    {result_str}")
                        else:
                            print(f"  RESPONSE: {url} (len={len(text)})")
                    else:
                        print(f"  RESPONSE: {url} (non-JSON, len={len(text)})")
                except Exception as ex:
                    print(f"  RESPONSE: {url} (error: {ex})")
        
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        # 访问登录页
        print("\n访问登录页...")
        try:
            await page.goto('https://www.95598.cn/osgweb/login', wait_until='networkidle', timeout=30000)
        except Exception as ex:
            print(f"  页面加载超时: {ex} (继续)")
        
        # 等一下让页面完全渲染
        await asyncio.sleep(3)
        
        # 搜索页面中的扫码相关元素
        print("\n搜索页面中的扫码元素...")
        
        # 查找所有按钮和链接
        elements = await page.query_selector_all('div, button, a, span, p, li')
        for el in elements[:200]:
            try:
                text = await el.text_content()
                if text and any(kw in text for kw in ['扫码', '二维码', 'QR', 'qr', '扫一扫']):
                    tag = await el.evaluate('el => el.tagName')
                    cls = await el.evaluate('el => el.className')
                    print(f"  找到: <{tag}> class='{cls}' text='{text.strip()[:50]}'")
            except:
                pass
        
        # 查找class名含qr/scan/sweep的元素
        print("\n搜索CSS类名...")
        qr_elements = await page.query_selector_all('[class*="qr"], [class*="scan"], [class*="sweep"], [class*="QR"]')
        for el in qr_elements:
            cls = await el.evaluate('el => el.className')
            text = await el.text_content()
            print(f"  QR元素: class='{cls}' text='{(text or "").strip()[:50]}'")
        
        # 获取页面HTML
        print("\n获取页面HTML（搜索QR相关内容）...")
        html = await page.content()
        print(f"  HTML大小: {len(html)} bytes")
        
        for kw in ['qr', 'QR', 'scan', 'Scan', 'sweep', 'Sweep', '扫码', '二维码', 'erweima', 'saoma']:
            idx = html.lower().find(kw.lower())
            if idx >= 0:
                context = html[max(0,idx-100):idx+200].replace('\n', ' ')
                print(f"  '{kw}' 在HTML中: ...{context[:250]}...")
        
        # 获取页面中的JS变量和函数
        print("\n搜索JS全局变量中的QR相关信息...")
        try:
            qr_info = await page.evaluate("""() => {
                const results = [];
                // 检查window上的属性
                for (let key of Object.keys(window)) {
                    const val = String(window[key]);
                    if (val && (val.toLowerCase().includes('qr') || val.toLowerCase().includes('scan') || val.toLowerCase().includes('sweep'))) {
                        results.push({key, val: val.substring(0, 200)});
                    }
                }
                return results;
            }""")
            if qr_info:
                for item in qr_info:
                    print(f"  window.{item['key']}: {item['val'][:100]}")
            else:
                print("  未找到QR相关全局变量")
        except Exception as ex:
            print(f"  JS评估失败: {ex}")
        
        # 尝试点击"扫码登录"按钮（如果有）
        print("\n尝试查找并点击扫码登录按钮...")
        try:
            # 查找包含"扫码"或"二维码"的元素
            scan_btn = await page.query_selector('text=扫码')
            if not scan_btn:
                scan_btn = await page.query_selector('text=二维码')
            if not scan_btn:
                scan_btn = await page.query_selector('text=扫一扫')
            if not scan_btn:
                # 尝试class选择器
                scan_btn = await page.query_selector('.sweep_code, .qr_code, .scan-login, [class*="qr"]')
            
            if scan_btn:
                print("  找到扫码按钮，点击...")
                await scan_btn.click()
                await asyncio.sleep(3)
                
                # 拦截点击后的API请求
                print("  点击后的API调用:")
                for call in api_calls[-10:]:
                    print(f"    {call['method']} {call['url']}")
                
                # 查找二维码图片
                print("\n  查找二维码图片...")
                qr_img = await page.query_selector('img[src*="data:image"]')
                if qr_img:
                    src = await qr_img.get_attribute('src')
                    print(f"  找到二维码图片: {src[:100]}...")
                else:
                    # 尝试canvas
                    canvas = await page.query_selector('canvas')
                    if canvas:
                        print("  找到canvas元素（可能含二维码）")
                    else:
                        print("  未找到二维码图片")
            else:
                print("  未找到扫码登录按钮")
                
                # 截图看看页面长什么样
                await page.screenshot(path='/home/z/my-project/download/95598_login_screenshot.png')
                print("  已截图保存到 download/95598_login_screenshot.png")
                
                # 打印页面文本内容
                page_text = await page.text_content('body')
                if page_text:
                    print(f"\n  页面文本内容（前500字）:")
                    print(f"  {page_text[:500]}")
        
        except Exception as ex:
            print(f"  操作失败: {ex}")
        
        # 输出所有捕获的API调用
        print("\n" + "=" * 60)
        print(f"总共捕获 {len(api_calls)} 个API调用")
        print("=" * 60)
        for call in api_calls:
            print(f"  {call['method']} {call['url']}")
        
        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
