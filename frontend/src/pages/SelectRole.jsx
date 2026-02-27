import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../App';
import { FlippingCard } from '@/components/ui/flipping-card';
import { Component as EtheralShadow } from '@/components/ui/etheral-shadow';
import '../css/SelectRole.css';

export default function SelectRole() {
  const { logout } = useAuth();
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'dark';
    return localStorage.getItem('theme') || 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));

  return (
    <div className="select-role-page">
      <div className="select-role-bg" aria-hidden="true">
        <EtheralShadow
          color="rgba(128, 128, 128, 1)"
          animation={{ scale: 100, speed: 90 }}
          noise={{ opacity: 1, scale: 1.2 }}
          sizing="fill"
        />
      </div>

      <div className="select-role-container select-role-content">
        <div className="topbar">
          <div className="brand">Art Marketplace</div>
          <div className="topbar-actions">
            <button type="button" className="theme-toggle" onClick={toggleTheme}>
              {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
            </button>
            <button type="button" className="link logout-btn" onClick={logout}>
              Logout
            </button>
          </div>
        </div>

        <div className="select-role-card">
          <h2>Choose how you want to continue</h2>
          <div className="select-role-flipping-cards">
            <FlippingCard
              width={360}
              height={340}
              className="select-role-flip-card"
              frontContent={
                <div className="flipping-card-face">
                  <img
                    src="https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=800&h=520&fit=crop"
                    alt="Art Buyer"
                    className="flipping-card-image"
                  />
                  <div className="flipping-card-text">
                    <h3>Buyer</h3>
                    <p>Discover and collect artwork you love.</p>
                  </div>
                </div>
              }
              backContent={
                <div className="flipping-card-back">
                  <p>Browse curated pieces and purchase with confidence.</p>
                  <Link className="flipping-card-button" to="/buyer">
                    Continue as Buyer →
                  </Link>
                </div>
              }
            />

            <FlippingCard
              width={360}
              height={340}
              className="select-role-flip-card"
              frontContent={
                <div className="flipping-card-face">
                  <img
                    src="https://images.unsplash.com/photo-1460661419201-fd4cecdf8a8b?w=800&h=520&fit=crop"
                    alt="Art Seller"
                    className="flipping-card-image"
                  />
                  <div className="flipping-card-text">
                    <h3>Seller</h3>
                    <p>Showcase your work and manage listings.</p>
                  </div>
                </div>
              }
              backContent={
                <div className="flipping-card-back">
                  <p>Upload art, set prices, and reach collectors.</p>
                  <Link className="flipping-card-button" to="/seller">
                    Continue as Seller →
                  </Link>
                </div>
              }
            />
          </div>
        </div>
      </div>
    </div>
  );
}
