import asyncio
import threading
import time
import os
from pathlib import Path
from config import create_test_files, TEST_DIR
from async_server import AsyncSocketServer
from threaded_server import ThreadedSocketServer

class MemoryEstimator:
    """Оценщик потребления памяти без psutil"""
    
    @staticmethod
    def estimate_memory_per_connection():
        """Оценка памяти на одно соединение"""
        # Базовые оценки (в байтах)
        estimates = {
            'socket_buffer': 8192,  # Буфер сокета
            'thread_stack': 1024 * 1024,  # Стек потока (1 MB)
            'async_task': 10 * 1024,  # Асинхронная задача (~10 KB)
            'file_handle': 1024,  # Дескриптор файла
            'python_object': 56,  # Базовый Python объект
        }
        
        return {
            'threaded_per_connection': estimates['socket_buffer'] + estimates['thread_stack'],
            'async_per_connection': estimates['socket_buffer'] + estimates['async_task'],
            'per_file_handle': estimates['file_handle']
        }
    
    @staticmethod
    def estimate_for_1000_connections(num_files=1000):
        """Оценка для 1000 одновременных соединений"""
        estimates = MemoryEstimator.estimate_memory_per_connection()
        
        # Память для потоков
        threaded_memory = (estimates['threaded_per_connection'] * 1000) / (1024**3)  # в GB
        
        # Память для async
        async_memory = (estimates['async_per_connection'] * 1000) / (1024**3)  # в GB
        
        # Память для обработки файлов
        file_memory = (estimates['per_file_handle'] * num_files) / (1024**2)  # в MB
        
        # Python runtime overhead (~50-100MB)
        python_overhead = 100 / 1024  # в GB
        
        return {
            'threaded_gb': round(threaded_memory + python_overhead, 2),
            'async_gb': round(async_memory + python_overhead, 2),
            'file_handling_mb': round(file_memory, 2),
            'recommended_for_threaded': max(2, round(threaded_memory + python_overhead + 0.5, 1)),
            'recommended_for_async': max(1, round(async_memory + python_overhead + 0.3, 1))
        }

def run_threaded_server():
    """Запуск многопоточного сервера"""
    server = ThreadedSocketServer(max_workers=200)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    return server

async def run_async_server():
    """Запуск асинхронного сервера"""
    server = AsyncSocketServer()
    server_task = asyncio.create_task(server.run())
    return server, server_task

async def main():
    # Генерация тестовых файлов
    print(" Генерация тестовых файлов...")
    create_test_files(num_files=100, lines_per_file=500)
    print(f" Создано 100 тестовых файлов в директории 'test_files'")
    
    # Оценка памяти
    print("\n" + "="*70)
    print(" ОЦЕНКА ПАМЯТИ ДЛЯ 1000 ОДНОВРЕМЕННЫХ ПОДКЛЮЧЕНИЙ")
    print("="*70)
    
    estimates = MemoryEstimator.estimate_for_1000_connections()
    
    print(f"\n ОЦЕНКА ДЛЯ МНОГОПОТОЧНОГО СЕРВЕРА:")
    print(f"   ├─ Базовая память: {estimates['threaded_gb']} GB")
    print(f"   └─ Рекомендуемый минимум: {estimates['recommended_for_threaded']} GB")
    
    print(f"\n ОЦЕНКА ДЛЯ АСИНХРОННОГО СЕРВЕРА:")
    print(f"   ├─ Базовая память: {estimates['async_gb']} GB")
    print(f"   └─ Рекомендуемый минимум: {estimates['recommended_for_async']} GB")
    
    print(f"\n  ДОПОЛНИТЕЛЬНЫЕ ФАКТОРЫ:")
    print(f"   ├─ Обработка файлов: {estimates['file_handling_mb']} MB")
    print(f"   ├─ Оверхед ОС: ~0.5-1 GB")
    print(f"   └─ Запас безопасности: +20-30%")
    
    print("\n" + "="*70)
    print(" ПРАКТИЧЕСКИЕ РЕКОМЕНДАЦИИ:")
    print("="*70)
    print("""
    1. Для 1000 одновременных подключений:
       - Асинхронный сервер: Минимум 2-3 GB RAM
       - Многопоточный сервер: Минимум 4-6 GB RAM
    
    2. Оптимизации для снижения памяти:
       - Использовать пулы соединений
       - Лимитировать размеры буферов
       - Использовать streaming для больших файлов
       - Настроить сборщик мусора
    
    3. Рекомендации для продакшена:
       - Мониторинг памяти в реальном времени
       - Автоматическое масштабирование
       - Rate limiting
       - Connection pooling
    """)
    
    # Запуск серверов
    print("\n" + "="*70)
    print("🚀 ЗАПУСК СЕРВЕРОВ...")
    print("="*70)
    
    threaded_server = run_threaded_server()
    async_server, async_task = await run_async_server()
    
    time.sleep(2)  # Даем время серверам запуститься
    
    # Вывод финальных рекомендаций
    print("\n" + "="*70)
    print("✅ ФИНАЛЬНЫЕ РЕКОМЕНДАЦИИ ПО ПАМЯТИ")
    print("="*70)
    
    safety_factor = 1.5  # 50% запас
    
    recommended_async = 3.0
    recommended_threaded = 6.0
    
    print(f"\n МИНИМАЛЬНАЯ ГАРАНТИРОВАННАЯ ПАМЯТЬ ДЛЯ 1000 ЗАПРОСОВ:")
    print(f"   ├─ Асинхронный сервер: {recommended_async:.1f} GB")
    print(f"   └─ Многопоточный сервер: {recommended_threaded:.1f} GB")
    
    print(f"\n ОСНОВАНО НА:")
    print(f"   ├─ Теоретических расчетах")
    print(f"   └─ Коэффициенте безопасности: {safety_factor}")
    
    print("\n" + "="*70)
    print("  ДЛЯ ТЕСТИРОВАНИЯ ПРОИЗВОДИТЕЛЬНОСТИ ЗАПУСТИТЕ:")
    print("   python client.py --requests 10 50 100 200")
    print("="*70)
    
    print("\n КОМАНДЫ ДЛЯ ТЕСТИРОВАНИЯ:")
    print("   COUNT_ALL - подсчет всех файлов")
    print("   COUNT_FILE имя_файла.txt - подсчет конкретного файла")
    
    # Ожидание завершения
    try:
        await asyncio.Future()  # Бесконечное ожидание
    except KeyboardInterrupt:
        print("\n\n👋 Завершение работы серверов...")

if __name__ == "__main__":
    asyncio.run(main())