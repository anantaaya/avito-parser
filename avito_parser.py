# -*- coding: utf-8 -*-
import json
import asyncio
import random
from playwright.async_api import async_playwright

async def check_captcha(page):
    # ... (без изменений)
    pass

async def wait_and_resolve_captcha(page):
    # ... (без изменений)
    pass

async def get_page_urls(page):
    # ... (без изменений)
    pass

async def collect_page_data(page):
    # ... (без изменений)
    pass

async def main():
    BASE_URL = "https://www.avito.ru/all/noutbuki/b_u-ASgBAgICAUTwvA2I0jQ?cd=1&d=1&f=ASgBAgECAUTwvA2I0jQCRcaaDBl7ImZyb20iOjE1MDAwLCJ0byI6MzUwMDB9nKEUFXsiZnJvbSI6MzIsInRvIjpudWxsfQ"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        all_results = []

        print(f"\n--- Загрузка первой страницы ---")
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)

        if not await wait_and_resolve_captcha(page):
            print("⏭️ Пропускаем первую страницу из-за капчи.")
            await browser.close()
            return

        items = await collect_page_data(page)
        print(f"✅ Найдено {len(items)} объявлений на странице 1")
        all_results.extend(items)

        page_urls = await get_page_urls(page)
        unique_urls = []
        seen = set()
        for url in page_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        if unique_urls and unique_urls[0] == page.url:
            unique_urls.pop(0)
        unique_urls = [url for url in unique_urls if 'p=1' not in url]

        print(f"Найдено страниц: {len(unique_urls)}")

        for idx, url in enumerate(unique_urls, start=2):
            print(f"\n--- Страница {idx} --- {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            if not await wait_and_resolve_captcha(page):
                print("⏭️ Пропускаем страницу из-за капчи.")
                continue

            items = await collect_page_data(page)
            if items:
                print(f"✅ Найдено {len(items)} объявлений на странице {idx}")
                all_results.extend(items)
            else:
                print(f"⚠️ На странице {idx} объявлений нет, пропускаем.")

            await asyncio.sleep(random.uniform(3, 6))

        await browser.close()

        with open("avito_all_pages.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        print(f"\n🎉 Готово! Собрано {len(all_results)} объявлений с {len(unique_urls)+1} страниц.")
        print("📁 Файл: avito_all_pages.json")

if __name__ == "__main__":
    asyncio.run(main())
