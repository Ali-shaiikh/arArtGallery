import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/App';
import InfiniteGallery from '@/components/ui/3d-gallery-simple';

export default function Gallery() {
	const navigate = useNavigate();
	const { user } = useAuth();

	const sampleImages = [
		{ src: 'https://images.unsplash.com/photo-1741332966416-414d8a5b8887?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxmZWF0dXJlZC1waG90b3MtZmVlZHw2fHx8ZW58MHx8fHx8', alt: 'Image 1' },
		{ src: 'https://images.unsplash.com/photo-1754769440490-2eb64d715775?q=80&w=1113&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D', alt: 'Image 2' },
		{ src: 'https://images.unsplash.com/photo-1758640920659-0bb864175983?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxmZWF0dXJlZC1waG90b3MtZmVlZHwzNHx8fGVufDB8fHx8fA%3D%3D', alt: 'Image 3' },
		{ src: 'https://plus.unsplash.com/premium_photo-1758367454070-731d3cc11774?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxmZWF0dXJlZC1waG90b3MtZmVlZHw0MXx8fGVufDB8fHx8fA%3D%3D', alt: 'Image 4' },
		{ src: 'https://images.unsplash.com/photo-1746023841657-e5cd7cc90d2c?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxmZWF0dXJlZC1waG90b3MtZmVlZHw0Nnx8fGVufDB8fHx8fA%3D%3D', alt: 'Image 5' },
		{ src: 'https://images.unsplash.com/photo-1741715661559-6149723ea89a?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxmZWF0dXJlZC1waG90b3MtZmVlZHw1MHx8fGVufDB8fHx8fA%3D%3D', alt: 'Image 6' },
		{ src: 'https://images.unsplash.com/photo-1725878746053-407492aa4034?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxmZWF0dXJlZC1waG90b3MtZmVlZHw1OHx8fGVufDB8fHx8fA%3D%3D', alt: 'Image 7' },
		{ src: 'https://images.unsplash.com/photo-1752588975168-d2d7965a6d64?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxmZWF0dXJlZC1waG90b3MtZmVlZHw2M3x8fGVufDB8fHx8fA%3D%3D', alt: 'Image 8' },
	];

	return (
		<>
			<InfiniteGallery
				images={sampleImages}
				speed={1.2}
				visibleCount={12}
				className="h-screen w-full overflow-hidden"
			/>
			
			{/* Center Title Overlay */}
			<div 
				style={{
					position: 'fixed',
					top: '50%',
					left: '50%',
					transform: 'translate(-50%, -50%)',
					zIndex: 9999,
					pointerEvents: 'none',
					margin: 0,
					padding: '20px',
					backgroundColor: 'rgba(0, 0, 0, 0.3)',
					borderRadius: '8px',
					textAlign: 'center'
				}}
			>
				<h1 
					style={{ 
						fontFamily: "'Playfair Display', 'Georgia', serif",
						fontSize: '5rem',
						fontStyle: 'italic',
						fontWeight: '600',
						letterSpacing: '0.02em',
						color: '#ffffff',
						margin: '0 0 30px 0',
						padding: 0,
						textShadow: '0 4px 20px rgba(0, 0, 0, 0.8), 0 2px 10px rgba(0, 0, 0, 0.6)'
					}}
				>
					Art Gallery
				</h1>
				
				<button
					onClick={() => user ? navigate('/select-role') : navigate('/start')}
					style={{
						pointerEvents: 'auto',
						padding: '14px 40px',
						fontSize: '16px',
						fontWeight: '600',
						backgroundColor: '#ffffff',
						color: '#000000',
						border: 'none',
						borderRadius: '6px',
						cursor: 'pointer',
						transition: 'all 0.3s ease',
						boxShadow: '0 4px 15px rgba(0, 0, 0, 0.3)',
						letterSpacing: '0.5px'
					}}
					onMouseEnter={(e) => {
						e.target.style.backgroundColor = '#f0f0f0';
						e.target.style.transform = 'translateY(-2px)';
						e.target.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.4)';
					}}
					onMouseLeave={(e) => {
						e.target.style.backgroundColor = '#ffffff';
						e.target.style.transform = 'translateY(0)';
						e.target.style.boxShadow = '0 4px 15px rgba(0, 0, 0, 0.3)';
					}}
				>
					{user ? 'Continue to Marketplace' : 'Explore Now'}
				</button>
			</div>

			{/* Navigation Instructions */}
			<div 
				style={{
					position: 'fixed',
					bottom: '40px',
					left: 0,
					right: 0,
					textAlign: 'center',
					zIndex: 9998,
					pointerEvents: 'none',
					margin: 0,
					padding: '0 20px'
				}}
			>
				<p style={{
					fontFamily: 'monospace',
					fontSize: '12px',
					fontWeight: '700',
					color: '#ffffff',
					textTransform: 'uppercase',
					margin: '0 0 8px 0',
					padding: 0
				}}>
					Use mouse wheel, arrow keys, or touch to navigate
				</p>
				<p style={{
					fontFamily: 'monospace',
					fontSize: '12px',
					fontWeight: '700',
					color: '#ffffff',
					opacity: 0.6,
					textTransform: 'uppercase',
					margin: 0,
					padding: 0
				}}>
					Auto-play resumes after 3 seconds of inactivity
				</p>
			</div>

			{/* Top Right User Menu */}
			{user && (
				<div 
					style={{
						position: 'fixed',
						top: '20px',
						right: '20px',
						zIndex: 9998,
						pointerEvents: 'auto'
					}}
				>
					<button
						onClick={() => navigate('/select-role')}
						style={{
							padding: '10px 20px',
							fontSize: '14px',
							fontWeight: '600',
							backgroundColor: 'rgba(255, 255, 255, 0.1)',
							color: '#ffffff',
							border: '2px solid #ffffff',
							borderRadius: '6px',
							cursor: 'pointer',
							transition: 'all 0.3s ease',
							backdropFilter: 'blur(4px)',
							marginRight: '10px'
						}}
						onMouseEnter={(e) => {
							e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
						}}
						onMouseLeave={(e) => {
							e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
						}}
					>
						Go to Marketplace
					</button>
				</div>
			)}

			{/* Top Right Login Button */}
			{!user && (
				<div 
					style={{
						position: 'fixed',
						top: '20px',
						right: '20px',
						zIndex: 9998,
						pointerEvents: 'auto'
					}}
				>
					<button
						onClick={() => navigate('/start')}
						style={{
							padding: '10px 20px',
							fontSize: '14px',
							fontWeight: '600',
							backgroundColor: 'rgba(255, 255, 255, 0.1)',
							color: '#ffffff',
							border: '2px solid #ffffff',
							borderRadius: '6px',
							cursor: 'pointer',
							transition: 'all 0.3s ease',
							backdropFilter: 'blur(4px)'
						}}
						onMouseEnter={(e) => {
							e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
						}}
						onMouseLeave={(e) => {
							e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
						}}
					>
						Join Now
					</button>
				</div>
			)}
		</>
	);
}
