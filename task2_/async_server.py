import asyncio
import socket
import logging
from pathlib import Path
from config import HOST, PORT_ASYNC, BUFFER_SIZE, MAX_CONNECTIONS, TEST_DIR
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AsyncServer")

class AsyncSocketServer:
    def __init__(self, host=HOST, port=PORT_ASYNC):
        self.host = host
        self.port = port
        self.stats = {
            'requests_processed': 0,
            'start_time': time.time(),
            'memory_usage_mb': 0
        }
    
    def count_lines_in_file(self, filepath: Path) -> int:
        """Подсчет строк в файле"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except Exception as e:
            logger.error(f"Ошибка чтения {filepath}: {e}")
            return -1
    
    async def handle_client(self, reader, writer):
        """Обработка клиентского соединения"""
        client_addr = writer.get_extra_info('peername')
        logger.info(f"Новое асинхронное соединение от {client_addr}")
        
        try:
            # Читаем запрос клиента
            data = await reader.read(BUFFER_SIZE)
            request = data.decode().strip()
            
            if request == "COUNT_ALL":
                # Подсчет всех файлов в директории
                total_lines = 0
                file_count = 0
                
                for file_path in TEST_DIR.glob("*.txt"):
                    lines = self.count_lines_in_file(file_path)
                    if lines >= 0:
                        total_lines += lines
                        file_count += 1
                
                response = f"Файлы: {file_count}, Всего строк: {total_lines}"
            
            elif request.startswith("COUNT_FILE "):
                # Подсчет конкретного файла
                filename = request.split(" ", 1)[1]
                file_path = TEST_DIR / filename
                if file_path.exists():
                    lines = self.count_lines_in_file(file_path)
                    response = f"Строк в {filename}: {lines}"
                else:
                    response = f"Файл {filename} не найден"
            
            else:
                response = "Неизвестная команда. Используйте: COUNT_ALL или COUNT_FILE <имя_файла>"
            
            # Отправляем ответ
            writer.write(response.encode())
            await writer.drain()
            
            self.stats['requests_processed'] += 1
            
        except Exception as e:
            logger.error(f"Ошибка обработки клиента {client_addr}: {e}")
            response = f"ОШИБКА: {str(e)}"
            writer.write(response.encode())
            await writer.drain()
        
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"Соединение с {client_addr} закрыто")
    
    async def run(self):
        """Запуск асинхронного сервера"""
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
            limit=MAX_CONNECTIONS
        )
        
        addr = server.sockets[0].getsockname()
        logger.info(f'[АСИНХРОННЫЙ СЕРВЕР] Запущен на {addr}')
        logger.info(f'Тестовая директория: {TEST_DIR}')
        
        # Расчет примерного использования памяти
        self.stats['memory_usage_mb'] = self.estimate_memory_usage()
        logger.info(f'Примерное использование памяти: {self.stats["memory_usage_mb"]} MB')
        
        async with server:
            try:
                await server.serve_forever()
            except asyncio.CancelledError:
                logger.info("Сервер завершает работу...")
    
    def estimate_memory_usage(self):
        """Оценка использования памяти без psutil"""
        # Примерная оценка: 10 MB базово + 5 KB на подключение
        base_memory = 10  # MB
        per_connection = 5 / 1024  # 5 KB в MB
        estimated = base_memory + (MAX_CONNECTIONS * per_connection)
        return round(estimated, 2)
    
    def get_statistics(self):
        """Получение статистики производительности"""
        elapsed_time = time.time() - self.stats['start_time']
        
        stats = {
            **self.stats,
            'elapsed_time_seconds': round(elapsed_time, 2),
            'requests_per_second': round(self.stats['requests_processed'] / elapsed_time, 2) if elapsed_time > 0 else 0
        }
        
        return stats