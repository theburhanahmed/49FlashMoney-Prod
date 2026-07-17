import { useState, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import GlowButton from '../components/GlowButton';

function RegisterPage() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const { register, isLoading, error, clearError } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    clearError();
    setLocalError(null);
    if (password !== passwordConfirm) {
      setLocalError('Passwords do not match');
      return;
    }
    try {
      await register({ username, email, password, password_confirm: passwordConfirm });
      navigate('/login');
    } catch {
      // error is set in store
    }
  };

  const displayError = localError ?? error;

  return (
    <div className="min-h-screen bg-casino-gradient flex flex-col items-center justify-center px-4 relative overflow-hidden">
      {/* Background decorative elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-casino-gold/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full bg-casino-neon/10 blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="font-display font-bold text-4xl tracking-widest mb-1">
            <span className="text-casino-gold text-gold-glow">49FLASH</span>
            <span className="text-white">MONEY</span>
          </h1>
          <p className="text-casino-muted text-sm">Create Your Account</p>
        </div>

        {/* Card */}
        <div className="casino-card p-8">
          <h2 className="font-display text-2xl font-bold text-white mb-6 text-center">Register</h2>

          {displayError && (
            <div className="bg-casino-red/10 border border-casino-red/30 rounded-xl px-4 py-3 mb-5 text-casino-red text-sm">
              {displayError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label htmlFor="username" className="block text-casino-muted text-xs font-medium uppercase tracking-wider mb-2">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                placeholder="Choose a username"
                className="casino-input"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-casino-muted text-xs font-medium uppercase tracking-wider mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="your@email.com"
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
                minLength={8}
                placeholder="Minimum 8 characters"
                className="casino-input"
              />
            </div>

            <div>
              <label htmlFor="passwordConfirm" className="block text-casino-muted text-xs font-medium uppercase tracking-wider mb-2">
                Confirm Password
              </label>
              <input
                id="passwordConfirm"
                type="password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                required
                minLength={8}
                placeholder="Repeat your password"
                className="casino-input"
              />
            </div>

            <div className="mt-2">
              <GlowButton
                type="submit"
                variant="neon"
                fullWidth
                disabled={isLoading}
              >
                {isLoading ? 'Creating Account...' : 'Create Account'}
              </GlowButton>
            </div>
          </form>
        </div>

        {/* Login link */}
        <p className="text-center text-casino-muted mt-6 text-sm">
          Already have an account?{' '}
          <Link to="/login" className="text-casino-gold hover:text-casino-gold-light font-semibold transition-colors">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}

export default RegisterPage;
