import socket
import asyncio
import time
import statistics
import argparse
from typing import List
import matplotlib.pyplot as plt

class PerformanceClient:
    def __init__(self, host='127.0.0.1', port_async=8888, port_thread=8889):
        self.host = host
        self.port_async = port_async
        self.port_thread = port_thread
        self.results = {
            'async': [],
            'threaded': []
        }
    
    def test_threaded_server(self, num_requests=100, command="COUNT_ALL"):
        """Тестирование многопоточного сервера"""
        latencies = []
        successes = 0
        
        print(f"\n🔧 Тестирование многопоточного сервера ({num_requests} запросов)...")
        
        for i in range(num_requests):
            try:
                start_time = time.time()
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)  # 5 секунд таймаут
                sock.connect((self.host, self.port_thread))
                
                sock.send(command.encode())
                response = sock.recv(4096).decode()
                
                latency = (time.time() - start_time) * 1000  # в мс
                latencies.append(latency)
                
                if not response.startswith("ОШИБКА"):
                    successes += 1
                
                sock.close()
                
                # Прогресс
                if (i + 1) % max(1, num_requests // 5) == 0:
                    print(f"   Выполнено: {i + 1}/{num_requests} запросов")
                
            except socket.timeout:
                print(f"   Запрос {i + 1}: Таймаут (5 секунд)")
            except ConnectionRefusedError:
                print(f"   Запрос {i + 1}: Соединение отклонено. Убедитесь, что сервер запущен на порту {self.port_thread}")
                break
            except Exception as e:
                print(f"   Запрос {i + 1} не удался: {type(e).__name__}: {e}")
        
        if not latencies:
            print(f"   ❌ Нет успешных запросов к многопоточному серверу")
            return {
                'avg_latency': 0,
                'max_latency': 0,
                'min_latency': 0,
                'success_rate': 0
            }
        
        return {
            'avg_latency': statistics.mean(latencies) if latencies else 0,
            'max_latency': max(latencies) if latencies else 0,
            'min_latency': min(latencies) if latencies else 0,
            'success_rate': (successes / num_requests) * 100 if num_requests > 0 else 0
        }
    
    async def test_async_server_single(self, command="COUNT_ALL"):
        """Одиночный запрос к асинхронному серверу"""
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port_async)
            
            start_time = time.time()
            writer.write(command.encode())
            await writer.drain()
            
            response = await asyncio.wait_for(reader.read(4096), timeout=5)
            latency = (time.time() - start_time) * 1000
            
            writer.close()
            await writer.wait_closed()
            
            return latency, True
            
        except asyncio.TimeoutError:
            return 0, False
        except ConnectionRefusedError:
            print(f"   Соединение отклонено. Убедитесь, что асинхронный сервер запущен на порту {self.port_async}")
            return 0, False
        except Exception as e:
            print(f"   Асинхронный запрос не удался: {type(e).__name__}: {e}")
            return 0, False
    
    async def test_async_server(self, num_requests=100, command="COUNT_ALL"):
        """Тестирование асинхронного сервера"""
        print(f"\n⚡ Тестирование асинхронного сервера ({num_requests} запросов)...")
        
        tasks = []
        
        for i in range(num_requests):
            task = asyncio.create_task(self.test_async_server_single(command))
            tasks.append(task)
            
            # Прогресс
            if (i + 1) % max(1, num_requests // 5) == 0:
                print(f"   Создано задач: {i + 1}/{num_requests}")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        latencies = []
        successes = 0
        
        for i, result in enumerate(results):
            if isinstance(result, tuple):
                latency, success = result
                if success and latency > 0:
                    latencies.append(latency)
                    successes += 1
        
        if not latencies:
            print(f"   ❌ Нет успешных запросов к асинхронному серверу")
            return {
                'avg_latency': 0,
                'max_latency': 0,
                'min_latency': 0,
                'success_rate': 0
            }
        
        return {
            'avg_latency': statistics.mean(latencies) if latencies else 0,
            'max_latency': max(latencies) if latencies else 0,
            'min_latency': min(latencies) if latencies else 0,
            'success_rate': (successes / num_requests) * 100 if num_requests > 0 else 0
        }
    
    def run_comparison(self, num_requests_list=[10, 50, 100, 200]):
        """Запуск сравнительного тестирования"""
        print("=" * 70)
        print("🚀 КЛИЕНТ ТЕСТИРОВАНИЯ ПРОИЗВОДИТЕЛЬНОСТИ")
        print("=" * 70)
        print(f"📡 Адрес сервера: {self.host}")
        print(f"🎯 Асинхронный сервер: порт {self.port_async}")
        print(f"🎯 Многопоточный сервер: порт {self.port_thread}")
        print("=" * 70)
        
        for num_requests in num_requests_list:
            print(f"\n📊 Тестирование с {num_requests} запросами:")
            print("-" * 50)
            
            # Тестируем многопоточный сервер
            threaded_results = self.test_threaded_server(num_requests)
            self.results['threaded'].append({
                'num_requests': num_requests,
                **threaded_results
            })
            
            print(f"  📈 Результаты многопоточного сервера:")
            print(f"     ✓ Средняя задержка: {threaded_results['avg_latency']:.2f} мс")
            print(f"     ✓ Успешных запросов: {threaded_results['success_rate']:.1f}%")
            print(f"     ✓ Макс. задержка: {threaded_results['max_latency']:.2f} мс")
            
            # Тестируем асинхронный сервер
            async_results = asyncio.run(self.test_async_server(num_requests))
            self.results['async'].append({
                'num_requests': num_requests,
                **async_results
            })
            
            print(f"  🚀 Результаты асинхронного сервера:")
            print(f"     ✓ Средняя задержка: {async_results['avg_latency']:.2f} мс")
            print(f"     ✓ Успешных запросов: {async_results['success_rate']:.1f}%")
            print(f"     ✓ Макс. задержка: {async_results['max_latency']:.2f} мс")
        
        # Сохраняем результаты только если есть данные
        if any(r['success_rate'] > 0 for r in self.results['async'] + self.results['threaded']):
            self.plot_results()
        else:
            print("\n❌ Нет успешных запросов. Проверьте, что серверы запущены.")
            print("   Запустите в другом терминале: python run_servers.py")
    
    def plot_results(self):
        """Визуализация результатов"""
        try:
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            
            # Настройка шрифта
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 1. Сравнение задержек
            ax1 = axes[0, 0]
            async_nums = [r['num_requests'] for r in self.results['async']]
            async_latencies = [r['avg_latency'] for r in self.results['async']]
            thread_nums = [r['num_requests'] for r in self.results['threaded']]
            thread_latencies = [r['avg_latency'] for r in self.results['threaded']]
            
            ax1.plot(async_nums, async_latencies, 'b-o', label='Асинхронный сервер', linewidth=2, markersize=8)
            ax1.plot(thread_nums, thread_latencies, 'r-s', label='Многопоточный сервер', linewidth=2, markersize=8)
            ax1.set_xlabel('Количество запросов', fontsize=12)
            ax1.set_ylabel('Средняя задержка (мс)', fontsize=12)
            ax1.set_title('Сравнение задержек', fontsize=14, fontweight='bold')
            ax1.legend(fontsize=11)
            ax1.grid(True, alpha=0.3)
            
            # 2. Успешные запросы
            ax2 = axes[0, 1]
            async_success = [r['success_rate'] for r in self.results['async']]
            thread_success = [r['success_rate'] for r in self.results['threaded']]
            
            x_pos = range(len(async_nums))
            ax2.bar([x-0.2 for x in x_pos], async_success, 0.4, label='Асинхронный', color='blue', alpha=0.7)
            ax2.bar([x+0.2 for x in x_pos], thread_success, 0.4, label='Многопоточный', color='red', alpha=0.7)
            ax2.set_xlabel('Количество запросов', fontsize=12)
            ax2.set_ylabel('Процент успешных запросов (%)', fontsize=12)
            ax2.set_title('Процент успешных запросов', fontsize=14, fontweight='bold')
            ax2.set_xticks(x_pos)
            ax2.set_xticklabels(async_nums)
            ax2.legend(fontsize=11)
            ax2.grid(True, alpha=0.3, axis='y')
            
            # 3. Максимальная задержка
            ax3 = axes[1, 0]
            async_max = [r['max_latency'] for r in self.results['async']]
            thread_max = [r['max_latency'] for r in self.results['threaded']]
            
            ax3.plot(async_nums, async_max, 'b--o', label='Асинхронный (макс)', linewidth=2, markersize=8)
            ax3.plot(thread_nums, thread_max, 'r--s', label='Многопоточный (макс)', linewidth=2, markersize=8)
            ax3.set_xlabel('Количество запросов', fontsize=12)
            ax3.set_ylabel('Максимальная задержка (мс)', fontsize=12)
            ax3.set_title('Максимальная задержка', fontsize=14, fontweight='bold')
            ax3.legend(fontsize=11)
            ax3.grid(True, alpha=0.3)
            
            # 4. Производительность
            ax4 = axes[1, 1]
            async_rps = []
            thread_rps = []
            
            for i in range(len(async_nums)):
                if self.results['async'][i]['avg_latency'] > 0:
                    async_rps.append(1000 / self.results['async'][i]['avg_latency'])
                else:
                    async_rps.append(0)
                
                if self.results['threaded'][i]['avg_latency'] > 0:
                    thread_rps.append(1000 / self.results['threaded'][i]['avg_latency'])
                else:
                    thread_rps.append(0)
            
            ax4.plot(async_nums, async_rps, 'g-^', label='Асинхронный RPS', linewidth=2, markersize=8)
            ax4.plot(thread_nums, thread_rps, 'm-v', label='Многопоточный RPS', linewidth=2, markersize=8)
            ax4.set_xlabel('Количество запросов', fontsize=12)
            ax4.set_ylabel('Запросов в секунду (RPS)', fontsize=12)
            ax4.set_title('Пропускная способность', fontsize=14, fontweight='bold')
            ax4.legend(fontsize=11)
            ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig('сравнение_производительности.png', dpi=150, bbox_inches='tight')
            print(f"\n✅ Графики сохранены в файл: сравнение_производительности.png")
            plt.show()
            
        except Exception as e:
            print(f"\n⚠️  Ошибка при создании графиков: {e}")
            print("   Убедитесь, что установлен matplotlib: pip install matplotlib")

def main():
    parser = argparse.ArgumentParser(description='Клиент для тестирования производительности сокет-серверов')
    parser.add_argument('--host', default='127.0.0.1', help='Адрес сервера')
    parser.add_argument('--requests', type=int, nargs='+', 
                       default=[10, 50, 100, 200], help='Количество запросов для тестирования')
    parser.add_argument('--command', default='COUNT_ALL', 
                       help='Команда (COUNT_ALL или COUNT_FILE имя_файла)')
    
    args = parser.parse_args()
    
    client = PerformanceClient(host=args.host)
    client.run_comparison(args.requests)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Тестирование прервано")
    except Exception as e:
        print(f"\n❌ Ошибка в клиенте: {e}")
        print("Проверьте, что серверы запущены: python run_servers.py")
        input("Нажмите Enter для выхода...")