import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDashboard, getCauses, giveDonation } from '../services/api';

const STORAGE_KEY = 'rkl_child_id';

export default function Give() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState(null);
  const [causes, setCauses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Multi-step: 'cause' → 'amount' → 'confirm' → 'impact'
  const [step, setStep] = useState('cause');
  const [selectedCause, setSelectedCause] = useState(null);
  const [amount, setAmount] = useState('');
  const [giving, setGiving] = useState(false);
  const [impactResult, setImpactResult] = useState(null);

  const childId = localStorage.getItem(STORAGE_KEY);

  const loadData = async () => {
    if (!childId) { navigate('/'); return; }
    try {
      const [dash, causeList] = await Promise.all([
        getDashboard(childId),
        getCauses(),
      ]);
      if (!dash) { localStorage.removeItem(STORAGE_KEY); navigate('/'); return; }
      setDashboard(dash);
      setCauses(causeList);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  const refreshDashboard = async () => {
    const dash = await getDashboard(childId);
    setDashboard(dash);
  };

  const handleSelectCause = (cause) => {
    setSelectedCause(cause);
    setAmount('');
    setImpactResult(null);
    setStep('amount');
  };

  const handleGive = async () => {
    const amt = parseFloat(amount);
    if (isNaN(amt) || amt <= 0) { setError('Amount 0 se zyada hona chahiye.'); return; }
    setGiving(true);
    setError('');
    try {
      const result = await giveDonation(childId, amt, selectedCause.id);
      setImpactResult(result);
      setStep('impact');
      await refreshDashboard();
    } catch (err) {
      setError(err.message);
    } finally {
      setGiving(false);
    }
  };

  const handleGiveAgain = () => {
    setSelectedCause(null);
    setAmount('');
    setImpactResult(null);
    setStep('cause');
  };

  if (loading || !dashboard) {
    return <div className="page-container"><p className="loading-text">Load ho raha hai...</p></div>;
  }

  const balance = parseFloat(dashboard.balance);

  return (
    <div className="page-container give-page">
      {/* Header */}
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>← Wapas</button>
        <h1 className="page-title">❤️ GIVE</h1>
      </div>

      {/* Balance */}
      <div className="info-card">
        <span className="info-label">Aapka Balance</span>
        <span className="info-value">Rs. {balance.toLocaleString()}</span>
      </div>

      {error && <p className="error-text" style={{ background: 'white', padding: '0.8rem', borderRadius: '10px' }}>{error}</p>}

      {/* ======== STEP 1: Choose Cause ======== */}
      {step === 'cause' && (
        <div className="section-card give-card">
          <div className="give-header">
            <h2 className="give-title">Madad Karein!</h2>
            <p className="give-subtitle">Kis wajah ke liye dena chahte ho?</p>
          </div>
          <div className="cause-grid">
            {causes.map((cause) => (
              <button
                key={cause.id}
                className="cause-card"
                onClick={() => handleSelectCause(cause)}
                style={{ '--cause-color': cause.color }}
              >
                <span className="cause-icon">{cause.icon}</span>
                <span className="cause-name">{cause.name}</span>
                <span className="cause-desc">{cause.description}</span>
              </button>
            ))}
          </div>
          <p className="give-inspiration">
            Inspired by <strong>Alkhidmat Foundation</strong> — jo logon ki madad karta hai.
          </p>
        </div>
      )}

      {/* ======== STEP 2: Enter Amount ======== */}
      {step === 'amount' && selectedCause && (
        <div className="section-card give-card">
          <div className="give-header">
            <span className="give-selected-cause">{selectedCause.icon} {selectedCause.name}</span>
            <p className="give-subtitle">Kitna dena chahte ho?</p>
          </div>
          <div className="form-stack">
            <div className="form-group">
              <input
                type="number"
                className="form-input give-amount-input"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                min="1"
                max={balance}
                placeholder="Rs. ___"
                autoFocus
              />
            </div>
            <div className="quick-amounts give-quick">
              {[10, 25, 50, 100, 200].map((q) => (
                <button
                  key={q}
                  className={`quick-btn give-quick-btn ${parseFloat(amount) === q ? 'active' : ''}`}
                  onClick={() => setAmount(String(q))}
                >
                  Rs. {q}
                </button>
              ))}
            </div>
            <button
              className="primary-btn give-confirm-btn"
              onClick={handleGive}
              disabled={giving || !amount || parseFloat(amount) <= 0}
            >
              {giving ? 'Processing...' : `Rs. ${amount || '___'} Donate Karein ❤️`}
            </button>
            <button className="secondary-btn" onClick={() => setStep('cause')}>
              ← Doosri Cause Choose Karein
            </button>
          </div>
        </div>
      )}

      {/* ======== STEP 3: Impact Celebration ======== */}
      {step === 'impact' && impactResult && (
        <div className="section-card give-card impact-celebration">
          {/* Celebration particles */}
          <div className="celebration-particles">
            <span>❤️</span><span>⭐</span><span>🌟</span><span>💚</span><span>✨</span>
          </div>

          {/* Big cause icon */}
          <div className="impact-icon-big">{impactResult.cause_icon}</div>

          {/* Impact message */}
          <h2 className="impact-title">Shukriya, Aap Ne Madad Ki!</h2>
          <p className="impact-message">{impactResult.impact_message}</p>

          {/* Impact stats */}
          <div className="impact-stats">
            <div className="impact-stat">
              <span className="impact-stat-value">{impactResult.impact_icon} {impactResult.impact_unit}</span>
              <span className="impact-stat-label">Aapka Impact</span>
            </div>
            <div className="impact-stat">
              <span className="impact-stat-value">Rs. {parseFloat(impactResult.total_given).toLocaleString()}</span>
              <span className="impact-stat-label">Total Donated</span>
            </div>
            <div className="impact-stat">
              <span className="impact-stat-value">{impactResult.total_gives}x</span>
              <span className="impact-stat-label">Times Given</span>
            </div>
          </div>

          {/* Educational message */}
          <div className="impact-education">
            <p>{impactResult.educational_message}</p>
          </div>

          {/* Cause badge */}
          <div className="impact-cause-badge" style={{ borderColor: 'var(--cause-color, #27ae60)' }}>
            {impactResult.cause_icon} {impactResult.cause_name}
          </div>

          {/* New balance */}
          <p className="give-new-balance">
            Naya balance: <strong>Rs. {parseFloat(impactResult.new_balance).toLocaleString()}</strong>
          </p>

          {/* Alkhidmat note */}
          <p className="give-alkhidmat-note">
            Ye ek simulation hai. Real donations ke liye <strong>Alkhidmat Foundation</strong> se connect karein!
          </p>

          {/* Actions */}
          <div className="give-actions">
            <button className="primary-btn give-confirm-btn" onClick={handleGiveAgain}>
              Aur Madad Karein ❤️
            </button>
            <button className="secondary-btn" onClick={() => navigate('/dashboard')}>
              Dashboard par Wapas
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
