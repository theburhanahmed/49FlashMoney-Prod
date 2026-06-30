import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useWalletStore } from '../store/walletStore';

function DashboardPage() {
  const { user, logout } = useAuthStore();
  const { wallet, fetchWallet } = useWalletStore();

  useEffect(() => {
    fetchWallet();
  }, [fetchWallet]);

  return (
    <div style={{ maxWidth: 800, margin: '40px auto', padding: 24 }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>49FlashMoney</h1>
        <div>
          <span style={{ marginRight: 16 }}>{user?.username}</span>
          <button onClick={logout}>Logout</button>
        </div>
      </header>

      <nav style={{ margin: '20px 0', display: 'flex', gap: 16 }}>
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/wallet">Wallet</Link>
        <Link to="/games">Games</Link>
      </nav>

      <section style={{ marginTop: 24 }}>
        <h2>Wallet</h2>
        {wallet ? (
          <div style={{ background: '#f5f5f5', padding: 16, borderRadius: 8 }}>
            <p><strong>Balance:</strong> {wallet.currency} {wallet.balance}</p>
            <p><strong>Available:</strong> {wallet.currency} {wallet.available_balance}</p>
            <p><strong>Reserved:</strong> {wallet.currency} {wallet.reserved_balance}</p>
            <p><strong>Status:</strong> {wallet.status}</p>
          </div>
        ) : (
          <p>Loading wallet...</p>
        )}
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>Quick Actions</h2>
        <div style={{ display: 'flex', gap: 12 }}>
          <Link to="/wallet" style={{ padding: '10px 20px', background: '#007bff', color: '#fff', textDecoration: 'none', borderRadius: 4 }}>
            Deposit
          </Link>
          <Link to="/games" style={{ padding: '10px 20px', background: '#28a745', color: '#fff', textDecoration: 'none', borderRadius: 4 }}>
            Play Games
          </Link>
        </div>
      </section>
    </div>
  );
}

export default DashboardPage;
