import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// Глобальные переменные
let scene, camera, renderer, controls;
let earth, atmosphere;
let animationFrameId;
let isDisposed = false;
let scrollY = 0;
let targetRotationY = 0;

// Инициализация основных компонентов
function init() {
    // Создаем сцену
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0B0B1E);

    // Настраиваем камеру
    camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);
    camera.position.z = 15;

    // Создаем рендерер
    renderer = new THREE.WebGLRenderer({ 
        antialias: true,
        alpha: true,
        powerPreference: "high-performance"
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    document.body.appendChild(renderer.domElement);

    // Настраиваем контролы
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxDistance = 50;
    controls.minDistance = 8;
    controls.rotateSpeed = 0.5;
    controls.zoomSpeed = 0.8;
    controls.autoRotate = false;
    controls.autoRotateSpeed = 0.5;
    controls.enabled = window.innerWidth > 768; // Отключаем контролы на мобильных

    // Добавляем освещение
    const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xffffff, 1.5);
    sunLight.position.set(10, 6, 10);
    sunLight.castShadow = true;
    scene.add(sunLight);

    // Создаем звезды
    createStars();
    
    // Создаем Землю
    createEarth();

    // Добавляем обработчики событий
    window.addEventListener('resize', onWindowResize);
    window.addEventListener('scroll', onScroll);
    window.addEventListener('beforeunload', dispose);
}

// Создание звезд
function createStars() {
    const starCount = 10000;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(starCount * 3);
    const colors = new Float32Array(starCount * 3);
    const sizes = new Float32Array(starCount);
    
    for (let i = 0; i < starCount; i++) {
        const i3 = i * 3;
        const radius = 1000;
        const theta = 2 * Math.PI * Math.random();
        const phi = Math.acos(2 * Math.random() - 1);
        
        positions[i3] = radius * Math.sin(phi) * Math.cos(theta);
        positions[i3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
        positions[i3 + 2] = radius * Math.cos(phi);
        
        colors[i3] = colors[i3 + 1] = colors[i3 + 2] = 1;
        sizes[i] = Math.random() * 2;
    }
    
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
    
    const material = new THREE.PointsMaterial({
        size: 2,
        sizeAttenuation: true,
        color: 0xffffff,
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending
    });
    
    const stars = new THREE.Points(geometry, material);
    scene.add(stars);
}

// Создание Земли
function createEarth() {
    const textureLoader = new THREE.TextureLoader();
    
    // Загружаем текстуры
    Promise.all([
        textureLoader.loadAsync('textures/earth_day.jpg'),
        textureLoader.loadAsync('textures/earth_night.jpg')
    ]).then(([dayTexture, nightTexture]) => {
        const geometry = new THREE.SphereGeometry(5, 64, 64);
        const material = new THREE.MeshPhongMaterial({
            map: dayTexture,
            bumpScale: 0.05,
            specular: new THREE.Color(0x333333),
            shininess: 25
        });
        
        earth = new THREE.Mesh(geometry, material);
        scene.add(earth);
        
        // Создаем атмосферу
        const atmosphereGeometry = new THREE.SphereGeometry(5.1, 64, 64);
        const atmosphereMaterial = new THREE.ShaderMaterial({
            transparent: true,
            side: THREE.BackSide,
            uniforms: {
                glowColor: { value: new THREE.Color(0x4A90E2) },
                viewVector: { value: camera.position },
                time: { value: 0 }
            },
            vertexShader: `
                uniform vec3 viewVector;
                varying float intensity;
                void main() {
                    vec3 vNormal = normalize(normalMatrix * normal);
                    vec3 vNormel = normalize(normalMatrix * viewVector);
                    intensity = pow(0.6 - dot(vNormal, vNormel), 2.0);
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `,
            fragmentShader: `
                uniform vec3 glowColor;
                uniform float time;
                varying float intensity;
                void main() {
                    vec3 glow = glowColor * intensity;
                    float pulse = 1.0 + sin(time * 2.0) * 0.1;
                    gl_FragColor = vec4(glow, intensity * pulse);
                }
            `
        });
        
        atmosphere = new THREE.Mesh(atmosphereGeometry, atmosphereMaterial);
        scene.add(atmosphere);
        
    }).catch(error => {
        console.error('Ошибка при загрузке текстур:', error);
        document.getElementById('error').textContent = 'Ошибка при загрузке текстур: ' + error.message;
    });
}

// Обработчик скролла
function onScroll() {
    scrollY = window.scrollY;
    const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
    const scrollProgress = scrollY / maxScroll;
    
    // Увеличиваем чувствительность вращения
    targetRotationY = scrollProgress * Math.PI * 8; // Четыре полных оборота
    
    // Плавное изменение позиции камеры
    if (earth) {
        camera.position.z = 15 - scrollProgress * 5; // Увеличиваем эффект приближения
        camera.lookAt(scene.position);
    }
}

// Обработчик изменения размера окна
function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    
    // Обновляем контролы для мобильных устройств
    controls.enabled = window.innerWidth > 768;
}

// Функция очистки ресурсов
function dispose() {
    isDisposed = true;
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
    }
    
    scene.traverse(object => {
        if (object.geometry) {
            object.geometry.dispose();
        }
        if (object.material) {
            if (Array.isArray(object.material)) {
                object.material.forEach(material => material.dispose());
            } else {
                object.material.dispose();
            }
        }
    });
    
    renderer.dispose();
    controls.dispose();
}

// Функция анимации
function animate(time) {
    if (isDisposed) return;
    
    animationFrameId = requestAnimationFrame(animate);
    
    if (earth) {
        // Плавное вращение к целевой позиции
        earth.rotation.y += (targetRotationY - earth.rotation.y) * 0.05;
    }
    
    if (atmosphere) {
        atmosphere.rotation.y = earth ? earth.rotation.y : 0;
        atmosphere.material.uniforms.time.value = time * 0.001;
    }
    
    controls.update();
    renderer.render(scene, camera);
}

// Инициализация и запуск
init();
animate(); 