#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import shutil
import logging
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('deploy.log')
    ]
)
logger = logging.getLogger(__name__)

class Deployer:
    """Класс для развертывания проекта"""
    
    def __init__(self, args):
        self.args = args
        self.dist_dir = Path('dist')
        self.deploy_dir = Path(args.deploy_dir) if args.deploy_dir else Path('deploy')
        self.backup_dir = Path('backups')
        self.errors = []
        self.warnings = []

    def check_requirements(self) -> bool:
        """Проверка требований перед развертыванием"""
        try:
            # Проверяем наличие собранного проекта
            if not self.dist_dir.exists():
                self.errors.append("Директория dist не найдена. Сначала выполните сборку проекта")
                return False
                
            # Проверяем наличие всех необходимых файлов
            required_files = [
                'dist/index.html',
                'dist/bundle.min.js',
                'dist/server.py'
            ]
            
            for file in required_files:
                if not Path(file).exists():
                    self.errors.append(f"Файл не найден: {file}")
                    return False
                    
            return True
        except Exception as e:
            self.errors.append(f"Ошибка проверки требований: {str(e)}")
            return False

    def create_backup(self) -> bool:
        """Создание резервной копии"""
        try:
            if self.deploy_dir.exists():
                # Создаем директорию для бэкапов
                self.backup_dir.mkdir(exist_ok=True)
                
                # Создаем имя бэкапа с текущей датой
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                backup_path = self.backup_dir / backup_name
                
                # Копируем текущую версию в бэкап
                shutil.copytree(self.deploy_dir, backup_path)
                logger.info(f"Создана резервная копия: {backup_path}")
                
                # Удаляем старые бэкапы (оставляем только 5 последних)
                backups = sorted(self.backup_dir.glob('backup_*'))
                for backup in backups[:-5]:
                    shutil.rmtree(backup)
                    logger.info(f"Удален старый бэкап: {backup}")
                    
            return True
        except Exception as e:
            self.errors.append(f"Ошибка создания резервной копии: {str(e)}")
            return False

    def deploy_files(self) -> bool:
        """Развертывание файлов"""
        try:
            # Очищаем директорию развертывания
            if self.deploy_dir.exists():
                shutil.rmtree(self.deploy_dir)
            
            # Копируем файлы из dist
            shutil.copytree(self.dist_dir, self.deploy_dir)
            logger.info(f"Файлы скопированы в: {self.deploy_dir}")
            
            # Устанавливаем права доступа
            for root, dirs, files in os.walk(self.deploy_dir):
                for dir in dirs:
                    os.chmod(os.path.join(root, dir), 0o755)
                for file in files:
                    os.chmod(os.path.join(root, file), 0o644)
                    
            return True
        except Exception as e:
            self.errors.append(f"Ошибка развертывания файлов: {str(e)}")
            return False

    def update_server_config(self) -> bool:
        """Обновление конфигурации сервера"""
        try:
            server_file = self.deploy_dir / 'server.py'
            
            # Читаем текущий файл
            with open(server_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Обновляем порт, если указан
            if self.args.port:
                content = content.replace(
                    'PORT = 8000',
                    f'PORT = {self.args.port}'
                )
                
            # Обновляем хост, если указан
            if self.args.host:
                content = content.replace(
                    "HOST = ''",
                    f"HOST = '{self.args.host}'"
                )
                
            # Сохраняем изменения
            with open(server_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return True
        except Exception as e:
            self.errors.append(f"Ошибка обновления конфигурации сервера: {str(e)}")
            return False

    def create_service_file(self) -> bool:
        """Создание systemd сервиса"""
        try:
            if self.args.create_service:
                service_content = f"""[Unit]
Description=Earth Telegram Mini App
After=network.target

[Service]
Type=simple
User={os.getenv('USER')}
WorkingDirectory={self.deploy_dir.absolute()}
ExecStart={sys.executable} server.py
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
                
                service_file = Path('/etc/systemd/system/earth-app.service')
                
                # Записываем файл сервиса
                with open(service_file, 'w') as f:
                    f.write(service_content)
                    
                # Устанавливаем права
                os.chmod(service_file, 0o644)
                
                # Перезагружаем systemd
                subprocess.run(['systemctl', 'daemon-reload'])
                
                logger.info("Сервис systemd создан: earth-app.service")
                logger.info("Для управления используйте команды:")
                logger.info("systemctl start earth-app")
                logger.info("systemctl enable earth-app")
                
            return True
        except Exception as e:
            self.errors.append(f"Ошибка создания systemd сервиса: {str(e)}")
            return False

    def deploy_all(self) -> bool:
        """Полное развертывание"""
        logger.info("Начало развертывания...")
        
        # Проверяем требования
        if not self.check_requirements():
            return False
            
        # Создаем резервную копию
        if not self.create_backup():
            return False
            
        # Развертываем файлы
        if not self.deploy_files():
            return False
            
        # Обновляем конфигурацию
        if not self.update_server_config():
            return False
            
        # Создаем сервис
        if not self.create_service_file():
            return False
        
        # Выводим результаты
        if self.errors:
            logger.error("Найдены критические ошибки:")
            for error in self.errors:
                logger.error(f"❌ {error}")
                
        if self.warnings:
            logger.warning("Найдены предупреждения:")
            for warning in self.warnings:
                logger.warning(f"⚠️ {warning}")
                
        if not self.errors and not self.warnings:
            logger.info("✅ Развертывание успешно завершено")
            logger.info(f"\nПриложение развернуто в: {self.deploy_dir}")
            
            if not self.args.create_service:
                logger.info("\nДля запуска выполните:")
                logger.info(f"cd {self.deploy_dir}")
                logger.info("python server.py")
                
            return True
            
        return len(self.errors) == 0

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='Развертывание Earth Telegram Mini App')
    
    parser.add_argument(
        '--deploy-dir',
        help='Директория для развертывания'
    )
    parser.add_argument(
        '--port',
        type=int,
        help='Порт для сервера'
    )
    parser.add_argument(
        '--host',
        help='Хост для сервера'
    )
    parser.add_argument(
        '--create-service',
        action='store_true',
        help='Создать systemd сервис'
    )
    
    args = parser.parse_args()
    
    try:
        deployer = Deployer(args)
        success = deployer.deploy_all()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 