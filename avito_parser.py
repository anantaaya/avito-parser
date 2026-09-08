# -*- coding: utf-8 -*-
import json
import asyncio
import random
from playwright.async_api import async_playwright

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
    attempts = 0
    while True:
        if not await check_captcha(page):
            return True
        attempts += 1
        if attempts > 5:
            print("⚠️ Слишком много попыток. Перезагружаем страницу...")
            await page.reload(wait_until="domcontentloaded")
            await asyncio.sleep(3)
            if not await check_captcha(page):
                return True
            return False
        print("\n[!!!] Обнаружена капча! Решите её вручную в браузере.")
        user_input = input("После решения нажмите Enter (или 'skip' для пропуска): ")
        if user_input.strip().lower() == 'skip':
            print("⏩ Пропускаем проверку капчи.")
            return True
        await page.wait_for_timeout(3000)

async def collect_page_data(page):
    try:
        await page.wait_for_selector('[data-marker="item"]', timeout=10000)
    except:
        print("❗ На странице нет объявлений.")
        return []

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
                    const match = url.match(/\\/(\\d+)_/i);
                    if (match) id = match[1];
                }
                const titleEl = el.querySelector('[data-marker="item-title"]');
                const title = titleEl ? titleEl.textContent.trim() : null;
                const priceEl = el.querySelector('[data-marker="item-price"]');
                const price = priceEl ? priceEl.textContent.trim() : null;
                const addressEl = el.querySelector('[data-marker="item-address"]');
                const address = addressEl ? addressEl.textContent.trim() : null;
                const dateEl = el.querySelector('[data-marker="item-date"]');
                const date = dateEl ? dateEl.textContent.trim() : null;
                const params = [];
                const paramItems = el.querySelectorAll('[data-marker="item-params"] span');
                paramItems.forEach(p => {
                    const text = p.textContent.trim();
                    if (text) params.push(text);
                });

                const sellerBlock = el.querySelector('[data-marker="item-seller"]');
                let sellerName = null, sellerRating = null, sellerAdsCount = null;
                if (sellerBlock) {
                    const nameEl = sellerBlock.querySelector('[itemprop="name"]') ||
                                   sellerBlock.querySelector('.seller-info-name') ||
                                   sellerBlock.querySelector('span:not([class*="rating"])');
                    if (nameEl) sellerName = nameEl.textContent.trim();
                    const ratingEl = sellerBlock.querySelector('[aria-label*="звезд"]') ||
                                     sellerBlock.querySelector('.seller-rating') ||
                                     sellerBlock.querySelector('[data-marker*="rating"]');
                    if (ratingEl) {
                        const ratingText = ratingEl.textContent.trim();
                        const numMatch = ratingText.match(/[\\d.]+/);
                        if (numMatch) sellerRating = parseFloat(numMatch[0]);
                        else sellerRating = ratingText;
                    }
                    const adsEl = sellerBlock.querySelector('[data-marker*="seller-ads"]') ||
                                  sellerBlock.querySelector('.seller-ads-count');
                    if (adsEl) {
                        const adsText = adsEl.textContent.trim();
                        const numMatch = adsText.match(/\\d+/);
                        if (numMatch) sellerAdsCount = parseInt(numMatch[0]);
                    }
                }

                const deliveryEl = el.querySelector('[data-marker="item-delivery"]') ||
                                   el.querySelector('[class*="delivery"]');
                let deliveryInfo = deliveryEl ? deliveryEl.textContent.trim() : null;

                const descEl = el.querySelector('[data-marker="item-description"]') ||
                               el.querySelector('.iva-item-text') ||
                               el.querySelector('[class*="description"]');
                const description = descEl ? descEl.textContent.trim() : null;

                results.push({
                    id: id,
                    title: title,
                    price: price,
                    address: address,
                    date: date,
                    params: params,
                    url: url,
                    seller_name: sellerName,
                    seller_rating: sellerRating,
                    seller_ads_count: sellerAdsCount,
                    delivery_info: deliveryInfo,
                    description_preview: description
                });
            });
            return results;
        }
    ''')
    return data

async def get_page_urls(page):
    """Извлекает все ссылки на страницы из пагинации."""
    # Прокручиваем вниз, чтобы пагинация точно загрузилась
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(2)

    # Ждём появления блока .pagination-pages (он может быть скрыт, но в DOM есть)
    try:
        await page.wait_for_selector('.pagination-pages', timeout=5000)
    except:
        print("⚠️ Блок .pagination-pages не найден.")

    urls = await page.evaluate('''
        () => {
            const links = [];
            // 1) Ищем скрытый блок .pagination-pages
            document.querySelectorAll('.pagination-pages a.pagination-page').forEach(el => {
                const href = el.getAttribute('href');
                if (href) {
                    const url = new URL(href, window.location.origin);
                    links.push(url.href);
                }
            });
            // Если нашли — возвращаем
            if (links.length > 0) return links;

            // 2) Иначе ищем в основном блоке пагинации
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
            return links;
        }
    ''')
    return urls

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

        # Сбор первой страницы
        items = await collect_page_data(page)
        print(f"✅ Найдено {len(items)} объявлений на странице 1")
        all_results.extend(items)

        # Получаем все ссылки на страницы
        page_urls = await get_page_urls(page)
        # Удаляем дубликаты и сортируем
        unique_urls = []
        seen = set()
        for url in page_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        unique_urls.sort()

        print(f"Найдено страниц: {len(unique_urls)}")
        if unique_urls:
            print("Страницы:", [url.split('p=')[-1].split('&')[0] if 'p=' in url else '?' for url in unique_urls])

        # Если ссылок нет — пробуем определить общее количество страниц по тексту
        if not unique_urls:
            total_pages = await page.evaluate('''
                () => {
                    const text = document.body.innerText;
                    const match = text.match(/из\\s*(\\d+)/i);
                    return match ? parseInt(match[1]) : 0;
                }
            ''')
            if total_pages > 1:
                print(f"⚠️ Не удалось найти ссылки, но по тексту страниц: {total_pages}. Попробуем сгенерировать URL.")
                # Генерируем ссылки, используя текущий URL как шаблон (но без параметра p)
                # Это рискованно, но как запасной вариант
                base = page.url.split('?')[0]
                qs = page.url.split('?')[1] if '?' in page.url else ''
                # Удаляем p из qs
                import urllib.parse
                params = urllib.parse.parse_qs(qs)
                params.pop('p', None)
                for p_num in range(2, total_pages+1):
                    params['p'] = [str(p_num)]
                    new_qs = urllib.parse.urlencode(params, doseq=True)
                    new_url = f"{base}?{new_qs}"
                    unique_urls.append(new_url)
            else:
                print("ℹ️ Пагинация не найдена – вероятно, только одна страница.")
                await browser.close()
                with open("avito_all_pages.json", "w", encoding="utf-8") as f:
                    json.dump(all_results, f, ensure_ascii=False, indent=2)
                print(f"🎉 Готово! Собрано {len(all_results)} объявлений с 1 страницы.")
                return

        # Удаляем первую страницу, если она есть в списке
        first_url = page.url
        if unique_urls and unique_urls[0] == first_url:
            unique_urls.pop(0)
        # Также удаляем p=1
        unique_urls = [url for url in unique_urls if 'p=1' not in url]

        # Проходим по остальным страницам
        for idx, url in enumerate(unique_urls, start=2):
            print(f"\n--- Страница {idx} --- {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            if not await wait_and_resolve_captcha(page):
                print("⏭️ Пропускаем страницу из-за капчи.")
                continue

            items = await collect_page_data(page)
            print(f"✅ Найдено {len(items)} объявлений на странице {idx}")
            all_results.extend(items)

            await asyncio.sleep(random.uniform(3, 6))

        await browser.close()

        with open("avito_all_pages.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        print(f"\n🎉 Готово! Собрано {len(all_results)} объявлений с {len(unique_urls)+1} страниц.")
        print("📁 Файл: avito_all_pages.json")

if __name__ == "__main__":
    asyncio.run(main())
