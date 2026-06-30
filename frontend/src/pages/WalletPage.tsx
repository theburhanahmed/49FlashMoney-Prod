import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useWalletStore } from '../store/walletStore';
import type { LedgerEntry } from '../types';

function LedgerEntryRow({ entry }: { entry: LedgerEntry }) {
  const isCredit = entry.direction === 'CREDIT';
  return (
    <tr>
      <td>{new Date(entry.created_at).toLocaleString()}</td>
      <td>{entry.entry_type}</td>
      <td style={{ color: isCredit ? 'green' : 'red' }}>
        {isCredit ? '+' : '-'}{entry.amount}
      </td>
      <td>{entry.balance_after}</td>
      <td>{entry.description || '-'}</td>
    </tr>
  );
}

function WalletPage() {
  const { wallet, ledgerEntries, ledgerCount, fetchWallet, fetchLedger, isLoading } = useWalletStore();

  useEffect(() => {
    fetchWallet();
    fetchLedger({ limit: 20, offset: 0 });
  }, [fetchWallet, fetchLedger]);

  return (
    <div style={{ maxWidth: 900, margin: '40px auto', padding: 24 }}>
      <nav style={{ marginBottom: 20, display: 'flex', gap: 16 }}>
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/wallet">Wallet</Link>
        <Link to="/games">Games</Link>
      </nav>

      <h1>Wallet</h1>

      {wallet && (
        <div style={{ background: '#f5f5f5', padding: 16, borderRadius: 8, marginBottom: 24 }}>
          <p><strong>Balance:</strong> {wallet.currency} {wallet.balance}</p>
          <p><strong>Available:</strong> {wallet.currency} {wallet.available_balance}</p>
          <p><strong>Reserved:</strong> {wallet.currency} {wallet.reserved_balance}</p>
          <p><strong>Status:</strong> {wallet.status}</p>
        </div>
      )}

      <h2>Transaction History ({ledgerCount} entries)</h2>
      {isLoading ? (
        <p>Loading...</p>
      ) : ledgerEntries.length === 0 ? (
        <p>No transactions yet.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #ccc', textAlign: 'left' }}>
              <th style={{ padding: 8 }}>Date</th>
              <th style={{ padding: 8 }}>Type</th>
              <th style={{ padding: 8 }}>Amount</th>
              <th style={{ padding: 8 }}>Balance After</th>
              <th style={{ padding: 8 }}>Description</th>
            </tr>
          </thead>
          <tbody>
            {ledgerEntries.map((entry) => (
              <LedgerEntryRow key={entry.id} entry={entry} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default WalletPage;
