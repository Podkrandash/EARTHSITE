#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import logging
from typing import List, Tuple

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('setup.log')
    ]
)
logger = logging.getLogger(__name__)

class DependencyInstaller:
    """Установщик зависимостей проекта"""
    
    def __init__(self):
        self.python_dependencies = [
            'esprima>=4.0.1',
            'beautifulsoup4>=4.9.3',
            'pillow>=8.0.0',
            'requests>=2.25.1'
        ]
        
        self.npm_dependencies = {
            'three': '^0.160.0',
            'esbuild': '^0.19.0'
        }
        
        self.errors = []
        self.warnings = []

    def check_python_version(self) -> bool:
        """Проверка версии Python"""
        required_version = (3, 7)
        current_version = sys.version_info[:2]
        
        if current_version < required_version:
            self.errors.append(
                f"Требуется Python {required_version[0]}.{required_version[1]} или выше. "
                f"Текущая версия: {current_version[0]}.{current_version[1]}"
            )
            return False
        return True

    def check_pip(self) -> bool:
        """Проверка наличия pip"""
        try:
            subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                         check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            self.errors.append("pip не установлен")
            return False

    def check_npm(self) -> bool:
        """Проверка наличия npm"""
        try:
            subprocess.run(['npm', '--version'], 
                         check=True, capture_output=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.warnings.append("npm не установлен, пропуск установки JavaScript зависимостей")
            return False

    def install_python_dependencies(self) -> bool:
        """Установка Python зависимостей"""
        try:
            for package in self.python_dependencies:
                logger.info(f"Установка {package}...")
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', package],
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            self.errors.append(f"Ошибка установки Python зависимостей: {str(e)}")
            logger.error(e.stderr)
            return False

    def create_package_json(self) -> bool:
        """Создание package.json"""
        try:
            package_json = {
                "name": "earth-telegram-app",
                "version": "1.0.0",
                "description": "3D Earth presentation for Telegram Mini App",
                "main": "main.js",
                "scripts": {
                    "build": "esbuild main.js --bundle --outfile=dist/bundle.js",
                    "serve": "python server.py"
                },
                "dependencies": self.npm_dependencies,
                "devDependencies": {}
            }
            
            with open('package.json', 'w', encoding='utf-8') as f:
                import json
                json.dump(package_json, f, indent=2)
            
            return True
        except Exception as e:
            self.errors.append(f"Ошибка создания package.json: {str(e)}")
            return False

    def install_npm_dependencies(self) -> bool:
        """Установка npm зависимостей"""
        try:
            if not os.path.exists('package.json'):
                if not self.create_package_json():
                    return False
            
            logger.info("Установка npm зависимостей...")
            result = subprocess.run(
                ['npm', 'install'],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            self.errors.append(f"Ошибка установки npm зависимостей: {str(e)}")
            logger.error(e.stderr)
            return False

    def create_virtual_environment(self) -> bool:
        """Создание виртуального окружения"""
        try:
            if not os.path.exists('venv'):
                logger.info("Создание виртуального окружения...")
                subprocess.run(
                    [sys.executable, '-m', 'venv', 'venv'],
                    check=True,
                    capture_output=True
                )
            return True
        except subprocess.CalledProcessError as e:
            self.errors.append(f"Ошибка создания виртуального окружения: {str(e)}")
            return False

    def setup_all(self) -> bool:
        """Полная настройка проекта"""
        logger.info("Начало установки зависимостей...")
        
        # Проверяем требования
        if not self.check_python_version():
            return False
            
        if not self.check_pip():
            return False
        
        # Создаем виртуальное окружение
        if not self.create_virtual_environment():
            return False
        
        # Устанавливаем Python зависимости
        if not self.install_python_dependencies():
            return False
        
        # Проверяем npm и устанавливаем JavaScript зависимости
        if self.check_npm():
            if not self.install_npm_dependencies():
                return False
        
        # Создаем необходимые директории
        os.makedirs('dist', exist_ok=True)
        os.makedirs('textures', exist_ok=True)
        
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
            logger.info("✅ Установка успешно завершена")
            logger.info("\nДля запуска проекта выполните:")
            logger.info("1. source venv/bin/activate  # Для Linux/Mac")
            logger.info("   .\\venv\\Scripts\\activate  # Для Windows")
            logger.info("2. python server.py")
            logger.info("3. Откройте http://localhost:8000 в браузере")
            return True
            
        return len(self.errors) == 0

def main():
    """Основная функция"""
    try:
        installer = DependencyInstaller()
        success = installer.setup_all()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 