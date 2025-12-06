import os
from pathlib import Path

# Конфигурация серверов
HOST = '127.0.0.1'
PORT_ASYNC = 8888
PORT_THREAD = 8889
BUFFER_SIZE = 4096
MAX_CONNECTIONS = 1000

# Тестовая директория
TEST_DIR = Path("test_files")
TEST_DIR.mkdir(exist_ok=True)

# Генерация тестовых файлов
def create_test_files(num_files=50, lines_per_file=100):
    """Создание тестовых файлов"""
    for i in range(num_files):
        file_path = TEST_DIR / f"file_{i}.txt"
        with open(file_path, 'w', encoding='utf-8') as f:
            for j in range(lines_per_file):
                f.write(f"Line {j} in file {i}\n")
    print(f" Создано {num_files} тестовых файлов")

if not list(TEST_DIR.glob("*.txt")):
    create_test_files()