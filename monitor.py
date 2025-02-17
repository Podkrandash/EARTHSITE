#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import psutil
import logging
import requests
import argparse
import platform
import threading
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from collections import deque

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('monitor.log')
    ]
)
logger = logging.getLogger(__name__)

class SystemMonitor:
    """Мониторинг системных ресурсов"""
    
    def __init__(self):
        self.cpu_history = deque(maxlen=60)  # История загрузки CPU за последнюю минуту
        self.memory_history = deque(maxlen=60)  # История использования памяти
        self.disk_history = deque(maxlen=60)  # История использования диска
        
    def get_cpu_usage(self) -> float:
        """Получение загрузки CPU"""
        return psutil.cpu_percent(interval=1)
        
    def get_memory_usage(self) -> Dict[str, float]:
        """Получение использования памяти"""
        memory = psutil.virtual_memory()
        return {
            'total': memory.total / (1024 * 1024 * 1024),  # GB
            'used': memory.used / (1024 * 1024 * 1024),    # GB
            'percent': memory.percent
        }
        
    def get_disk_usage(self) -> Dict[str, float]:
        """Получение использования диска"""
        disk = psutil.disk_usage('/')
        return {
            'total': disk.total / (1024 * 1024 * 1024),  # GB
            'used': disk.used / (1024 * 1024 * 1024),    # GB
            'percent': disk.percent
        }
        
    def update_history(self):
        """Обновление истории метрик"""
        self.cpu_history.append(self.get_cpu_usage())
        self.memory_history.append(self.get_memory_usage()['percent'])
        self.disk_history.append(self.get_disk_usage()['percent'])
        
    def get_system_info(self) -> Dict[str, Any]:
        """Получение информации о системе"""
        return {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total / (1024 * 1024 * 1024)
        }

class ApplicationMonitor:
    """Мониторинг приложения"""
    
    def __init__(self, url: str = 'http://localhost:8000'):
        self.url = url
        self.response_times = deque(maxlen=60)  # История времени отклика
        self.errors = deque(maxlen=100)  # История ошибок
        
    def check_health(self) -> Dict[str, Any]:
        """Проверка работоспособности приложения"""
        try:
            start_time = time.time()
            response = requests.get(self.url)
            response_time = time.time() - start_time
            
            self.response_times.append(response_time)
            
            return {
                'status': response.status_code,
                'response_time': response_time,
                'is_alive': response.status_code == 200
            }
        except Exception as e:
            self.errors.append({
                'time': datetime.now().isoformat(),
                'error': str(e)
            })
            return {
                'status': 0,
                'response_time': 0,
                'is_alive': False,
                'error': str(e)
            }
            
    def get_average_response_time(self) -> float:
        """Получение среднего времени отклика"""
        if not self.response_times:
            return 0
        return sum(self.response_times) / len(self.response_times)
        
    def get_error_rate(self) -> float:
        """Получение процента ошибок"""
        if not self.errors:
            return 0
        return (len(self.errors) / 100) * 100  # За последние 100 запросов

class ProcessMonitor:
    """Мониторинг процесса"""
    
    def __init__(self, process_name: str = 'python'):
        self.process_name = process_name
        self.processes = []
        
    def find_processes(self) -> List[psutil.Process]:
        """Поиск процессов приложения"""
        self.processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if self.process_name in proc.info['name'].lower():
                    if any('server.py' in cmd.lower() for cmd in proc.info['cmdline'] if cmd):
                        self.processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return self.processes
        
    def get_process_info(self, process: psutil.Process) -> Dict[str, Any]:
        """Получение информации о процессе"""
        try:
            memory_info = process.memory_info()
            return {
                'pid': process.pid,
                'cpu_percent': process.cpu_percent(),
                'memory_rss': memory_info.rss / (1024 * 1024),  # MB
                'memory_vms': memory_info.vms / (1024 * 1024),  # MB
                'threads': process.num_threads(),
                'connections': len(process.connections()),
                'open_files': len(process.open_files())
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {}

class Monitor:
    """Основной класс мониторинга"""
    
    def __init__(self, args):
        self.args = args
        self.system_monitor = SystemMonitor()
        self.app_monitor = ApplicationMonitor(args.url)
        self.process_monitor = ProcessMonitor()
        self.stats_file = Path('monitor_stats.json')
        self.is_running = False
        
    def save_stats(self, stats: Dict[str, Any]):
        """Сохранение статистики"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения статистики: {str(e)}")
            
    def format_stats(self, stats: Dict[str, Any]) -> str:
        """Форматирование статистики для вывода"""
        output = []
        
        # Статус приложения
        status = '🟢' if stats['application']['is_alive'] else '🔴'
        output.append(f"\nСтатус приложения: {status}")
        
        # Системные ресурсы
        output.append("\nСистемные ресурсы:")
        output.append(f"CPU: {stats['system']['cpu_percent']}%")
        output.append(f"Память: {stats['system']['memory_percent']}%")
        output.append(f"Диск: {stats['system']['disk_percent']}%")
        
        # Информация о процессе
        if stats['process']:
            output.append("\nПроцесс:")
            output.append(f"PID: {stats['process']['pid']}")
            output.append(f"CPU: {stats['process']['cpu_percent']}%")
            output.append(f"Память: {stats['process']['memory_rss']:.1f} MB")
            output.append(f"Потоки: {stats['process']['threads']}")
            
        # Производительность
        output.append("\nПроизводительность:")
        output.append(f"Среднее время отклика: {stats['application']['avg_response_time']*1000:.1f} мс")
        output.append(f"Процент ошибок: {stats['application']['error_rate']:.1f}%")
        
        return '\n'.join(output)
        
    def collect_stats(self) -> Dict[str, Any]:
        """Сбор статистики"""
        # Обновляем историю системных метрик
        self.system_monitor.update_history()
        
        # Проверяем работоспособность приложения
        health = self.app_monitor.check_health()
        
        # Ищем процессы приложения
        processes = self.process_monitor.find_processes()
        process_info = {}
        if processes:
            process_info = self.process_monitor.get_process_info(processes[0])
        
        # Собираем статистику
        stats = {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_percent': self.system_monitor.get_cpu_usage(),
                'memory_percent': self.system_monitor.get_memory_usage()['percent'],
                'disk_percent': self.system_monitor.get_disk_usage()['percent'],
                'cpu_history': list(self.system_monitor.cpu_history),
                'memory_history': list(self.system_monitor.memory_history),
                'disk_history': list(self.system_monitor.disk_history)
            },
            'application': {
                'is_alive': health['is_alive'],
                'status_code': health['status'],
                'response_time': health['response_time'],
                'avg_response_time': self.app_monitor.get_average_response_time(),
                'error_rate': self.app_monitor.get_error_rate(),
                'recent_errors': list(self.app_monitor.errors)
            },
            'process': process_info
        }
        
        return stats
        
    def monitor(self):
        """Основной цикл мониторинга"""
        self.is_running = True
        
        try:
            while self.is_running:
                # Собираем статистику
                stats = self.collect_stats()
                
                # Сохраняем статистику
                self.save_stats(stats)
                
                # Выводим статистику
                if not self.args.quiet:
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(self.format_stats(stats))
                    
                # Проверяем критические значения
                if stats['system']['cpu_percent'] > 90:
                    logger.warning("Высокая загрузка CPU!")
                    
                if stats['system']['memory_percent'] > 90:
                    logger.warning("Высокое использование памяти!")
                    
                if not stats['application']['is_alive']:
                    logger.error("Приложение не отвечает!")
                    
                time.sleep(self.args.interval)
                
        except KeyboardInterrupt:
            logger.info("Мониторинг остановлен")
        finally:
            self.is_running = False

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='Мониторинг Earth Telegram Mini App')
    
    parser.add_argument(
        '--url',
        default='http://localhost:8000',
        help='URL приложения'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Интервал проверки в секундах'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Не выводить статистику в консоль'
    )
    
    args = parser.parse_args()
    
    try:
        monitor = Monitor(args)
        monitor.monitor()
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 