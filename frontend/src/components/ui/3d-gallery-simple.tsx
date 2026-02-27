import type React from 'react';
import { useRef, useMemo, useCallback, useState, useEffect } from 'react';
import * as THREE from 'three';

type ImageItem = string | { src: string; alt?: string };

interface InfiniteGalleryProps {
	images: ImageItem[];
	speed?: number;
	visibleCount?: number;
	className?: string;
	style?: React.CSSProperties;
}

const DEFAULT_DEPTH_RANGE = 50;
const MAX_HORIZONTAL_OFFSET = 8;
const MAX_VERTICAL_OFFSET = 8;

export default function InfiniteGallery({
	images,
	speed = 1.2,
	visibleCount = 12,
	className = 'h-96 w-full',
	style,
}: InfiniteGalleryProps) {
	const containerRef = useRef<HTMLDivElement>(null);
	const sceneRef = useRef<THREE.Scene | null>(null);
	const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
	const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
	const planesRef = useRef<THREE.Mesh[]>([]);
	const scrollVelocityRef = useRef(0);
	const autoPlayRef = useRef(true);
	const lastInteractionRef = useRef(Date.now());
	const [loadingProgress, setLoadingProgress] = useState(0);

	const normalizedImages = useMemo(
		() =>
			images.map((img) =>
				typeof img === 'string' ? { src: img, alt: '' } : img
			),
		[images]
	);

	useEffect(() => {
		if (!containerRef.current) return;

		// Initialize Three.js scene
		const scene = new THREE.Scene();
		scene.background = new THREE.Color(0x000000);
		sceneRef.current = scene;

		const camera = new THREE.PerspectiveCamera(
			55,
			containerRef.current.clientWidth / containerRef.current.clientHeight,
			0.1,
			1000
		);
		camera.position.z = 0;
		cameraRef.current = camera;

		const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
		renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
		renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
		renderer.domElement.style.display = 'block';
		renderer.domElement.style.margin = '0';
		renderer.domElement.style.padding = '0';
		containerRef.current.appendChild(renderer.domElement);
		rendererRef.current = renderer;

		// Load textures
		const textureLoader = new THREE.TextureLoader();
		const textures: THREE.Texture[] = [];
		let loadedCount = 0;

		normalizedImages.forEach((img, idx) => {
			textureLoader.load(
				img.src,
				(texture) => {
					textures[idx] = texture;
					loadedCount++;
					setLoadingProgress((loadedCount / normalizedImages.length) * 100);
				},
				undefined,
				() => {
					loadedCount++;
					setLoadingProgress((loadedCount / normalizedImages.length) * 100);
				}
			);
		});

		// Wait for textures to load, then create planes
		const checkTexturesInterval = setInterval(() => {
			if (loadedCount === normalizedImages.length && textures.length > 0) {
				clearInterval(checkTexturesInterval);
				createPlanes();
			}
		}, 100);

		function createPlanes() {
			const depthRange = DEFAULT_DEPTH_RANGE;
			const spatialPositions: { x: number; y: number }[] = [];

			// Generate spatial positions
			for (let i = 0; i < visibleCount; i++) {
				const horizontalAngle = (i * 2.618) % (Math.PI * 2);
				const verticalAngle = (i * 1.618 + Math.PI / 3) % (Math.PI * 2);
				const horizontalRadius = (i % 3) * 1.2;
				const verticalRadius = ((i + 1) % 4) * 0.8;

				const x =
					(Math.sin(horizontalAngle) * horizontalRadius * MAX_HORIZONTAL_OFFSET) / 3;
				const y =
					(Math.cos(verticalAngle) * verticalRadius * MAX_VERTICAL_OFFSET) / 4;

				spatialPositions.push({ x, y });
			}

			// Create planes
			for (let i = 0; i < visibleCount; i++) {
				const textureIndex = i % textures.length;
				const texture = textures[textureIndex];

				if (!texture) continue;

				const geometry = new THREE.PlaneGeometry(1, 1, 32, 32);
				const material = new THREE.MeshBasicMaterial({
					map: texture,
					side: THREE.DoubleSide,
				});

				const mesh = new THREE.Mesh(geometry, material);
				const z = ((depthRange / visibleCount) * i) % depthRange;
				const pos = spatialPositions[i];

				mesh.position.set(pos.x, pos.y, z - depthRange / 2);

				// Set scale based on aspect ratio
				const aspect = texture.source.data
					? (texture.source.data as any).width / (texture.source.data as any).height
					: 1;
				const scaleX = aspect > 1 ? 2 * aspect : 2;
				const scaleY = aspect > 1 ? 2 : 2 / aspect;
				mesh.scale.set(scaleX, scaleY, 1);

				scene.add(mesh);
				planesRef.current.push(mesh);
			}
		}

		// Handle wheel scroll
		const handleWheel = (e: WheelEvent) => {
			e.preventDefault();
			scrollVelocityRef.current += e.deltaY * 0.01 * speed;
			autoPlayRef.current = false;
			lastInteractionRef.current = Date.now();
		};

		// Handle keyboard
		const handleKeyDown = (e: KeyboardEvent) => {
			if (['ArrowUp', 'ArrowLeft', 'ArrowDown', 'ArrowRight'].includes(e.key)) {
				const delta = ['ArrowDown', 'ArrowRight'].includes(e.key) ? 2 : -2;
				scrollVelocityRef.current += delta * speed;
				autoPlayRef.current = false;
				lastInteractionRef.current = Date.now();
			}
		};

		renderer.domElement.addEventListener('wheel', handleWheel, { passive: false });
		document.addEventListener('keydown', handleKeyDown);

		// Auto-play timer
		const autoPlayInterval = setInterval(() => {
			if (Date.now() - lastInteractionRef.current > 3000) {
				autoPlayRef.current = true;
			}
		}, 1000);

		// Animation loop
		const clock = new THREE.Clock();
		let animationId: number;

		const animate = () => {
			animationId = requestAnimationFrame(animate);
			const delta = clock.getDelta();

			// Update velocity
			if (autoPlayRef.current) {
				scrollVelocityRef.current += 0.3 * delta;
			}
			scrollVelocityRef.current *= 0.95;

			// Update plane positions
			const depthRange = DEFAULT_DEPTH_RANGE;
			const halfRange = depthRange / 2;

			planesRef.current.forEach((mesh) => {
				let z = mesh.position.z + halfRange;
				z += scrollVelocityRef.current * delta * 10;

				// Wrap around
				z = ((z % depthRange) + depthRange) % depthRange;
				mesh.position.z = z - halfRange;

				// Fade effect based on depth
				const normalizedZ = (z / depthRange + 0.5) % 1;
				let opacity = 1;

				if (normalizedZ < 0.15) {
					opacity = normalizedZ / 0.15;
				} else if (normalizedZ > 0.85) {
					opacity = (1 - normalizedZ) / 0.15;
				}

				if (mesh.material instanceof THREE.MeshBasicMaterial) {
					mesh.material.opacity = opacity;
					mesh.material.transparent = true;
				}
			});

			renderer.render(scene, camera);
		};

		animate();

		// Handle resize
		const handleResize = () => {
			if (!containerRef.current) return;

			const width = containerRef.current.clientWidth;
			const height = containerRef.current.clientHeight;

			camera.aspect = width / height;
			camera.updateProjectionMatrix();
			renderer.setSize(width, height);
		};

		window.addEventListener('resize', handleResize);

		// Cleanup
		return () => {
			clearInterval(checkTexturesInterval);
			clearInterval(autoPlayInterval);
			cancelAnimationFrame(animationId);
			window.removeEventListener('resize', handleResize);
			renderer.domElement.removeEventListener('wheel', handleWheel);
			document.removeEventListener('keydown', handleKeyDown);

			if (containerRef.current && renderer.domElement.parentNode === containerRef.current) {
				containerRef.current.removeChild(renderer.domElement);
			}

			renderer.dispose();
		};
	}, [normalizedImages]);

	if (loadingProgress < 100 && loadingProgress > 0) {
		return (
			<div 
				className={className} 
				style={{
					...style,
					margin: 0,
					padding: 0,
					overflow: 'hidden',
					border: 'none',
				}}
				ref={containerRef}
			>
				<div className="flex items-center justify-center h-full bg-black">
					<div className="text-center">
						<div className="w-12 h-12 bg-gray-700 rounded-full animate-spin mx-auto mb-4" />
						<p className="text-gray-400">Loading gallery... {Math.round(loadingProgress)}%</p>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div 
			className={className} 
			style={{
				...style,
				margin: 0,
				padding: 0,
				overflow: 'hidden',
				border: 'none',
			}}
			ref={containerRef}
		/>
	);
}
