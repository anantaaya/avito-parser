# -*- coding: utf-8 -*-
import json
import asyncio
import random
from playwright.async_api import async_playwright
import config

async def check_captcha(page):
    selectors = [
        'iframe[src*="captcha"]:visible',
        '.captcha:visible',
        '[data-marker="captcha"]:visible',
        'form[action*="captcha"]:visible',
        'div:has-text("Я не робот"):visible',
        'div:has-text("Введите код"):visible',
        'div:has-text("подтвердите"):visible',
    ]
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                return True
        except:
            pass
    return False

async def wait_and_resolve_captcha(page):
    """Ожидает загрузки страницы: либо капча решается, либо загружаются объявления."""
    max_retries = 3
    for attempt in range(max_retries):
        # Проверяем капчу
        if await check_captcha(page):
            print("\n[!!!] Обнаружена капча! Решите её вручную в браузере.")
            user_input = input("После решения нажмите Enter (или 'skip' для пропуска): ")
            if user_input.strip().lower() == 'skip':
                print("⏩ Пропускаем проверку капчи.")
                await page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(2)
                # После перезагрузки проверяем наличие объявлений
                try:
                    await page.wait_for_selector('[data-marker="item"]', timeout=10000)
                    return True
                except:
                    print(f"⚠️ После перезагрузки объявления не найдены (попытка {attempt+1})")
                    continue
            else:
                # Ждём, пока пользователь решит капчу
                await page.wait_for_timeout(3000)
                await page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(2)
                # Проверяем, появились ли объявления
                try:
                    await page.wait_for_selector('[data-marker="item"]', timeout=10000)
                    return True
                except:
                    print(f"⚠️ После решения капчи объявления не найдены (попытка {attempt+1})")
                    continue
        else:
            print("✅ Капча не обнаружена. Ожидаем загрузки объявлений...")
            try:
                await page.wait_for_selector('[data-marker="item"]', timeout=10000)
                return True
            except:
                print(f"⚠️ Объявления не найдены. Перезагружаем страницу (попытка {attempt+1})")
                await page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(2)
                continue
    print("❌ Не удалось загрузить объявления после нескольких попыток.")
    return False

async def get_page_urls(page):
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(2)
    try:
        await page.wait_for_selector('.pagination-pages', timeout=5000)
    except:
        pass
    urls = await page.evaluate('''
        () => {
            const links = [];
            document.querySelectorAll('.pagination-pages a.pagination-page').forEach(el => {
                const href = el.getAttribute('href');
                if (href) {
                    const url = new URL(href, window.location.origin);
                    links.push(url.href);
                }
            });
            if (links.length === 0) {
                const pagination = document.querySelector('[data-marker="pagination-button"]');
                if (pagination) {
                    pagination.querySelectorAll('a[href*="?p="], a[href*="&p="]').forEach(el => {
                        const href = el.getAttribute('href');
                        if (href && !href.includes('javascript:')) {
                            const url = new URL(href, window.location.origin);
                            if (!links.includes(url.href)) links.push(url.href);
                        }
                    });
                }
            }
            return links;
        }
    ''')
    return urls

async def collect_page_data(page):
    """Собирает данные с карточек (предполагается, что они уже загружены)."""
    # Не ждём селектор, просто собираем то, что есть
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(2)

    data = await page.evaluate('''
        () => {
            const items = document.querySelectorAll('[data-marker="item"]');
            const results = [];
            items.forEach(el => {
                const linkEl = el.querySelector('a[href*="/"]');
                const url = linkEl ? linkEl.href : null;
                let id = null;
                if (url) {
                    const match = url.match(/_(\\d+)$/);
                    if (match) id = match[1];
                }
                const titleEl = el.querySelector('[data-marker="item-title"]');
                const title = titleEl ? titleEl.textContent.trim() : null;
                const priceEl = el.querySelector('[data-marker="item-price-value"]');
                const price = priceEl ? priceEl.textContent.trim() : null;
                const dateEl = el.querySelector('[data-marker="item-date"]');
                const date = dateEl ? dateEl.textContent.trim() : null;

                results.push({
                    id: id,
                    title: title,
                    price: price,
                    date: date,
                    url: url
                });
            });
            return results;
        }
    ''')
    return data

async def main():
    all_results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=config.HEADLESS)
        context = await browser.new_context(
            user_agent=config.USER_AGENT,
            viewport=config.VIEWPORT
        )
        page = await context.new_page()

        print(f"\n--- Загрузка первой страницы ---")
        await page.goto(config.BASE_URL, wait_until="domcontentloaded", timeout=config.TIMEOUT)

        if not await wait_and_resolve_captcha(page):
            print("⏭️ Не удалось решить капчу. Завершаем.")
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
        unique_urls.sort()

        print(f"Найдено страниц: {len(unique_urls)}")

        if config.MAX_PAGES is not None and len(unique_urls) > config.MAX_PAGES - 1:
            unique_urls = unique_urls[:config.MAX_PAGES - 1]

        first_url = page.url
        if unique_urls and unique_urls[0] == first_url:
            unique_urls.pop(0)
        unique_urls = [url for url in unique_urls if 'p=1' not in url]

        for idx, url in enumerate(unique_urls, start=2):
            print(f"\n--- Страница {idx} --- {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=config.TIMEOUT)

            if not await wait_and_resolve_captcha(page):
                print("⏭️ Пропускаем страницу из-за капчи.")
                continue

            items = await collect_page_data(page)
            if items:
                print(f"✅ Найдено {len(items)} объявлений на странице {idx}")
                all_results.extend(items)
            else:
                print(f"⚠️ На странице {idx} объявлений нет, пропускаем.")

            await asyncio.sleep(random.uniform(*config.DELAY_BETWEEN_PAGES))

        await browser.close()

    with open(config.OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Готово! Собрано {len(all_results)} объявлений с {len(unique_urls)+1} страниц.")
    print(f"📁 Файл: {config.OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
