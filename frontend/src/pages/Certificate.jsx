import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getCertificate } from '../services/api';

/**
 * Certificate — Level 1 completion certificate.
 * Displays a printable, shareable certificate with the child's
 * goal, badges, stats, and completion date.
 */
export default function Certificate() {
  const { anonymousId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!anonymousId) return;
    getCertificate(anonymousId)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [anonymousId]);

  if (loading) {
    return (
      <div className="cert-loading">
        <div className="cert-spinner" />
        <p>Loading certificate...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="cert-error">
        <div className="cert-error-icon">📜</div>
        <h2>Certificate not available yet</h2>
        <p>{error}</p>
        <button className="cert-back-btn" onClick={() => navigate('/vault')}>
          ← Back to Vault
        </button>
      </div>
    );
  }

  const completedDate = data.completed_at
    ? new Date(data.completed_at).toLocaleDateString('en-PK', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : '—';

  const stats = data.stats || {};

  return (
    <div className="cert-page">
      {/* Print button (hidden when printing) */}
      <div className="cert-toolbar">
        <button className="cert-back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>
        <button className="cert-print-btn" onClick={() => window.print()}>
          🖨️ Print / Save PDF
        </button>
        <Link to="/vault" className="cert-vault-link">
          Go to Vault Map
        </Link>
      </div>

      {/* Certificate card */}
      <div className="cert-card">
        {/* Decorative corners */}
        <div className="cert-corner cert-corner-tl" />
        <div className="cert-corner cert-corner-tr" />
        <div className="cert-corner cert-corner-bl" />
        <div className="cert-corner cert-corner-br" />

        {/* Header */}
        <div className="cert-header">
          <span className="cert-logo">🏦</span>
          <h1 className="cert-org">Rich Kids Lab</h1>
          <div className="cert-divider" />
          <h2 className="cert-title">Certificate of Achievement</h2>
          <p className="cert-subtitle">Level 1 — Your First Goal</p>
        </div>

        {/* Body */}
        <div className="cert-body">
          <p className="cert-presented">This is proudly presented to</p>
          <h3 className="cert-child-name">
            {data.child_name || data.child_id}
          </h3>
          <p className="cert-id">
            <span className="cert-id-label">Student ID</span>
            <span className="cert-id-value">{data.child_id}</span>
          </p>

          <p className="cert-achievement">
            for successfully completing the <strong>First Goal Challenge</strong>
          </p>

          {/* Goal card */}
          {data.goal && (
            <div className="cert-goal-card">
              <span className="cert-goal-icon">🎯</span>
              <div className="cert-goal-info">
                <span className="cert-goal-name">{data.goal.name}</span>
                <span className="cert-goal-amount">
                  Rs. {data.goal.saved_amount.toLocaleString()} saved
                  <span className="cert-goal-target">
                    {' '}
                    / Rs. {data.goal.target_amount.toLocaleString()} target
                  </span>
                </span>
              </div>
            </div>
          )}

          {/* Stats row */}
          <div className="cert-stats">
            <div className="cert-stat">
              <span className="cert-stat-value">Rs. {stats.total_saved?.toLocaleString() || 0}</span>
              <span className="cert-stat-label">Total Saved</span>
            </div>
            <div className="cert-stat">
              <span className="cert-stat-value">Rs. {stats.total_earned?.toLocaleString() || 0}</span>
              <span className="cert-stat-label">Total Earned</span>
            </div>
            <div className="cert-stat">
              <span className="cert-stat-value">{stats.businesses_completed || 0}</span>
              <span className="cert-stat-label">Businesses</span>
            </div>
            <div className="cert-stat">
              <span className="cert-stat-value">{stats.transaction_count || 0}</span>
              <span className="cert-stat-label">Decisions</span>
            </div>
          </div>

          {/* Badges */}
          {data.badges.length > 0 && (
            <div className="cert-badges">
              <h4 className="cert-badges-title">Badges Earned</h4>
              <div className="cert-badges-row">
                {data.badges.map((b) => (
                  <div key={b.name} className="cert-badge" title={b.description}>
                    <span className="cert-badge-icon">{b.icon}</span>
                    <span className="cert-badge-name">{b.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reflection quote */}
          {data.reflection && (
            <div className="cert-reflection">
              <p className="cert-reflection-quote">&ldquo;{data.reflection}&rdquo;</p>
              <p className="cert-reflection-label">— My biggest learning</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="cert-footer">
          <div className="cert-footer-left">
            <div className="cert-signature-line" />
            <span className="cert-signature-label">Paisa Bot</span>
          </div>
          <div className="cert-footer-center">
            <span className="cert-seal">🏅</span>
          </div>
          <div className="cert-footer-right">
            <div className="cert-signature-line" />
            <span className="cert-signature-label">{completedDate}</span>
          </div>
        </div>

        {/* Current balance */}
        <div className="cert-balance-strip">
          <span>Current Wallet Balance</span>
          <strong>Rs. {data.wallet_balance?.toLocaleString() || 0}</strong>
        </div>
      </div>

      {/* Next step prompt */}
      <div className="cert-next-step">
        <h3>🎉 What's next?</h3>
        <p>Level 2 "Needs vs Wants" is now unlocked! Keep your money journey going.</p>
        <Link to="/vault" className="cert-continue-btn">
          Continue Adventure →
        </Link>
      </div>
    </div>
  );
}
