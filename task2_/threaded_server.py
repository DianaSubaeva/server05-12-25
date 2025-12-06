import socket
import threading
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from config import HOST, PORT_THREAD, BUFFER_SIZE, MAX_CONNECTIONS, TEST_DIR
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ThreadedServer")

class ThreadedSocketServer:
    def __init__(self, host=HOST, port=PORT_THREAD, max_workers=100):
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self.stats = {
            'requests_processed': 0,
            'start_time': time.time(),
            'active_connections': 0,
            'memory_usage_mb': 0
        }
        self.stats_lock = threading.Lock()
        self.running = True
    
    def count_lines_in_file(self, filepath: Path) -> int:
        """Подсчет строк в файле"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except Exception as e:
            logger.error(f"Ошибка чтения {filepath}: {e}")
            return -1
    
    def handle_client(self, client_socket, address):
        """Обработка клиентского соединения"""
        with self.stats_lock:
            self.stats['active_connections'] += 1
        
        logger.info(f"Новое многопоточное соединение от {address}")
        
        try:
            # Получаем запрос
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                return
            
            request = data.decode().strip()
            
            if request == "COUNT_ALL":
                total_lines = 0
                file_count = 0
                
                for file_path in TEST_DIR.glob("*.txt"):
                    lines = self.count_lines_in_file(file_path)
                    if lines >= 0:
                        total_lines += lines
                        file_count += 1
                
                response = f"Файлы: {file_count}, Всего строк: {total_lines}"
            
            elif request.startswith("COUNT_FILE "):
                filename = request.split(" ", 1)[1]
                file_path = TEST_DIR / filename
                if file_path.exists():
                    lines = self.count_lines_in_file(file_path)
                    response = f"Строк в {filename}: {lines}"
                else:
                    response = f"Файл {filename} не найден"
            else:
                response = "Неизвестная команда"
            
            # Отправляем ответ
            client_socket.send(response.encode())
            
            with self.stats_lock:
                self.stats['requests_processed'] += 1
            
        except Exception as e:
            logger.error(f"Ошибка обработки клиента {address}: {e}")
        finally:
            client_socket.close()
            with self.stats_lock:
                self.stats['active_connections'] -= 1
            logger.info(f"Соединение с {address} закрыто")
    
    def run(self):
        """Запуск многопоточного сервера"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(MAX_CONNECTIONS)
        
        logger.info(f'[МНОГОПОТОЧНЫЙ СЕРВЕР] Запущен на {self.host}:{self.port}')
        
        # Расчет примерного использования памяти
        self.stats['memory_usage_mb'] = self.estimate_memory_usage()
        logger.info(f'Примерное использование памяти: {self.stats["memory_usage_mb"]} MB')
        
        # Используем ThreadPoolExecutor для управления потоками
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            try:
                while self.running:
                    client_socket, address = server_socket.accept()
                    executor.submit(self.handle_client, client_socket, address)
            except KeyboardInterrupt:
                logger.info("Завершение работы сервера...")
                self.running = False
            finally:
                server_socket.close()
    
    def estimate_memory_usage(self):
        """Оценка использования памяти без psutil"""
        # Примерная оценка: 20 MB базово + 1 MB на поток
        base_memory = 20  # MB
        per_thread = 1  # MB
        estimated = base_memory + (self.max_workers * per_thread)
        return round(estimated, 2)
    
    def get_statistics(self):
        """Получение статистики производительности"""
        with self.stats_lock:
            elapsed_time = time.time() - self.stats['start_time']
            
            stats = {
                **self.stats,
                'elapsed_time_seconds': round(elapsed_time, 2),
                'requests_per_second': round(self.stats['requests_processed'] / elapsed_time, 2) if elapsed_time > 0 else 0
            }
            
            return stats