import React, { useEffect, useState } from 'react';
import { adminApi, type AuditLogEntry, type WithdrawalSummary, type RoundSummary } from '../api/admin';

type AdminTab = 'engines' | 'rounds' | 'withdrawals' | 'audit';

const AdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AdminTab>('engines');

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Admin Dashboard</h1>
      <nav style={{ display: 'flex', gap: '12px', marginBottom: '24px', borderBottom: '1px solid #ddd', paddingBottom: '12px' }}>
        {(['engines', 'rounds', 'withdrawals', 'audit'] as AdminTab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderBottom: activeTab === tab ? '2px solid #007bff' : '2px solid transparent',
              background: 'none',
              cursor: 'pointer',
              fontWeight: activeTab === tab ? 'bold' : 'normal',
              textTransform: 'capitalize',
            }}
          >
            {tab}
          </button>
        ))}
      </nav>

      {activeTab === 'engines' && <EnginesPanel />}
      {activeTab === 'rounds' && <RoundsPanel />}
      {activeTab === 'withdrawals' && <WithdrawalsPanel />}
      {activeTab === 'audit' && <AuditPanel />}
    </div>
  );
};

const EnginesPanel: React.FC = () => {
  const [engines, setEngines] = useState<Array<{ game_kind: string; module: string }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi.getEngines()
      .then((res) => setEngines(res.data.engines))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading engines...</p>;

  return (
    <div>
      <h2>Registered Game Engines</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
            <th style={{ padding: '8px' }}>Game Kind</th>
            <th style={{ padding: '8px' }}>Module</th>
            <th style={{ padding: '8px' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {engines.map((e) => (
            <tr key={e.game_kind} style={{ borderBottom: '1px solid #eee' }}>
              <td style={{ padding: '8px' }}>{e.game_kind}</td>
              <td style={{ padding: '8px' }}>{e.module}</td>
              <td style={{ padding: '8px' }}>
                <button style={{ marginRight: '8px', padding: '4px 8px' }}>Configure</button>
                <button style={{ padding: '4px 8px', color: 'red' }}>Disable</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const RoundsPanel: React.FC = () => {
  const [rounds, setRounds] = useState<RoundSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi.getRounds({ limit: 50 })
      .then((res) => setRounds(res.data.results))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading rounds...</p>;

  return (
    <div>
      <h2>Game Round History</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
            <th style={{ padding: '8px' }}>ID</th>
            <th style={{ padding: '8px' }}>Game</th>
            <th style={{ padding: '8px' }}>Status</th>
            <th style={{ padding: '8px' }}>Entry Fee</th>
            <th style={{ padding: '8px' }}>Players</th>
            <th style={{ padding: '8px' }}>Created</th>
          </tr>
        </thead>
        <tbody>
          {rounds.map((r) => (
            <tr key={r.id} style={{ borderBottom: '1px solid #eee' }}>
              <td style={{ padding: '8px', fontFamily: 'monospace', fontSize: '12px' }}>{r.id.slice(0, 8)}</td>
              <td style={{ padding: '8px' }}>{r.game_kind}</td>
              <td style={{ padding: '8px' }}>{r.status}</td>
              <td style={{ padding: '8px' }}>{r.entry_fee}</td>
              <td style={{ padding: '8px' }}>{r.player_count}</td>
              <td style={{ padding: '8px' }}>{new Date(r.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const WithdrawalsPanel: React.FC = () => {
  const [withdrawals, setWithdrawals] = useState<WithdrawalSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi.getWithdrawals({ status: 'REQUESTED' })
      .then((res) => setWithdrawals(res.data.results))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleApprove = async (id: string) => {
    try {
      await adminApi.approveWithdrawal(id);
      setWithdrawals((prev) => prev.filter((w) => w.id !== id));
    } catch (error) {
      console.error('Failed to approve withdrawal:', error);
    }
  };

  const handleReject = async (id: string) => {
    const reason = prompt('Rejection reason:');
    if (reason === null) return;
    try {
      await adminApi.rejectWithdrawal(id, reason);
      setWithdrawals((prev) => prev.filter((w) => w.id !== id));
    } catch (error) {
      console.error('Failed to reject withdrawal:', error);
    }
  };

  if (loading) return <p>Loading withdrawals...</p>;

  return (
    <div>
      <h2>Pending Withdrawals</h2>
      {withdrawals.length === 0 ? (
        <p>No pending withdrawals.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
              <th style={{ padding: '8px' }}>User</th>
              <th style={{ padding: '8px' }}>Amount</th>
              <th style={{ padding: '8px' }}>Requested</th>
              <th style={{ padding: '8px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {withdrawals.map((w) => (
              <tr key={w.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '8px' }}>{w.user}</td>
                <td style={{ padding: '8px' }}>{w.amount}</td>
                <td style={{ padding: '8px' }}>{new Date(w.requested_at).toLocaleDateString()}</td>
                <td style={{ padding: '8px' }}>
                  <button onClick={() => handleApprove(w.id)} style={{ marginRight: '8px', padding: '4px 12px', background: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Approve</button>
                  <button onClick={() => handleReject(w.id)} style={{ padding: '4px 12px', background: '#dc3545', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Reject</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

const AuditPanel: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi.getAuditLogs({ limit: 100 })
      .then((res) => setLogs(res.data.results))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading audit logs...</p>;

  return (
    <div>
      <h2>Audit Logs</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
            <th style={{ padding: '8px' }}>Timestamp</th>
            <th style={{ padding: '8px' }}>User</th>
            <th style={{ padding: '8px' }}>Action</th>
            <th style={{ padding: '8px' }}>Description</th>
            <th style={{ padding: '8px' }}>Resource</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id} style={{ borderBottom: '1px solid #eee' }}>
              <td style={{ padding: '8px', fontSize: '12px' }}>{new Date(log.timestamp).toLocaleString()}</td>
              <td style={{ padding: '8px' }}>{log.user}</td>
              <td style={{ padding: '8px' }}>{log.action}</td>
              <td style={{ padding: '8px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{log.description}</td>
              <td style={{ padding: '8px', fontSize: '12px' }}>{log.resource_type}:{log.resource_id?.slice(0, 8)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AdminPage;
