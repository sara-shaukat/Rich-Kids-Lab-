import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDashboard } from '../services/api';
import Mascot from '../components/Mascot';

const STORAGE_KEY = 'rkl_child_id';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showTrackRecord, setShowTrackRecord] = useState(false);
  const [toast, setToast] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const childId = localStorage.getItem(STORAGE_KEY);
    if (!childId) { navigate('/'); return; }
    getDashboard(childId).then((result) => {
      if (!result) { localStorage.removeItem(STORAGE_KEY); navigate('/'); return; }
      setData(result);
      setLoading(false);
    });
  }, [navigate]);

  if (loading || !data) {
    return <div className="dashboard-container"><p className="loading-text">Load ho raha hai...</p></div>;
  }

  const balance = parseFloat(data.balance);
  const netWorth = parseFloat(data.net_worth || 0);
  const totalSaved = parseFloat(data.total_saved);
  const totalSpent = parseFloat(data.total_spent);
  const totalGrown = parseFloat(data.total_grown);
  const totalGiven = parseFloat(data.total_given);
  const goal = data.active_goal;
  const badges = data.badges || [];
  const unearnedBadges = data.unearned_badges || [];
  const level = data.level || {};
  const assets = data.assets || [];
  const liabilities = data.liabilities || [];
  const businessHistory = data.business_history || [];
  const investmentHistory = data.investment_history || [];

  const handleBadgeClick = (badge) => {
    setToast(badge.meme_line);
    setTimeout(() => setToast(null), 3000);
  };

  return (
    <div className="dashboard-container dashboard-v2">
      {/* Toast notification */}
      {toast && <div className="badge-toast">{toast}</div>}

      {/* Mascot */}
      <Mascot
        line={data.mascot_line || ''}
        mode={data.mascot_mode || 'hype'}
        onClick={() => {
          const tips = [
            "Paisa follows my brother, paisa follows!",
            "Champion log soch ke kharch karte hain!",
            "Aaj kuch naya seekhte hain!",
            "Bina goal ke archer? Target set karo!",
          ];
          setToast(tips[Math.floor(Math.random() * tips.length)]);
          setTimeout(() => setToast(null), 3000);
        }}
      />

      {/* Header */}
      <div className="dashboard-header">
        <h1 className="dashboard-title">Rich Kids Lab</h1>
        <span className="child-id">ID: {data.anonymous_id}</span>
      </div>

      {/* Balance Card */}
      <div className="balance-card balance-v2">
        <div className="balance-coin">💰</div>
        <p className="balance-label">Aapka Balance</p>
        <p className="balance-amount">Rs. {balance.toLocaleString()}</p>
        <p className="net-worth-line">Net Worth: <strong>Rs. {netWorth.toLocaleString()}</strong></p>
      </div>

      {/* Level Bar */}
      {level.level && (
        <div className="level-section">
          <div className="level-header">
            <span className="level-badge">Lvl {level.level}</span>
            <span className="level-name">{level.name}</span>
            {level.next_level_name && (
              <span className="level-next">→ {level.next_level_name}</span>
            )}
          </div>
          <div className="level-bar">
            <div
              className="level-fill"
              style={{ width: `${level.progress_to_next || 0}%` }}
            />
          </div>
          <p className="level-actions">{level.total_actions} actions done</p>
        </div>
      )}

      {/* Badges */}
      {(badges.length > 0 || unearnedBadges.length > 0) && (
        <div className="badges-section">
          <h3 className="section-title">🏆 Badges</h3>
          <div className="badges-grid">
            {badges.map((b) => (
              <button
                key={b.id}
                className="badge-item badge-earned"
                onClick={() => handleBadgeClick(b)}
              >
                <span className="badge-icon">{b.icon}</span>
                <span className="badge-name">{b.name}</span>
              </button>
            ))}
            {unearnedBadges.map((b) => (
              <div key={b.id} className="badge-item badge-locked" title={b.condition_desc}>
                <span className="badge-icon badge-icon-locked">🔒</span>
                <span className="badge-name badge-name-locked">{b.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* My Money Empire — Assets vs Liabilities */}
      {(assets.length > 0 || liabilities.length > 0) && (
        <div className="empire-section">
          <h3 className="section-title">🏰 My Money Empire</h3>
          <div className="empire-grid">
            <div className="empire-col empire-assets">
              <h4>✅ Assets</h4>
              {assets.length === 0 && <p className="empire-empty">Koi asset nahi abhi</p>}
              {assets.map((a, i) => (
                <div key={i} className="empire-item empire-item-asset">
                  <span>{a.name}</span>
                  <span className="empire-amount">{a.label}</span>
                </div>
              ))}
            </div>
            <div className="empire-col empire-liabilities">
              <h4>📉 Liabilities</h4>
              {liabilities.length === 0 && <p className="empire-empty">Koi liability nahi — smart!</p>}
              {liabilities.map((l, i) => (
                <div key={i} className="empire-item empire-item-liability">
                  <span>{l.name}</span>
                  <span className="empire-amount">{l.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Business Track Record */}
      {(businessHistory.length > 0 || investmentHistory.length > 0) && (
        <div className="track-section">
          <button
            className="track-toggle"
            onClick={() => setShowTrackRecord(!showTrackRecord)}
          >
            📊 Track Record {showTrackRecord ? '▲' : '▼'}
          </button>
          {showTrackRecord && (
            <div className="track-list">
              {businessHistory.map((b, i) => (
                <div key={`biz-${i}`} className={`track-item ${b.is_profit ? 'track-profit' : 'track-loss'}`}>
                  <span className="track-name">{b.name}</span>
                  <span className="track-result">{b.is_profit ? '✅' : '❌'} {b.profit >= 0 ? '+' : ''}Rs. {parseFloat(b.profit).toLocaleString()}</span>
                  <span className="track-verdict">{b.verdict}</span>
                </div>
              ))}
              {investmentHistory.map((inv, i) => (
                <div key={`inv-${i}`} className={`track-item ${inv.is_profit ? 'track-profit' : 'track-loss'}`}>
                  <span className="track-name">Investment ({inv.risk_level})</span>
                  <span className="track-result">{inv.is_profit ? '✅' : '❌'} {inv.profit_loss >= 0 ? '+' : ''}Rs. {parseFloat(inv.profit_loss).toLocaleString()}</span>
                  <span className="track-verdict">{inv.verdict}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Goal Progress */}
      {goal && (
        <div className="goal-card goal-v2">
          <p className="goal-label">🎯 Mera Goal</p>
          <p className="goal-name">{goal.name}</p>
          <div className="goal-progress">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{
                  width: `${Math.min(100, (parseFloat(goal.saved_amount) / parseFloat(goal.target_amount)) * 100)}%`,
                }}
              />
            </div>
            <p className="progress-text">
              Rs. {parseFloat(goal.saved_amount).toLocaleString()} / Rs. {parseFloat(goal.target_amount).toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {/* Summary Row */}
      <div className="summary-row summary-v2">
        <div className="summary-item save">
          <span className="summary-value">Rs. {totalSaved.toLocaleString()}</span>
          <span className="summary-label">💰 Saved</span>
        </div>
        <div className="summary-item spend">
          <span className="summary-value">Rs. {totalSpent.toLocaleString()}</span>
          <span className="summary-label">💸 Spent</span>
        </div>
        <div className="summary-item grow">
          <span className="summary-value">Rs. {totalGrown.toLocaleString()}</span>
          <span className="summary-label">📈 Grown</span>
        </div>
        <div className="summary-item give">
          <span className="summary-value">Rs. {totalGiven.toLocaleString()}</span>
          <span className="summary-label">🤲 Given</span>
        </div>
      </div>

      <button className="paisa-map-entry" onClick={() => navigate('/map')}>
        <span className="paisa-map-entry-kicker">Paisa Duniya</span>
        <span className="paisa-map-entry-title">Open the money map</span>
        <span className="paisa-map-entry-hint">Abhi: Lock-In Peak · beat it to reach Gatekeep</span>
      </button>

      {/* Action Buttons */}
      <div className="action-grid action-grid-v2">
        <button className="action-btn save-btn" onClick={() => navigate('/save')}>
          <span className="action-icon">💰</span>
          <span className="action-text">SAVE</span>
          <span className="action-hint">Paise bachao</span>
        </button>
        <button className="action-btn spend-btn" onClick={() => navigate('/spend')}>
          <span className="action-icon">🛒</span>
          <span className="action-text">SPEND</span>
          <span className="action-hint">Paise kharch karo</span>
        </button>
        <button className="action-btn grow-btn" onClick={() => navigate('/grow')}>
          <span className="action-icon">🌱</span>
          <span className="action-text">GROW</span>
          <span className="action-hint">Paise barhao</span>
        </button>
        <button className="action-btn give-btn" onClick={() => navigate('/give')}>
          <span className="action-icon">❤️</span>
          <span className="action-text">GIVE</span>
          <span className="action-hint">Madad karo</span>
        </button>
      </div>

      {/* Quests entry */}
      <button className="mentor-btn" onClick={() => navigate('/quests')}>
        🗺️ Aaj ke Quests — mushkil faisla!
      </button>

      {/* AI Mentor */}
      <button className="mentor-btn" onClick={() => navigate('/mentor')}>
        🤖 AI Mentor se baat karein
      </button>
    </div>
  );
}
