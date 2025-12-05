# Многопоточный сервер парсинга
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import queue
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import sys
import argparse

class ThreadedParserHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Кастомное логирование"""
        print(f"[{self.client_address[0]}] {format % args}")
    
    def do_GET(self):
        """Обработка GET запросов"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            response = ("Многопоточный сервер парсинга Dental-First\n\n"
                       "Используйте:\n"
                       "POST /parse - запуск парсинга\n"
                       f"\nПорт: {self.server.server_port}")
            self.wfile.write(response.encode('utf-8'))
        
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps({
                'status': 'running',
                'server': 'threaded',
                'port': self.server.server_port,
                'endpoints': {
                    'POST /parse': 'Запуск парсинга каталога'
                }
            })
            self.wfile.write(response.encode('utf-8'))
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Обработка POST запросов"""
        if self.path == '/parse':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                # Запускаем парсинг в отдельном потоке
                thread = threading.Thread(
                    target=self.parse_in_background,
                    args=(data,)
                )
                thread.daemon = True
                thread.start()
                
                self.send_response(202)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                response = json.dumps({
                    'status': 'processing',
                    'message': 'Парсинг запущен в фоновом режиме',
                    'check_file': 'threaded_results.json'
                })
                self.wfile.write(response.encode('utf-8'))
                
            except json.JSONDecodeError:
                self.send_error(400, "Неверный JSON")
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_response(404)
            self.end_headers()
    
    def fetch_page(self, url):
        """Синхронное получение страницы"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            response = requests.get(url, headers=headers, timeout=30)
            return response.text if response.status_code == 200 else None
        except Exception as e:
            print(f"Ошибка получения {url}: {e}")
            return None
    
    def parse_product_card(self, soup, product_div):
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
    
    def parse_page(self, page_url):
        """Парсинг одной страницы"""
        html = self.fetch_page(page_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        product_cards = soup.find_all('div', class_='set-card block')
        
        for card in product_cards:
            product_data = self.parse_product_card(soup, card)
            if product_data:
                products.append(product_data)
        
        return products
    
    def parse_page_worker(self, page_queue, results_queue):
        """Рабочая функция для потока"""
        while True:
            try:
                page_url = page_queue.get_nowait()
                products = self.parse_page(page_url)
                results_queue.put(products)
                page_queue.task_done()
            except queue.Empty:
                break
            except Exception as e:
                print(f"Ошибка в потоке: {e}")
                page_queue.task_done()
    
    def parse_in_background(self, data):
        """Фоновая обработка парсинга"""
        try:
            start_time = time.time()
            
            url = data.get('url', 'https://dental-first.ru/catalog')
            start_page = data.get('start_page', 1)
            end_page = data.get('end_page', 3)
            num_threads = min(data.get('threads', 5), 10)  # Максимум 10 потоков
            
            print(f"Запуск многопоточного парсинга: {url}")
            print(f"Страницы: {start_page}-{end_page}")
            print(f"Потоков: {num_threads}")
            
            # Создаем очередь страниц
            page_queue = queue.Queue()
            for page_num in range(start_page, end_page + 1):
                if page_num == 1:
                    page_url = url
                else:
                    page_url = f"{url}?PAGEN_1={page_num}"
                page_queue.put(page_url)
            
            # Создаем очередь для результатов
            results_queue = queue.Queue()
            
            # Запускаем потоки
            threads = []
            for _ in range(min(num_threads, page_queue.qsize())):
                thread = threading.Thread(
                    target=self.parse_page_worker,
                    args=(page_queue, results_queue)
                )
                thread.daemon = True
                thread.start()
                threads.append(thread)
            
            # Ждем завершения всех страниц
            page_queue.join()
            
            # Собираем результаты
            all_products = []
            while not results_queue.empty():
                products = results_queue.get()
                all_products.extend(products)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Считаем общую стоимость
            total_price = sum(p['price'] for p in all_products)
            
            # Сохраняем результаты
            result_data = {
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'pages_parsed': f"{start_page}-{end_page}",
                'threads_used': num_threads,
                'total_products': len(all_products),
                'total_price': total_price,
                'execution_time': round(execution_time, 2),
                'products': all_products[:100]  # Первые 100 товаров
            }
            
            with open('threaded_results.json', 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            print(f"Многопоточный парсинг завершен:")
            print(f"  Товаров: {len(all_products)}")
            print(f"  Время: {execution_time:.2f} сек")
            print(f"  Сумма: {total_price:,} руб".replace(',', ' '))
            print(f"  Потоков использовано: {num_threads}")
            
        except Exception as e:
            print(f"Ошибка при парсинге: {e}")
            
            with open('threaded_results.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e),
                    'status': 'error'
                }, f, ensure_ascii=False, indent=2)

def run_threaded_server(port=8081, host='localhost'):
    """Запуск многопоточного сервера"""
    server = HTTPServer((host, port), ThreadedParserHandler)
    
    print("="*60)
    print("МНОГОПОТОЧНЫЙ СЕРВЕР ЗАПУЩЕН")
    print("="*60)
    print(f"Адрес: http://{host}:{port}")
    print(f"Парсинг: POST http://{host}:{port}/parse")
    print("="*60)
    print("\nПример запроса:")
    print('curl -X POST http://localhost:8081/parse \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"url":"https://dental-first.ru/catalog","start_page":1,"end_page":2,"threads":3}\'')
    print("="*60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nСервер остановлен пользователем")
    except Exception as e:
        print(f"\nОшибка сервера: {e}")

def main():
    """Точка входа"""
    parser = argparse.ArgumentParser(description='Многопоточный сервер парсинга')
    parser.add_argument('--port', type=int, default=8081, help='Порт сервера')
    parser.add_argument('--host', default='localhost', help='Хост сервера')
    
    args = parser.parse_args()
    
    try:
        run_threaded_server(port=args.port, host=args.host)
    except Exception as e:
        print(f"Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()