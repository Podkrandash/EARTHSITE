#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import mimetypes
import hashlib

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('integrity_check.log')
    ]
)
logger = logging.getLogger(__name__)

class IntegrityChecker:
    """Класс для проверки целостности проекта"""
    
    def __init__(self):
        self.required_files = {
            'main.js': {'mime': 'application/javascript', 'required': True},
            'index.html': {'mime': 'text/html', 'required': True},
            'server.py': {'mime': 'text/x-python', 'required': True},
            'README.md': {'mime': 'text/markdown', 'required': True},
            'textures/earth_day.jpg': {'mime': 'image/jpeg', 'required': True},
            'textures/earth_night.jpg': {'mime': 'image/jpeg', 'required': True},
            'textures/favicon.png': {'mime': 'image/png', 'required': True}
        }
        self.errors = []
        self.warnings = []

    def check_file_exists(self, filepath: str) -> bool:
        """Проверка существования файла"""
        if not os.path.exists(filepath):
            self.errors.append(f"Файл не найден: {filepath}")
            return False
        return True

    def check_file_permissions(self, filepath: str) -> bool:
        """Проверка прав доступа к файлу"""
        try:
            if not os.access(filepath, os.R_OK):
                self.errors.append(f"Нет прав на чтение: {filepath}")
                return False
            return True
        except Exception as e:
            self.errors.append(f"Ошибка проверки прав доступа {filepath}: {str(e)}")
        return False

    def check_file_mime(self, filepath: str, expected_mime: str) -> bool:
        """Проверка MIME-типа файла"""
        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type != expected_mime:
            self.warnings.append(f"Неверный MIME-тип для {filepath}: ожидался {expected_mime}, получен {mime_type}")
            return False
        return True

    def check_file_size(self, filepath: str) -> bool:
        """Проверка размера файла"""
        try:
            size = os.path.getsize(filepath)
            if size == 0:
                self.errors.append(f"Файл пуст: {filepath}")
                return False
            if size > 10 * 1024 * 1024:  # 10MB
                self.warnings.append(f"Файл слишком большой: {filepath} ({size / 1024 / 1024:.2f} MB)")
            return True
        except Exception as e:
            self.errors.append(f"Ошибка проверки размера {filepath}: {str(e)}")
            return False

    def check_image_dimensions(self, filepath: str) -> bool:
        """Проверка размеров изображения"""
        try:
            from PIL import Image
            with Image.open(filepath) as img:
                width, height = img.size
                if width < 256 or height < 256:
                    self.warnings.append(f"Изображение слишком маленькое: {filepath} ({width}x{height})")
                return True
        except ImportError:
            self.warnings.append("PIL не установлен, пропуск проверки размеров изображений")
            return True
        except Exception as e:
            self.errors.append(f"Ошибка проверки изображения {filepath}: {str(e)}")
            return False

    def check_js_syntax(self, filepath: str) -> bool:
        """Проверка синтаксиса JavaScript"""
    try:
        import esprima
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            esprima.parseModule(content)
            return True
        except ImportError:
            self.warnings.append("esprima не установлен, пропуск проверки синтаксиса JavaScript")
            return True
        except Exception as e:
            self.errors.append(f"Ошибка синтаксиса в {filepath}: {str(e)}")
            return False

    def check_html_syntax(self, filepath: str) -> bool:
        """Проверка синтаксиса HTML"""
        try:
            from bs4 import BeautifulSoup
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            BeautifulSoup(content, 'html.parser')
            return True
        except ImportError:
            self.warnings.append("beautifulsoup4 не установлен, пропуск проверки синтаксиса HTML")
            return True
        except Exception as e:
            self.errors.append(f"Ошибка синтаксиса в {filepath}: {str(e)}")
            return False

    def calculate_file_hash(self, filepath: str) -> str:
        """Вычисление хеша файла"""
        try:
            sha256_hash = hashlib.sha256()
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.errors.append(f"Ошибка вычисления хеша {filepath}: {str(e)}")
            return ""

    def check_all(self) -> bool:
        """Проверка всех аспектов целостности проекта"""
        logger.info("Начало проверки целостности проекта...")
        
        # Проверяем все требуемые файлы
        for filepath, info in self.required_files.items():
            if not self.check_file_exists(filepath):
                if info['required']:
                    continue
            else:
                self.check_file_permissions(filepath)
                self.check_file_mime(filepath, info['mime'])
                self.check_file_size(filepath)
                
                # Дополнительные проверки в зависимости от типа файла
                if info['mime'] == 'application/javascript':
                    self.check_js_syntax(filepath)
                elif info['mime'] == 'text/html':
                    self.check_html_syntax(filepath)
                elif info['mime'].startswith('image/'):
                    self.check_image_dimensions(filepath)
                
                # Вычисляем хеш файла
                file_hash = self.calculate_file_hash(filepath)
                if file_hash:
                    logger.info(f"Хеш файла {filepath}: {file_hash}")

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
            logger.info("✅ Проверка успешно завершена, ошибок не найдено")
            return True
            
        return len(self.errors) == 0

def main():
    """Основная функция"""
    try:
        checker = IntegrityChecker()
        success = checker.check_all()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 