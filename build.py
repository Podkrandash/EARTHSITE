#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import subprocess
import logging
import json
from pathlib import Path
from typing import List, Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('build.log')
    ]
)
logger = logging.getLogger(__name__)

class ProjectBuilder:
    """Сборщик проекта"""
    
    def __init__(self):
        self.dist_dir = Path('dist')
        self.src_dir = Path('.')
        self.errors = []
        self.warnings = []

    def clean_dist(self) -> bool:
        """Очистка директории dist"""
        try:
            if self.dist_dir.exists():
                shutil.rmtree(self.dist_dir)
            self.dist_dir.mkdir(parents=True)
            return True
        except Exception as e:
            self.errors.append(f"Ошибка очистки директории dist: {str(e)}")
            return False

    def minify_js(self, input_file: str, output_file: str) -> bool:
        """Минификация JavaScript файла"""
        try:
            result = subprocess.run(
                ['npx', 'esbuild', 
                 input_file,
                 '--bundle',
                 '--minify',
                 '--sourcemap',
                 f'--outfile={output_file}'],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"JavaScript минифицирован: {output_file}")
            return True
        except subprocess.CalledProcessError as e:
            self.errors.append(f"Ошибка минификации JavaScript: {str(e)}")
            logger.error(e.stderr)
            return False
        except FileNotFoundError:
            self.errors.append("esbuild не найден. Установите его через npm")
            return False

    def optimize_images(self) -> bool:
        """Оптимизация изображений"""
        try:
            from PIL import Image
            
            textures_dir = self.src_dir / 'textures'
            dist_textures_dir = self.dist_dir / 'textures'
            dist_textures_dir.mkdir(exist_ok=True)
            
            for img_file in textures_dir.glob('*'):
                if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    with Image.open(img_file) as img:
                        # Конвертируем PNG в WebP для лучшего сжатия
                        if img_file.suffix.lower() == '.png':
                            output_path = dist_textures_dir / f"{img_file.stem}.webp"
                            img.save(output_path, 'WEBP', quality=85, method=6)
                        else:
                            output_path = dist_textures_dir / img_file.name
                            img.save(output_path, quality=85, optimize=True)
                        
                        logger.info(f"Изображение оптимизировано: {output_path}")
            
            return True
        except ImportError:
            self.warnings.append("PIL не установлен, пропуск оптимизации изображений")
            return True
        except Exception as e:
            self.errors.append(f"Ошибка оптимизации изображений: {str(e)}")
            return False

    def minify_html(self, input_file: str, output_file: str) -> bool:
        """Минификация HTML файла"""
        try:
            from bs4 import BeautifulSoup
            
            with open(input_file, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            # Обновляем пути к ресурсам
            for script in soup.find_all('script', src=True):
                if script['src'].endswith('main.js'):
                    script['src'] = 'bundle.min.js'
                    
            for img in soup.find_all('img', src=True):
                src = img['src']
                if src.endswith('.png'):
                    img['src'] = src.replace('.png', '.webp')
            
            # Минифицируем HTML
            minified_html = str(soup).replace('    ', '').replace('\n', '')
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(minified_html)
                
            logger.info(f"HTML минифицирован: {output_file}")
            return True
        except ImportError:
            self.warnings.append("beautifulsoup4 не установлен, пропуск минификации HTML")
            return True
        except Exception as e:
            self.errors.append(f"Ошибка минификации HTML: {str(e)}")
            return False

    def copy_static_files(self) -> bool:
        """Копирование статических файлов"""
        try:
            # Копируем README.md
            shutil.copy2(self.src_dir / 'README.md', self.dist_dir / 'README.md')
            
            # Копируем server.py
            shutil.copy2(self.src_dir / 'server.py', self.dist_dir / 'server.py')
            
            logger.info("Статические файлы скопированы")
            return True
        except Exception as e:
            self.errors.append(f"Ошибка копирования статических файлов: {str(e)}")
            return False

    def create_manifest(self) -> bool:
        """Создание манифеста сборки"""
        try:
            manifest = {
                "version": "1.0.0",
                "buildTime": str(datetime.datetime.now()),
                "files": []
            }
            
            for file in self.dist_dir.rglob('*'):
                if file.is_file():
                    manifest["files"].append({
                        "path": str(file.relative_to(self.dist_dir)),
                        "size": file.stat().st_size,
                        "hash": self.calculate_file_hash(file)
                    })
            
            manifest_file = self.dist_dir / 'manifest.json'
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
                
            logger.info("Манифест сборки создан")
            return True
        except Exception as e:
            self.errors.append(f"Ошибка создания манифеста: {str(e)}")
            return False

    def calculate_file_hash(self, file_path: Path) -> str:
        """Вычисление хеша файла"""
        import hashlib
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
                
        return sha256_hash.hexdigest()

    def build_all(self) -> bool:
        """Полная сборка проекта"""
        logger.info("Начало сборки проекта...")
        
        # Очищаем директорию сборки
        if not self.clean_dist():
            return False
        
        # Минифицируем JavaScript
        if not self.minify_js('main.js', 'dist/bundle.min.js'):
            return False
        
        # Оптимизируем изображения
        if not self.optimize_images():
            return False
        
        # Минифицируем HTML
        if not self.minify_html('index.html', 'dist/index.html'):
            return False
        
        # Копируем статические файлы
        if not self.copy_static_files():
            return False
        
        # Создаем манифест
        if not self.create_manifest():
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
            logger.info("✅ Сборка успешно завершена")
            logger.info(f"\nРезультаты сборки находятся в директории: {self.dist_dir}")
            return True
            
        return len(self.errors) == 0

def main():
    """Основная функция"""
    try:
        builder = ProjectBuilder()
        success = builder.build_all()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 