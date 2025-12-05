# Асинхронный сервер парсинга
import asyncio
import aiohttp
from aiohttp import web
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup
import re
import sys

class AsyncParserServer:
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Настройка маршрутов"""
        self.app.router.add_post('/parse', self.handle_parse)
        self.app.router.add_get('/', self.handle_root)
        self.app.router.add_get('/status', self.handle_status)
    
    async def handle_root(self, request):
        """Корневой эндпоинт"""
        return web.Response(
            text="Асинхронный сервер парсинга Dental-First\n\n"
                 "Используйте:\n"
                 "POST /parse - запуск парсинга\n"
                 "GET /status - статус сервера\n"
                 f"\nПорт: {self.port}",
            content_type='text/plain'
        )
    
    async def handle_status(self, request):
        """Статус сервера"""
        return web.json_response({
            'status': 'running',
            'server': 'async',
            'port': self.port,
            'endpoints': {
                'POST /parse': 'Запуск парсинга каталога',
                'GET /status': 'Статус сервера'
            }
        })
    
    async def fetch_page(self, session, url):
        """Получение HTML страницы"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            }
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"Ошибка {response.status} для {url}")
                    return None
        except Exception as e:
            print(f"Ошибка получения {url}: {e}")
            return None
    
    async def parse_product_card(self, soup, product_div):
        """Парсинг одной карточки товара"""
        try:
            # Название товара
            title_element = product_div.find('p', class_='set-card__title')
            if title_element:
                name_link = title_element.find('a', class_='di_b c_b')
                if name_link:
                    product_name = name_link.get_text(strip=True)
                else:
                    product_name = title_element.get_text(strip=True)
            else:
                product_name = "Без названия"
            
            # Цена товара
            price_element = product_div.find('span', class_='set-card__price')
            price = 0
            if price_element:
                price_text = price_element.get_text(strip=True)
                price_match = re.search(r'[\d\s]+(?=\s*₽)', price_text)
                if price_match:
                    price_str = price_match.group().replace(' ', '')
                    try:
                        price = int(price_str)
                    except:
                        price = 0
            
            # Артикул/метка
            label_element = product_div.find('span', class_='set-card__label')
            label = label_element.get_text(strip=True) if label_element else ""
            
            return {
                'name': product_name,
                'price': price,
                'label': label
            }
        except Exception as e:
            print(f"Ошибка парсинга карточки: {e}")
            return None
    
    async def parse_catalog_page(self, session, page_url):
        """Парсинг страницы каталога"""
        html = await self.fetch_page(session, page_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        # Находим все карточки товаров
        product_cards = soup.find_all('div', class_='set-card block')
        
        for card in product_cards:
            product_data = await self.parse_product_card(soup, card)
            if product_data:
                products.append(product_data)
        
        return products
    
    async def parse_multiple_pages(self, session, base_url, start_page, end_page):
        """Парсинг нескольких страниц"""
        all_products = []
        
        for page_num in range(start_page, end_page + 1):
            if page_num == 1:
                page_url = base_url
            else:
                page_url = f"{base_url}?PAGEN_1={page_num}"
            
            print(f"Парсинг страницы {page_num}...")
            products = await self.parse_catalog_page(session, page_url)
            all_products.extend(products)
            
            # Небольшая задержка между запросами
            await asyncio.sleep(1)
        
        return all_products
    
    async def handle_parse(self, request):
        """Обработчик запроса на парсинг"""
        try:
            # Получаем данные запроса
            data = await request.json()
            url = data.get('url', 'https://dental-first.ru/catalog')
            start_page = data.get('start_page', 1)
            end_page = data.get('end_page', 3)
            
            print(f"Запуск парсинга: {url}")
            print(f"Страницы: {start_page}-{end_page}")
            
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                all_products = await self.parse_multiple_pages(
                    session, url, start_page, end_page
                )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Считаем общую стоимость
            total_price = sum(p['price'] for p in all_products)
            
            # Сохраняем результаты
            result_data = {
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'pages_parsed': f"{start_page}-{end_page}",
                'total_products': len(all_products),
                'total_price': total_price,
                'execution_time': round(execution_time, 2),
                'products': all_products[:100]  # Первые 100 товаров
            }
            
            with open('async_results.json', 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            print(f"Парсинг завершен: {len(all_products)} товаров")
            print(f"Время: {execution_time:.2f} сек")
            print(f"Сумма: {total_price:,} руб".replace(',', ' '))
            
            return web.json_response({
                'status': 'success',
                'message': f'Парсинг завершен. Найдено {len(all_products)} товаров.',
                'total_products': len(all_products),
                'total_price': total_price,
                'execution_time': round(execution_time, 2),
                'results_file': 'async_results.json'
            })
            
        except json.JSONDecodeError:
            return web.json_response({
                'status': 'error',
                'message': 'Неверный JSON в теле запроса'
            }, status=400)
            
        except Exception as e:
            print(f"Ошибка при парсинге: {e}")
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    async def run(self):
        """Запуск сервера"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        print("="*60)
        print("АСИНХРОННЫЙ СЕРВЕР ЗАПУЩЕН")
        print("="*60)
        print(f"Адрес: http://{self.host}:{self.port}")
        print(f"Статус: http://{self.host}:{self.port}/status")
        print(f"Парсинг: POST http://{self.host}:{self.port}/parse")
        print("="*60)
        print("\nПример запроса:")
        print('curl -X POST http://localhost:8080/parse \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"url":"https://dental-first.ru/catalog","start_page":1,"end_page":2}\'')
        print("="*60)
        
        # Бесконечное ожидание
        await asyncio.Event().wait()

def main():
    """Точка входа"""
    # Парсим аргументы командной строки
    import argparse
    parser = argparse.ArgumentParser(description='Асинхронный сервер парсинга')
    parser.add_argument('--port', type=int, default=8080, help='Порт сервера')
    parser.add_argument('--host', default='localhost', help='Хост сервера')
    
    args = parser.parse_args()
    
    try:
        server = AsyncParserServer(host=args.host, port=args.port)
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\n\nСервер остановлен пользователем")
    except Exception as e:
        print(f"\nОшибка запуска сервера: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()