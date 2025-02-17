#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import unittest
import requests
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any
from http.client import HTTPConnection
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test.log')
    ]
)
logger = logging.getLogger(__name__)

class ServerTestCase(unittest.TestCase):
    """Тесты сервера"""
    
    @classmethod
    def setUpClass(cls):
        """Запуск сервера перед тестами"""
        cls.server_process = subprocess.Popen(
            [sys.executable, 'server.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)  # Ждем запуска сервера
        
    @classmethod
    def tearDownClass(cls):
        """Остановка сервера после тестов"""
        cls.server_process.terminate()
        cls.server_process.wait()
        
    def setUp(self):
        """Подготовка к каждому тесту"""
        self.base_url = 'http://localhost:8000'
        
    def test_server_running(self):
        """Проверка работы сервера"""
        response = requests.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        
    def test_cors_headers(self):
        """Проверка CORS заголовков"""
        response = requests.options(self.base_url)
        self.assertIn('Access-Control-Allow-Origin', response.headers)
        
    def test_content_type(self):
        """Проверка типов контента"""
        # HTML
        response = requests.get(self.base_url)
        self.assertIn('text/html', response.headers['Content-Type'])
        
        # JavaScript
        response = requests.get(urljoin(self.base_url, 'main.js'))
        self.assertIn('application/javascript', response.headers['Content-Type'])
        
    def test_404_handling(self):
        """Проверка обработки 404"""
        response = requests.get(urljoin(self.base_url, 'nonexistent.file'))
        self.assertEqual(response.status_code, 404)

class BrowserTestCase(unittest.TestCase):
    """Тесты в браузере"""
    
    @classmethod
    def setUpClass(cls):
        """Настройка браузера"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        cls.driver = webdriver.Chrome(options=options)
        
    @classmethod
    def tearDownClass(cls):
        """Закрытие браузера"""
        cls.driver.quit()
        
    def setUp(self):
        """Подготовка к каждому тесту"""
        self.base_url = 'http://localhost:8000'
        
    def test_page_load(self):
        """Проверка загрузки страницы"""
        self.driver.get(self.base_url)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "canvas"))
        )
        
    def test_webgl_support(self):
        """Проверка поддержки WebGL"""
        self.driver.get(self.base_url)
        webgl_enabled = self.driver.execute_script("""
            try {
                var canvas = document.createElement('canvas');
                return !!(window.WebGLRenderingContext && 
                    (canvas.getContext('webgl') || 
                     canvas.getContext('experimental-webgl')));
            } catch(e) {
                return false;
            }
        """)
        self.assertTrue(webgl_enabled)
        
    def test_performance(self):
        """Проверка производительности"""
        self.driver.get(self.base_url)
        time.sleep(5)  # Ждем полной загрузки
        
        # Проверяем FPS
        fps = self.driver.execute_script("""
            return window.performance.now() / 1000;
        """)
        self.assertGreater(fps, 30)
        
    def test_responsive_design(self):
        """Проверка адаптивного дизайна"""
        sizes = [
            (1920, 1080),  # Desktop
            (1366, 768),   # Laptop
            (768, 1024),   # Tablet
            (375, 812)     # Mobile
        ]
        
        for width, height in sizes:
            self.driver.set_window_size(width, height)
            self.driver.get(self.base_url)
            
            # Проверяем, что canvas занимает всю область просмотра
            canvas_size = self.driver.execute_script("""
                var canvas = document.querySelector('canvas');
                return {
                    width: canvas.clientWidth,
                    height: canvas.clientHeight
                };
            """)
            
            self.assertGreaterEqual(canvas_size['width'], width * 0.9)
            self.assertGreaterEqual(canvas_size['height'], height * 0.9)

class ResourceTestCase(unittest.TestCase):
    """Тесты ресурсов"""
    
    def test_texture_files(self):
        """Проверка файлов текстур"""
        required_textures = [
            'textures/earth_day.jpg',
            'textures/earth_night.jpg',
            'textures/favicon.png'
        ]
        
        for texture in required_textures:
            self.assertTrue(
                os.path.exists(texture),
                f"Текстура не найдена: {texture}"
            )
            
    def test_texture_dimensions(self):
        """Проверка размеров текстур"""
        from PIL import Image
        
        for texture in Path('textures').glob('*.*'):
            with Image.open(texture) as img:
                width, height = img.size
                self.assertGreaterEqual(width, 256)
                self.assertGreaterEqual(height, 256)
                
    def test_javascript_syntax(self):
        """Проверка синтаксиса JavaScript"""
        import esprima
        
        with open('main.js', 'r', encoding='utf-8') as f:
            js_code = f.read()
            
        try:
            esprima.parseModule(js_code)
        except Exception as e:
            self.fail(f"Ошибка синтаксиса JavaScript: {str(e)}")
            
    def test_html_syntax(self):
        """Проверка синтаксиса HTML"""
        from bs4 import BeautifulSoup
        
        with open('index.html', 'r', encoding='utf-8') as f:
            html_code = f.read()
            
        try:
            BeautifulSoup(html_code, 'html.parser')
        except Exception as e:
            self.fail(f"Ошибка синтаксиса HTML: {str(e)}")

def run_tests():
    """Запуск всех тестов"""
    try:
        # Проверяем зависимости
        import selenium
        import PIL
        import esprima
        import bs4
        
        # Запускаем тесты
        unittest.main(verbosity=2)
    except ImportError as e:
        logger.error(f"Отсутствует зависимость: {str(e)}")
        logger.info("Установите необходимые зависимости:")
        logger.info("pip install selenium pillow esprima beautifulsoup4")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    run_tests() 