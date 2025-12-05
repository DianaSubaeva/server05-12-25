# Клиент для тестирования
import requests
import json
import time
import sys

def test_async_server(port=8080, pages=2):
    """Тестирование асинхронного сервера"""
    print(f"\nТестирование асинхронного сервера (порт {port})...")
    
    try:
        # Проверяем доступность
        response = requests.get(f"http://localhost:{port}", timeout=2)
        if response.status_code != 200:
            print(f"Сервер не отвечает: HTTP {response.status_code}")
            return None
    except:
        print(f"Не удалось подключиться к серверу на порту {port}")
        return None
    
    # Отправляем запрос на парсинг
    payload = {
        "url": "https://dental-first.ru/catalog",
        "start_page": 1,
        "end_page": pages
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"http://localhost:{port}/parse",
            json=payload,
            timeout=60
        )
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print(f"Успех: {result.get('message', '')}")
            print(f"Время ответа: {end_time - start_time:.2f} сек")
            print(f"Товаров: {result.get('total_products', 0)}")
            print(f"Сумма: {result.get('total_price', 0):,} руб".replace(',', ' '))
            print(f"Время парсинга: {result.get('execution_time', 0):.2f} сек")
            return result
        else:
            print(f"Ошибка: HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("Таймаут запроса")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    return None

def test_threaded_server(port=8081, pages=2, threads=3):
    """Тестирование многопоточного сервера"""
    print(f"\nТестирование многопоточного сервера (порт {port})...")
    
    try:
        response = requests.get(f"http://localhost:{port}", timeout=2)
        if response.status_code != 200:
            print(f"Сервер не отвечает: HTTP {response.status_code}")
            return None
    except:
        print(f"Не удалось подключиться к серверу на порту {port}")
        return None
    
    # Отправляем запрос
    payload = {
        "url": "https://dental-first.ru/catalog",
        "start_page": 1,
        "end_page": pages,
        "threads": threads
    }
    
    try:
        response = requests.post(
            f"http://localhost:{port}/parse",
            json=payload,
            timeout=5  # Короткий таймаут для 202 ответа
        )
        
        if response.status_code == 202:
            result = response.json()
            print(f"Парсинг запущен в фоне")
            print(f"Результаты будут в файле: {result.get('check_file', 'threaded_results.json')}")
            
            # Ждем и проверяем файл
            print("Ожидаю 15 секунд...")
            for i in range(15):
                try:
                    with open("threaded_results.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if 'error' not in data:
                        print("Результаты получены:")
                        print(f"   Товаров: {data.get('total_products', 0)}")
                        print(f"   Сумма: {data.get('total_price', 0):,} руб".replace(',', ' '))
                        print(f"   Время: {data.get('execution_time', 0):.2f} сек")
                        print(f"   Потоков: {data.get('threads_used', 0)}")
                        return data
                except:
                    pass
                time.sleep(1)
            
            print("Время ожидания истекло")
            
        else:
            print(f"Неожиданный ответ: HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("Таймаут (ожидаемо для 202 ответа)")
        print("Проверяю файл результатов...")
        time.sleep(10)
        
        try:
            with open("threaded_results.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if 'error' not in data:
                print("Результаты в файле:")
                print(f"   Товаров: {data.get('total_products', 0)}")
                print(f"   Сумма: {data.get('total_price', 0):,} руб".replace(',', ' '))
                return data
            else:
                print(f"Ошибка в файле: {data.get('error')}")
        except:
            print("Файл результатов не найден или поврежден")
            
    except Exception as e:
        print(f"Ошибка: {e}")
    
    return None

def compare_results(async_result, threaded_result):
    """Сравнение результатов"""
    if not async_result or not threaded_result:
        return
    
    print("\n" + "="*60)
    print("СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
    print("="*60)
    
    # Читаем данные из файлов для более полной информации
    async_data = {}
    threaded_data = {}
    
    try:
        with open("async_results.json", "r", encoding="utf-8") as f:
            async_data = json.load(f)
    except:
        pass
    
    try:
        with open("threaded_results.json", "r", encoding="utf-8") as f:
            threaded_data = json.load(f)
    except:
        pass
    
    print(f"{'Параметр':<20} {'Асинхронный':<15} {'Многопоточный':<15} {'Разница':<10}")
    print("-"*60)
    
    # Количество товаров
    async_count = async_data.get('total_products', 0)
    threaded_count = threaded_data.get('total_products', 0)
    prod_diff = threaded_count - async_count
    print(f"{'Товаров':<20} {async_count:<15} {threaded_count:<15} {prod_diff:+d}")
    
    # Сумма
    async_price = async_data.get('total_price', 0)
    threaded_price = threaded_data.get('total_price', 0)
    price_diff = threaded_price - async_price
    print(f"{'Сумма (руб)':<20} {async_price:<15,} {threaded_price:<15,} {price_diff:+,}".replace(',', ' '))
    
    # Время
    async_time = async_data.get('execution_time', 0)
    threaded_time = threaded_data.get('execution_time', 0)
    if async_time and threaded_time:
        time_diff = threaded_time - async_time
        print(f"{'Время (сек)':<20} {async_time:<15.2f} {threaded_time:<15.2f} {time_diff:+.2f}")
    
    # Потоки
    threads = threaded_data.get('threads_used', 0)
    print(f"{'Потоков':<20} {'-':<15} {threads:<15} {'-'}")

def main():
    """Основная функция"""
    print("="*60)
    print("ТЕСТИРОВАНИЕ СЕРВЕРОВ ПАРСИНГА")
    print("="*60)
    
    # Парсим аргументы командной строки
    import argparse
    parser = argparse.ArgumentParser(description='Тестирование серверов парсинга')
    parser.add_argument('--async-port', type=int, default=8080, help='Порт асинхронного сервера')
    parser.add_argument('--threaded-port', type=int, default=8081, help='Порт многопоточного сервера')
    parser.add_argument('--pages', type=int, default=2, help='Количество страниц для парсинга')
    parser.add_argument('--threads', type=int, default=3, help='Количество потоков')
    
    args = parser.parse_args()
    
    # Тестируем асинхронный сервер
    async_result = test_async_server(port=args.async_port, pages=args.pages)
    
    # Ждем между тестами
    time.sleep(3)
    
    # Тестируем многопоточный сервер
    threaded_result = test_threaded_server(
        port=args.threaded_port, 
        pages=args.pages,
        threads=args.threads
    )
    
    # Сравниваем результаты
    compare_results(async_result, threaded_result)
    
    print("\nРезультаты сохранены в файлах:")
    print("   async_results.json")
    print("   threaded_results.json")

if __name__ == "__main__":
    main()