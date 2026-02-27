import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import ScrollMorphHero from '@/components/ui/scroll-morph-hero';
import '../css/Start.css';

export default function Start() {
  const [mode, setMode] = useState('login');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { login, signup } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    const form = e.target;
    const email = form.email.value.trim().toLowerCase();
    const password = form.password.value;
    try {
      await login(email, password);
      navigate('/select-role');
    } catch (err) {
      setError(err.message || 'Invalid email or password');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    const form = e.target;
    const name = form.name.value.trim();
    const email = form.email.value.trim().toLowerCase();
    const password = form.password.value;
    if (!name || !email || !password) {
      setError('Name, email and password are required');
      setSubmitting(false);
      return;
    }
    try {
      await signup(name, email, password);
      navigate('/select-role');
    } catch (err) {
      setError(err.message || 'Signup failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="start-page start-layout h-screen w-screen overflow-hidden">
      <ScrollMorphHero 
        renderAuthContent={() => (
          <div className="start-card">
            <h1 className="text-white text-4xl mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>Art Marketplace</h1>
            <p className="sub text-gray-300 mb-6" style={{ fontFamily: "'Playfair Display', serif" }}>Welcome to ArtVerse</p>
            {error && <div className="start-error text-red-400 mb-4">{error}</div>}
            {mode === 'login' ? (
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label htmlFor="login_email" className="block text-gray-300 text-sm mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>Email</label>
                  <input 
                    id="login_email" 
                    name="email" 
                    type="email" 
                    required 
                    className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white focus:outline-none focus:border-gray-400"
                  />
                </div>
                <div>
                  <label htmlFor="login_password" className="block text-gray-300 text-sm mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>Password</label>
                  <input 
                    id="login_password" 
                    name="password" 
                    type="password" 
                    required 
                    className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white focus:outline-none focus:border-gray-400"
                  />
                </div>
                <button 
                  type="submit" 
                  disabled={submitting}
                  className="w-full bg-gray-700 hover:bg-gray-600 text-white font-semibold py-2 rounded transition"
                  style={{ fontFamily: "'Playfair Display', serif" }}
                >
                  {submitting ? 'Logging in…' : 'Log In'}
                </button>
                <div className="toggle-link text-gray-400 text-sm">
                  {"Don't have an account? "}
                  <button 
                    type="button" 
                    className="link-btn text-gray-200 hover:text-white underline"
                    onClick={() => setMode('signup')}
                  >
                    Sign up here
                  </button>
                </div>
              </form>
            ) : (
              <form onSubmit={handleSignup} className="space-y-4">
                <div>
                  <label htmlFor="signup_name" className="block text-gray-300 text-sm mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>Full Name</label>
                  <input 
                    id="signup_name" 
                    name="name" 
                    type="text" 
                    required 
                    className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white focus:outline-none focus:border-gray-400"
                  />
                </div>
                <div>
                  <label htmlFor="signup_email" className="block text-gray-300 text-sm mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>Email</label>
                  <input 
                    id="signup_email" 
                    name="email" 
                    type="email" 
                    required 
                    className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white focus:outline-none focus:border-gray-400"
                  />
                </div>
                <div>
                  <label htmlFor="signup_password" className="block text-gray-300 text-sm mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>Password</label>
                  <input 
                    id="signup_password" 
                    name="password" 
                    type="password" 
                    minLength={6} 
                    required 
                    className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white focus:outline-none focus:border-gray-400"
                  />
                </div>
                <button 
                  type="submit" 
                  className="btn-alt w-full bg-gray-700 hover:bg-gray-600 text-white font-semibold py-2 rounded transition"
                  disabled={submitting}
                  style={{ fontFamily: "'Playfair Display', serif" }}
                >
                  {submitting ? 'Creating…' : 'Create Account'}
                </button>
                <div className="toggle-link text-gray-400 text-sm">
                  Already have an account?{' '}
                  <button 
                    type="button" 
                    className="link-btn text-gray-200 hover:text-white underline"
                    onClick={() => setMode('login')}
                  >
                    Log in here
                  </button>
                </div>
              </form>
            )}
            <button
              type="button"
              className="w-full mt-4 bg-transparent border border-gray-500 hover:border-gray-300 text-gray-200 hover:text-white font-semibold py-2 rounded transition"
              style={{ fontFamily: "'Playfair Display', serif" }}
              onClick={() => navigate('/')}
            >
              Return to homepage
            </button>
          </div>
        )}
      />
    </div>
  );
}
