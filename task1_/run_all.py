# Главный скрипт запуска всех компонентов
import subprocess
import time
import sys
import os
import threading
import signal
import requests
import json
import socket
from pathlib import Path

class AllInOneSystem:
    def __init__(self):
        self.processes = []
        self.async_port = 8080
        self.threaded_port = 8081
        self.running = True
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        print("\nПолучен сигнал завершения...")
        self.stop_all()
        sys.exit(0)
    
    def check_port(self, port):
        """Проверка свободен ли порт"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return True
            except:
                return False
    
    def install_dependencies(self):
        """Установка зависимостей"""
        print("Проверка зависимостей...")
        
        deps = ['aiohttp', 'beautifulsoup4', 'requests', 'psutil', 'lxml']
        
        try:
            import importlib
            for dep in deps:
                try:
                    importlib.import_module(dep.replace('-', '_'))
                    print(f"   {dep} - OK")
                except ImportError:
                    print(f"   Устанавливаю {dep}...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", dep, "--quiet"])
                    print(f"   {dep} установлен")
            
            print("Все зависимости установлены\n")
            return True
        except Exception as e:
            print(f"Ошибка установки: {e}")
            return False
    
    def start_async_server(self):
        """Запуск асинхронного сервера"""
        print(f"Запуск асинхронного сервера на порту {self.async_port}...")
        
        # Проверяем порт
        if not self.check_port(self.async_port):
            print(f"Порт {self.async_port} занят, попробую 8082...")
            self.async_port = 8082
            if not self.check_port(self.async_port):
                print("Не удалось найти свободный порт для асинхронного сервера")
                return False
        
        # Запускаем сервер в отдельном процессе
        cmd = [sys.executable, "async_server.py", "--port", str(self.async_port)]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.processes.append(("Асинхронный сервер", process))
            
            # Читаем вывод в отдельном потоке
            threading.Thread(
                target=self.read_output, 
                args=(process, "Асинхронный"),
                daemon=True
            ).start()
            
            # Даем время на запуск
            time.sleep(3)
            
            # Проверяем запуск
            try:
                response = requests.get(f"http://localhost:{self.async_port}", timeout=2)
                if response.status_code == 200:
                    print(f"Асинхронный сервер запущен: http://localhost:{self.async_port}")
                    return True
            except:
                # Сервер может быть еще запускается
                print(f"Асинхронный сервер запускается...")
                time.sleep(2)
                return True
                
        except Exception as e:
            print(f"Ошибка запуска асинхронного сервера: {e}")
        
        return False
    
    def start_threaded_server(self):
        """Запуск многопоточного сервера"""
        print(f"Запуск многопоточного сервера на порту {self.threaded_port}...")
        
        # Проверяем порт
        if not self.check_port(self.threaded_port):
            print(f"Порт {self.threaded_port} занят, попробую 8083...")
            self.threaded_port = 8083
            if not self.check_port(self.threaded_port):
                print("Не удалось найти свободный порт для многопоточного сервера")
                return False
        
        # Запускаем сервер в отдельном процессе
        cmd = [sys.executable, "threaded_server.py", "--port", str(self.threaded_port)]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.processes.append(("Многопоточный сервер", process))
            
            # Читаем вывод в отдельном потоке
            threading.Thread(
                target=self.read_output, 
                args=(process, "Многопоточный"),
                daemon=True
            ).start()
            
            # Даем время на запуск
            time.sleep(3)
            
            # Проверяем запуск
            try:
                response = requests.get(f"http://localhost:{self.threaded_port}", timeout=2)
                if response.status_code == 200:
                    print(f"Многопоточный сервер запущен: http://localhost:{self.threaded_port}")
                    return True
            except:
                print(f"Многопоточный сервер запускается...")
                time.sleep(2)
                return True
                
        except Exception as e:
            print(f"Ошибка запуска многопоточного сервера: {e}")
        
        return False
    
    def read_output(self, process, name):
        """Чтение вывода процесса"""
        try:
            while self.running:
                output = process.stdout.readline()
                if output:
                    print(f"[{name}] {output.strip()}")
                time.sleep(0.1)
        except:
            pass
    
    def run_test(self, pages=2):
        """Запуск тестового парсинга"""
        print(f"\nЗапуск тестового парсинга ({pages} страниц)...")
        
        # Даем серверам время на полный запуск
        time.sleep(5)
        
        results = {}
        
        # Тест асинхронного сервера
        print(f"\n1. Тестирование асинхронного сервера...")
        async_result = self.test_async_server(pages)
        if async_result:
            results['async'] = async_result
        
        # Ждем между тестами
        time.sleep(3)
        
        # Тест многопоточного сервера
        print(f"\n2. Тестирование многопоточного сервера...")
        threaded_result = self.test_threaded_server(pages)
        if threaded_result:
            results['threaded'] = threaded_result
        
        # Сравниваем результаты
        if results.get('async') and results.get('threaded'):
            self.compare_results(results['async'], results['threaded'])
        
        return results
    
    def test_async_server(self, pages):
        """Тестирование асинхронного сервера"""
        try:
            print(f"   Отправка запроса на парсинг {pages} страниц...")
            
            payload = {
                "url": "https://dental-first.ru/catalog",
                "start_page": 1,
                "end_page": pages
            }
            
            response = requests.post(
                f"http://localhost:{self.async_port}/parse",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   Успех: {result.get('message', '')}")
                print(f"   Время: {result.get('execution_time', 0):.2f} сек")
                
                # Читаем результаты из файла
                if os.path.exists("async_results.json"):
                    with open("async_results.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    print(f"   Товаров: {data.get('total_products', 0)}")
                    print(f"   Сумма: {data.get('total_price', 0):,} руб".replace(',', ' '))
                
                return result
            else:
                print(f"   Ошибка: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   Ошибка: {e}")
        
        return None
    
    def test_threaded_server(self, pages):
        """Тестирование многопоточного сервера"""
        try:
            print(f"   Отправка запроса на парсинг {pages} страниц...")
            
            payload = {
                "url": "https://dental-first.ru/catalog",
                "start_page": 1,
                "end_page": pages,
                "threads": 3
            }
            
            response = requests.post(
                f"http://localhost:{self.threaded_port}/parse",
                json=payload,
                timeout=5  # Короткий таймаут, т.к. сервер сразу возвращает 202
            )
            
            if response.status_code == 202:
                print("   Парсинг запущен в фоновом режиме...")
                print("   Ожидаю 15 секунд...")
                
                # Ждем завершения
                for i in range(15):
                    if os.path.exists("threaded_results.json"):
                        time.sleep(1)  # Даем время на запись
                        try:
                            with open("threaded_results.json", "r", encoding="utf-8") as f:
                                data = json.load(f)
                            
                            if 'error' not in data:
                                print("   Завершено:")
                                print(f"      Товаров: {data.get('total_products', 0)}")
                                print(f"      Сумма: {data.get('total_price', 0):,} руб".replace(',', ' '))
                                print(f"      Потоков: {data.get('threads_used', 0)}")
                                print(f"      Время: {data.get('execution_time', 0):.2f} сек")
                                return data
                        except:
                            pass
                    time.sleep(1)
                
                print("   Время ожидания истекло")
                
            else:
                print(f"   Неожиданный ответ: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("   Таймаут (ожидаемо, сервер возвращает 202)")
            print("   Проверяю файлы результатов...")
            time.sleep(10)
            
            if os.path.exists("threaded_results.json"):
                try:
                    with open("threaded_results.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if 'error' not in data:
                        print("   Результаты получены:")
                        print(f"      Товаров: {data.get('total_products', 0)}")
                        print(f"      Сумма: {data.get('total_price', 0):,} руб".replace(',', ' '))
                        return data
                except:
                    print("   Не удалось прочитать результаты")
            else:
                print("   Файл результатов не найден")
                
        except Exception as e:
            print(f"   Ошибка: {e}")
        
        return None
    
    def compare_results(self, async_result, threaded_result):
        """Сравнение результатов"""
        print("\n" + "="*60)
        print("СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
        print("="*60)
        
        # Читаем данные из файлов
        async_data = {}
        threaded_data = {}
        
        if os.path.exists("async_results.json"):
            try:
                with open("async_results.json", "r", encoding="utf-8") as f:
                    async_data = json.load(f)
            except:
                pass
        
        if os.path.exists("threaded_results.json"):
            try:
                with open("threaded_results.json", "r", encoding="utf-8") as f:
                    threaded_data = json.load(f)
            except:
                pass
        
        async_products = async_data.get('total_products', 0)
        threaded_products = threaded_data.get('total_products', 0)
        async_price = async_data.get('total_price', 0)
        threaded_price = threaded_data.get('total_price', 0)
        async_time = async_data.get('execution_time', 0)
        threaded_time = threaded_data.get('execution_time', 0)
        
        print(f"\n{'Параметр':<25} {'Асинхронный':<15} {'Многопоточный':<15} {'Разница':<10}")
        print("-"*65)
        
        # Количество товаров
        prod_diff = threaded_products - async_products
        print(f"{'Товаров найдено':<25} {async_products:<15} {threaded_products:<15} {prod_diff:+d}")
        
        # Сумма
        price_diff = threaded_price - async_price
        print(f"{'Сумма (руб)':<25} {async_price:<15,} {threaded_price:<15,} {price_diff:+,}".replace(',', ' '))
        
        # Время
        if async_time and threaded_time:
            time_diff = threaded_time - async_time
            print(f"{'Время (сек)':<25} {async_time:<15.2f} {threaded_time:<15.2f} {time_diff:+.2f}")
        
        # Потоки
        threads_used = threaded_data.get('threads_used', 0)
        print(f"{'Потоков':<25} {'-':<15} {threads_used:<15} {'-'}")
        
        # Сохраняем отчет
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'ports': {
                'async': self.async_port,
                'threaded': self.threaded_port
            },
            'async_server': {
                'products': async_products,
                'total_price': async_price,
                'execution_time': async_time
            },
            'threaded_server': {
                'products': threaded_products,
                'total_price': threaded_price,
                'execution_time': threaded_time,
                'threads_used': threads_used
            },
            'comparison': {
                'products_difference': prod_diff,
                'price_difference': price_diff,
                'time_difference': time_diff if async_time and threaded_time else None
            }
        }
        
        with open('comparison_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\nПолный отчет сохранен в comparison_report.json")
    
    def show_menu(self):
        """Показать меню"""
        print("\n" + "="*60)
        print("ГЛАВНОЕ МЕНЮ УПРАВЛЕНИЯ")
        print("="*60)
        print("1. ЗАПУСТИТЬ ВСЕ (серверы + тест)")
        print("2. Только запустить серверы")
        print("3. Выполнить тест (серверы должны быть запущены)")
        print("4. Показать результаты")
        print("5. Экспорт в CSV")
        print("6. Остановить все и выйти")
        print("="*60)
        
        try:
            choice = input("Выберите действие (1-6): ").strip()
            return choice
        except KeyboardInterrupt:
            return '6'
        except:
            return '6'
    
    def show_results(self):
        """Показать результаты"""
        print("\nРЕЗУЛЬТАТЫ:")
        
        for name, filename in [("Асинхронный", "async_results.json"), 
                               ("Многопоточный", "threaded_results.json")]:
            if os.path.exists(filename):
                try:
                    with open(filename, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    print(f"\n{name}:")
                    print(f"   Товаров: {data.get('total_products', 0)}")
                    print(f"   Сумма: {data.get('total_price', 0):,} руб".replace(',', ' '))
                    print(f"   Время: {data.get('execution_time', 0):.2f} сек")
                    
                    if 'threads_used' in data:
                        print(f"   Потоков: {data.get('threads_used')}")
                    
                    # Примеры товаров
                    products = data.get('products', [])[:3]
                    if products:
                        print("   Примеры:")
                        for i, p in enumerate(products, 1):
                            name_short = p.get('name', '')[:50]
                            if len(p.get('name', '')) > 50:
                                name_short += '...'
                            print(f"      {i}. {p.get('price', 0):,} руб - {name_short}".replace(',', ' '))
                    
                except Exception as e:
                    print(f"   Ошибка чтения {filename}: {e}")
            else:
                print(f"\n{name}: файл не найден")
    
    def export_to_csv(self):
        """Экспорт в CSV"""
        print("\nЭКСПОРТ В CSV:")
        
        try:
            import csv
        except:
            print("Не удалось импортировать модуль csv")
            return
        
        for name, filename in [("async", "async_results.json"), 
                               ("threaded", "threaded_results.json")]:
            if os.path.exists(filename):
                try:
                    with open(filename, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    csv_filename = f"{name}_results.csv"
                    products = data.get('products', [])
                    
                    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        writer.writerow(['Название', 'Цена (руб)', 'Артикул', 'Время парсинга'])
                        
                        for product in products:
                            writer.writerow([
                                product.get('name', ''),
                                product.get('price', 0),
                                product.get('label', ''),
                                data.get('timestamp', '')
                            ])
                    
                    print(f"{name}: {len(products)} товаров -> {csv_filename}")
                    
                except Exception as e:
                    print(f"Ошибка экспорта {filename}: {e}")
            else:
                print(f"{filename} не найден")
    
    def stop_all(self):
        """Остановить все процессы"""
        print("\nОстановка системы...")
        
        for name, process in self.processes:
            try:
                print(f"   Останавливаю {name}...")
                process.terminate()
                process.wait(timeout=2)
                print(f"   {name} остановлен")
            except:
                try:
                    process.kill()
                    print(f"   {name} принудительно завершен")
                except:
                    print(f"   Не удалось остановить {name}")
        
        self.processes.clear()
        print("Все процессы остановлены")
    
    def run(self):
        """Основной цикл"""
        print("="*60)
        print("СИСТЕМА ПАРСИНГА DENTAL-FIRST.RU")
        print("="*60)
        
        # Устанавливаем зависимости
        self.install_dependencies()
        
        servers_started = False
        
        while self.running:
            choice = self.show_menu()
            
            if choice == '1':
                print("\n" + "="*60)
                print("ПОЛНЫЙ ЗАПУСК СИСТЕМЫ")
                print("="*60)
                
                # Запускаем серверы
                async_ok = self.start_async_server()
                threaded_ok = self.start_threaded_server()
                servers_started = async_ok or threaded_ok
                
                if servers_started:
                    # Запускаем тест
                    self.run_test(pages=2)
                else:
                    print("Не удалось запустить серверы")
            
            elif choice == '2':
                print("\nЗАПУСК СЕРВЕРОВ")
                async_ok = self.start_async_server()
                threaded_ok = self.start_threaded_server()
                servers_started = async_ok or threaded_ok
                
                if servers_started:
                    print(f"\nСерверы запущены:")
                    print(f"   Асинхронный: http://localhost:{self.async_port}")
                    print(f"   Многопоточный: http://localhost:{self.threaded_port}")
                else:
                    print("Не удалось запустить серверы")
            
            elif choice == '3':
                if not servers_started:
                    print("\nСерверы не запущены!")
                    print("Сначала запустите серверы (пункт 1 или 2)")
                else:
                    try:
                        pages = int(input("Сколько страниц парсить? [2]: ").strip() or "2")
                        self.run_test(pages=pages)
                    except:
                        self.run_test(pages=2)
            
            elif choice == '4':
                self.show_results()
            
            elif choice == '5':
                self.export_to_csv()
            
            elif choice == '6':
                print("\nЗавершение работы...")
                if servers_started:
                    self.stop_all()
                self.running = False
                break
            
            else:
                print("Неверный выбор")
            
            if choice != '6' and self.running:
                try:
                    input("\nНажмите Enter чтобы продолжить...")
                except KeyboardInterrupt:
                    print("\nПрервано")
                    self.running = False

def main():
    """Точка входа"""
    try:
        system = AllInOneSystem()
        system.run()
    except KeyboardInterrupt:
        print("\n\nПрограмма завершена")
    except Exception as e:
        print(f"\nОшибка: {e}")
        import traceback
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()