import { useState, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import GlowButton from '../components/GlowButton';

function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login, isLoading, error, clearError } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    clearError();
    try {
      await login(username, password);
      navigate('/dashboard');
    } catch {
      // error is set in store
    }
  };

  return (
    <div className="min-h-screen bg-casino-gradient flex flex-col items-center justify-center px-4 relative overflow-hidden">
      {/* Background decorative elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-casino-neon/10 blur-3xl" />
        <div className="absolute -bottom-40 -right-40 w-96 h-96 rounded-full bg-casino-gold/10 blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-casino-violet/5 blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="font-display font-bold text-4xl tracking-widest mb-1">
            <span className="text-casino-gold text-gold-glow">49FLASH</span>
            <span className="text-white">MONEY</span>
          </h1>
          <p className="text-casino-muted text-sm">Premium Gaming Platform</p>
        </div>

        {/* Card */}
        <div className="casino-card p-8">
          <h2 className="font-display text-2xl font-bold text-white mb-6 text-center">Sign In</h2>

          {error && (
            <div className="bg-casino-red/10 border border-casino-red/30 rounded-xl px-4 py-3 mb-5 text-casino-red text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label htmlFor="username" className="block text-casino-muted text-xs font-medium uppercase tracking-wider mb-2">
                Username or Email
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                placeholder="Enter your username"
                className="casino-input"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-casino-muted text-xs font-medium uppercase tracking-wider mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Enter your password"
                className="casino-input"
              />
            </div>

            <div className="mt-2">
              <GlowButton
                type="submit"
                variant="gold"
                fullWidth
                disabled={isLoading}
              >
                {isLoading ? 'Signing In...' : 'Sign In'}
              </GlowButton>
            </div>
          </form>
        </div>

        {/* Register link */}
        <p className="text-center text-casino-muted mt-6 text-sm">
          New to 49FlashMoney?{' '}
          <Link to="/register" className="text-casino-gold hover:text-casino-gold-light font-semibold transition-colors">
            Create Account
          </Link>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
