import socket

def test_connection(port, server_name):
    """Простой тест соединения"""
    try:
        print(f"\n🔍 Тестирую {server_name} на порту {port}...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect(('127.0.0.1', port))
        
        # Отправляем тестовую команду
        sock.send(b'COUNT_ALL')
        
        # Получаем ответ
        response = sock.recv(4096).decode()
        print(f" {server_name} отвечает!")
        print(f"   Ответ: {response[:100]}...")
        
        sock.close()
        return True
        
    except ConnectionRefusedError:
        print(f" {server_name} не отвечает на порту {port}")
        print(f"   Запустите сервер: python run_servers.py")
        return False
    except Exception as e:
        print(f" Ошибка при тесте {server_name}: {e}")
        return False

# Проверяем оба сервера
print("=" * 50)
print("  ПРОВЕРКА СОЕДИНЕНИЯ С СЕРВЕРАМИ")
print("=" * 50)

async_ok = test_connection(8888, "Асинхронный сервер")
threaded_ok = test_connection(8889, "Многопоточный сервер")

print("\n" + "=" * 50)
if async_ok and threaded_ok:
    print(" Оба сервера работают! Можно запускать тесты.")
else:
    print("  Некоторые серверы не работают. Сначала запустите:")
    print("   python run_servers.py")
print("=" * 50)