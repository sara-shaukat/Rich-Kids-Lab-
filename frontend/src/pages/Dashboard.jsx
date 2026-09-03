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
  const [coinsFell, setCoinsFell] = useState(false);
  const navigate = useNavigate();
  const childId = localStorage.getItem(STORAGE_KEY);

  useEffect(() => {
    if (!childId) { navigate('/'); return; }
    getDashboard(childId).then((result) => {
      if (!result) { localStorage.removeItem(STORAGE_KEY); navigate('/'); return; }
      setData(result);
      setLoading(false);
      // One-time coin fall on first load
      setTimeout(() => setCoinsFell(true), 300);
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

  // Mission card copy — Level 1 is the "First Goal" mission in the Vault
  const missionName = Number(level.level) === 1 ? 'First Goal' : level.name;

  return (
    <div className="dashboard-container dashboard-v3">
      {/* Toast notification */}
      {toast && <div className="badge-toast">{toast}</div>}

      {/* ── 1. WELCOME — brand + Paisa Bot ── */}
      <header className="dash-hero">
        <div className="dash-hero-brand">
          <h1 className="dash-hero-title">Rich Kids Lab</h1>
          <p className="dash-hero-tagline">Learn money by making money decisions.</p>
        </div>
        <div className="dash-hero-bot">
          <Mascot
            line={data.mascot_line || ''}
            mode={data.mascot_mode || 'hype'}
            onClick={() => {
              const tips = [
                "Money follows my brother, money follows!",
                "Champion log soch ke kharch karte hain!",
                "Aaj kuch naya seekhte hain!",
                "Bina goal ke archer? Target set karo!",
              ];
              setToast(tips[Math.floor(Math.random() * tips.length)]);
              setTimeout(() => setToast(null), 3000);
            }}
          />
        </div>
      </header>
      <div className="dash-hero-meta">
        <span className="child-id">ID: {data.anonymous_id}</span>
      </div>

      {/* ── 2. MONEY — the anchor ── */}
      <section className={`money-card${coinsFell ? ' coins-fell' : ''}`}>
        <span className="money-card-coin" aria-hidden="true">💰</span>
        {coinsFell && (
          <div className="coin-rain">
            <span className="falling-coin" style={{ left: '20%', animationDelay: '0s' }}>🪙</span>
            <span className="falling-coin" style={{ left: '45%', animationDelay: '0.15s' }}>🪙</span>
            <span className="falling-coin" style={{ left: '70%', animationDelay: '0.3s' }}>🪙</span>
            <span className="falling-coin" style={{ left: '35%', animationDelay: '0.45s' }}>🪙</span>
            <span className="falling-coin" style={{ left: '60%', animationDelay: '0.1s' }}>🪙</span>
          </div>
        )}
        <p className="money-card-label">Your money</p>
        <p className="money-card-amount">Rs. {balance.toLocaleString()}</p>
        <p className="money-card-net">Net worth: Rs. {netWorth.toLocaleString()}</p>
      </section>

      {/* ── 3. CURRENT MISSION ── */}
      {level.level && (
        <section className="mission-card">
          <div className="mission-top">
            <span className="mission-kicker">Current Mission</span>
            {level.next_level_name && (
              <span className="mission-next">Next: {level.next_level_name}</span>
            )}
          </div>
          <div className="mission-title-row">
            <span className="mission-level-chip">Level {level.level}</span>
            <h2 className="mission-name">{missionName}</h2>
          </div>
          <div className="mission-bar">
            <div
              className="mission-fill"
              style={{ width: `${level.progress_to_next || 0}%` }}
            />
          </div>
          <p className="mission-meta">{level.total_actions} actions completed</p>
          <button className="mission-cta" onClick={() => navigate('/vault')}>
            Continue Mission
            <span className="mission-cta-arrow" aria-hidden="true">→</span>
          </button>
        </section>
      )}

      {/* ── 4. QUICK ACTIONS ── */}
      <div className="qa-grid">
        <button className="qa-tile qa-save" onClick={() => navigate('/save')}>
          <span className="qa-icon" aria-hidden="true">💰</span>
          <span className="qa-title">Save</span>
          <span className="qa-hint">Paise bachao</span>
        </button>
        <button className="qa-tile qa-spend" onClick={() => navigate('/spend')}>
          <span className="qa-icon" aria-hidden="true">🛒</span>
          <span className="qa-title">Spend</span>
          <span className="qa-hint">Paise kharch karo</span>
        </button>
        <button className="qa-tile qa-grow" onClick={() => navigate('/grow')}>
          <span className="qa-icon" aria-hidden="true">🌱</span>
          <span className="qa-title">Grow</span>
          <span className="qa-hint">Paise barhao</span>
        </button>
        <button className="qa-tile qa-give" onClick={() => navigate('/give')}>
          <span className="qa-icon" aria-hidden="true">❤️</span>
          <span className="qa-title">Give</span>
          <span className="qa-hint">Madad karo</span>
        </button>
      </div>

      {/* ── 5. MONEY LAB — the special room ── */}
      <button className="lab-feature" onClick={() => navigate('/lab')}>
        <span className="lab-feature-icon" aria-hidden="true">🧪</span>
        <div className="lab-feature-body">
          <span className="lab-feature-kicker">Money Lab</span>
          <p className="lab-feature-line">Run a business. Make decisions. See what happens.</p>
        </div>
        <span className="lab-feature-cta">
          Start Experiment
          <span className="lab-feature-arrow" aria-hidden="true">→</span>
        </span>
      </button>

      {/* ── 6. BADGES ── */}
      {(badges.length > 0 || unearnedBadges.length > 0) && (
        <section className="badges-section">
          <h3 className="dash-section-title">🏆 Badges</h3>
          {badges.length === 0 && (
            <p className="badges-empty">Your first badge is waiting!</p>
          )}
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
                <span className="badge-name badge-name-locked">???</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── 7. GOAL ── */}
      {goal && (
        <section className="goal-card goal-v3">
          <p className="goal-v3-label">🎯 Your Goal</p>
          <p className="goal-v3-name">{goal.name}</p>
          <div className="goal-progress">
            <div className="progress-bar goal-v3-bar">
              <div
                className="progress-fill goal-v3-fill"
                style={{
                  width: `${Math.min(100, (parseFloat(goal.saved_amount) / parseFloat(goal.target_amount)) * 100)}%`,
                }}
              />
            </div>
            <p className="goal-v3-text">
              Rs. {parseFloat(goal.saved_amount).toLocaleString()} saved of Rs. {parseFloat(goal.target_amount).toLocaleString()}
            </p>
          </div>
        </section>
      )}

      {/* ── 8. MONEY SUMMARY — flat strip, no cards ── */}
      <div className="summary-strip">
        <div className="summary-strip-item save">
          <span className="summary-strip-value">Rs. {totalSaved.toLocaleString()}</span>
          <span className="summary-strip-label">Saved</span>
        </div>
        <div className="summary-strip-item spend">
          <span className="summary-strip-value">Rs. {totalSpent.toLocaleString()}</span>
          <span className="summary-strip-label">Spent</span>
        </div>
        <div className="summary-strip-item grow">
          <span className="summary-strip-value">Rs. {totalGrown.toLocaleString()}</span>
          <span className="summary-strip-label">Grown</span>
        </div>
        <div className="summary-strip-item give">
          <span className="summary-strip-value">Rs. {totalGiven.toLocaleString()}</span>
          <span className="summary-strip-label">Given</span>
        </div>
      </div>

      {/* ── 9. MY MONEY EMPIRE — money flow + assets/liabilities ── */}
      <section className="empire-section">
        <h3 className="dash-section-title">🏰 My Money Empire</h3>

        {/* Money In / Money Out */}
        <div className="money-flow">
          <div className="money-flow-item money-in">
            <span className="money-flow-icon">📥</span>
            <span className="money-flow-label">Money In</span>
            <span className="money-flow-amount">Rs. {(totalSaved + totalGrown).toLocaleString()}</span>
          </div>
          <div className="money-flow-divider" />
          <div className="money-flow-item money-out">
            <span className="money-flow-icon">📤</span>
            <span className="money-flow-label">Money Out</span>
            <span className="money-flow-amount">Rs. {totalSpent.toLocaleString()}</span>
          </div>
        </div>

        {/* Assets / Liabilities */}
        <div className="empire-grid">
          <div className="empire-col empire-assets">
            <h4>✅ Assets <small>(paisa LAYA)</small></h4>
            {assets.length === 0 && <p className="empire-empty">Grow karo — pehla asset yahan aayega!</p>}
            {assets.map((a, i) => (
              <div key={i} className="empire-item empire-item-asset">
                <span>{a.name}</span>
                <span className="empire-amount">{a.label}</span>
              </div>
            ))}
          </div>
          <div className="empire-col empire-liabilities">
            <h4>📉 Liabilities <small>(paisa LE GAYA)</small></h4>
            {liabilities.length === 0 && <p className="empire-empty">Koi liability nahi — smart!</p>}
            {liabilities.map((l, i) => (
              <div key={i} className="empire-item empire-item-liability">
                <span>{l.name}</span>
                <span className="empire-amount">{l.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 10. TRACK RECORD ── */}
      {(businessHistory.length > 0 || investmentHistory.length > 0) && (
        <section className="track-section">
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
        </section>
      )}

      {/* ── 11. QUESTS & MENTOR ── */}
      <div className="quest-mentor-strip">
        <button className="quest-strip-btn" onClick={() => navigate('/quests')}>
          <span className="quest-strip-icon">🗺️</span>
          <div className="quest-strip-text">
            <span className="quest-strip-title">Aaj ke Quests</span>
            <span className="quest-strip-hint">Mushkil faisla — challenge lo!</span>
          </div>
        </button>
        <button className="mentor-strip-btn" onClick={() => navigate('/mentor')}>
          <span className="mentor-strip-icon">🤖</span>
          <div className="mentor-strip-text">
            <span className="mentor-strip-title">AI Mentor</span>
            <span className="mentor-strip-hint">Se baat karein — seekho!</span>
          </div>
        </button>
      </div>

      {/* ── 12. ACHIEVEMENTS — Report Card + Certificate ── */}
      <div className="achievement-strip">
        <button className="achievement-btn achievement-report" onClick={() => navigate(`/reportcard/${childId}`)}>
          <span className="achievement-icon">📊</span>
          <div className="achievement-text">
            <span className="achievement-title">Money Report Card</span>
            <span className="achievement-hint">Apni financial skills ka grade dekho</span>
          </div>
        </button>
        <button className="achievement-btn achievement-cert" onClick={() => navigate(`/certificate/${childId}`)}>
          <span className="achievement-icon">📜</span>
          <div className="achievement-text">
            <span className="achievement-title">Certificate</span>
            <span className="achievement-hint">Apna achievement certificate dekho</span>
          </div>
        </button>
      </div>
    </div>
  );
}
