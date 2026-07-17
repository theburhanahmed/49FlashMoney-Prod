import { useEffect } from 'react';
import { useWalletStore } from '../store/walletStore';
import type { LedgerEntry } from '../types';
import CasinoLayout from '../components/CasinoLayout';

function DirectionIcon({ direction }: { direction: string }) {
  if (direction === 'CREDIT') {
    return (
      <div className="w-8 h-8 rounded-full bg-casino-green/20 flex items-center justify-center flex-shrink-0">
        <svg className="w-4 h-4 text-casino-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
        </svg>
      </div>
    );
  }
  return (
    <div className="w-8 h-8 rounded-full bg-casino-red/20 flex items-center justify-center flex-shrink-0">
      <svg className="w-4 h-4 text-casino-red" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
      </svg>
    </div>
  );
}

function LedgerRow({ entry }: { entry: LedgerEntry }) {
  const isCredit = entry.direction === 'CREDIT';
  return (
    <div className="flex items-center gap-3 p-3 hover:bg-casino-card/50 rounded-xl transition-colors">
      <DirectionIcon direction={entry.direction} />
      <div className="flex-1 min-w-0">
        <p className="text-white text-sm font-medium">{entry.entry_type.replace(/_/g, ' ')}</p>
        {entry.description && (
          <p className="text-casino-muted text-xs truncate mt-0.5">{entry.description}</p>
        )}
        <p className="text-casino-muted text-xs mt-0.5">
          {new Date(entry.created_at).toLocaleString()}
        </p>
      </div>
      <div className="text-right flex-shrink-0">
        <p className={`font-display font-bold text-sm ${isCredit ? 'text-casino-green' : 'text-casino-red'}`}>
          {isCredit ? '+' : '-'}{entry.amount}
        </p>
        <p className="text-casino-muted text-xs mt-0.5">Bal: {entry.balance_after}</p>
      </div>
    </div>
  );
}

function WalletPage() {
  const { wallet, ledgerEntries, ledgerCount, fetchWallet, fetchLedger, isLoading } = useWalletStore();

  useEffect(() => {
    fetchWallet();
    fetchLedger({ limit: 20, offset: 0 });
  }, [fetchWallet, fetchLedger]);

  return (
    <CasinoLayout>
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <div>
          <h1 className="font-display text-3xl font-bold text-white">Wallet</h1>
          <p className="text-casino-muted text-sm mt-1">Manage your funds</p>
        </div>

        {/* Balance Cards */}
        {wallet ? (
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#1d0840] via-casino-card to-[#0e0620] border border-casino-neon/30 p-6">
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
              <div className="absolute -right-10 -top-10 w-48 h-48 rounded-full bg-casino-neon/10 blur-3xl" />
            </div>
            <div className="relative">
              <p className="text-casino-muted text-xs uppercase tracking-wider mb-1">Total Balance</p>
              <p className="font-display text-4xl font-bold text-casino-gold text-gold-glow mb-6">
                {wallet.currency} {parseFloat(wallet.balance).toFixed(2)}
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-casino-bg/50 rounded-xl p-3">
                  <p className="text-casino-muted text-xs uppercase tracking-wider mb-1">Available</p>
                  <p className="font-display text-xl font-bold text-casino-green">
                    {parseFloat(wallet.available_balance).toFixed(2)}
                  </p>
                </div>
                <div className="bg-casino-bg/50 rounded-xl p-3">
                  <p className="text-casino-muted text-xs uppercase tracking-wider mb-1">Reserved</p>
                  <p className="font-display text-xl font-bold text-casino-neon">
                    {parseFloat(wallet.reserved_balance).toFixed(2)}
                  </p>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${wallet.status === 'ACTIVE' ? 'bg-casino-green' : 'bg-casino-red'}`} />
                <span className="text-casino-muted text-xs capitalize">{wallet.status}</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="casino-card p-8 flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-casino-neon border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-3">
          <button className="casino-card p-4 flex flex-col items-center gap-2 hover:border-casino-gold hover:shadow-gold transition-all duration-200 group">
            <div className="w-12 h-12 rounded-full bg-casino-gold/20 flex items-center justify-center group-hover:bg-casino-gold/30 transition-colors">
              <svg className="w-6 h-6 text-casino-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
            </div>
            <span className="font-display font-bold text-white group-hover:text-casino-gold transition-colors">Deposit</span>
            <span className="text-casino-muted text-xs">Add funds to wallet</span>
          </button>
          <button className="casino-card p-4 flex flex-col items-center gap-2 hover:border-casino-neon hover:shadow-neon transition-all duration-200 group">
            <div className="w-12 h-12 rounded-full bg-casino-neon/20 flex items-center justify-center group-hover:bg-casino-neon/30 transition-colors">
              <svg className="w-6 h-6 text-casino-neon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <span className="font-display font-bold text-white group-hover:text-casino-neon transition-colors">Withdraw</span>
            <span className="text-casino-muted text-xs">Transfer to bank</span>
          </button>
        </div>

        {/* Transaction History */}
        <div className="casino-card overflow-hidden">
          <div className="p-4 border-b border-casino-border flex items-center justify-between">
            <h2 className="section-title text-lg">Transaction History</h2>
            <span className="text-casino-muted text-xs">{ledgerCount} entries</span>
          </div>

          {isLoading ? (
            <div className="p-8 flex items-center justify-center">
              <div className="w-8 h-8 border-2 border-casino-neon border-t-transparent rounded-full animate-spin" />
            </div>
          ) : ledgerEntries.length === 0 ? (
            <div className="p-8 text-center">
              <div className="text-4xl mb-3">📭</div>
              <p className="text-casino-muted text-sm">No transactions yet</p>
            </div>
          ) : (
            <div className="divide-y divide-casino-border/30 px-2 py-1">
              {ledgerEntries.map((entry) => (
                <LedgerRow key={entry.id} entry={entry} />
              ))}
            </div>
          )}
        </div>
      </div>
    </CasinoLayout>
  );
}

export default WalletPage;
