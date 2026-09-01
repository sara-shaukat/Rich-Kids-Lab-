import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDashboard, getSpendScenarios, spend } from '../services/api';

const STORAGE_KEY = 'rkl_child_id';

export default function Spend() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState(null);
  const [scenario, setScenario] = useState(null);
  const [loading, setLoading] = useState(true);
  const [spending, setSpending] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const childId = localStorage.getItem(STORAGE_KEY);

  const loadData = async () => {
    if (!childId) { navigate('/'); return; }
    try {
      const [dash, scen] = await Promise.all([
        getDashboard(childId),
        getSpendScenarios(childId),
      ]);
      if (!dash) { localStorage.removeItem(STORAGE_KEY); navigate('/'); return; }
      setDashboard(dash);
      setScenario(scen);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  const handleSpend = async (option) => {
    if (!option.affordable && option.cost > 0) return;
    setSpending(true);
    setError('');
    setResult(null);
    try {
      const res = await spend(childId, option.id);
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setSpending(false);
    }
  };

  const handleNewRound = async () => {
    setResult(null);
    setSpending(true);
    try {
      const scen = await getSpendScenarios(childId);
      setScenario(scen);
      const dash = await getDashboard(childId);
      setDashboard(dash);
    } catch (err) {
      setError(err.message);
    } finally {
      setSpending(false);
    }
  };

  if (loading || !dashboard || !scenario) {
    return <div className="page-container"><p className="loading-text">Load ho raha hai...</p></div>;
  }

  const balance = parseFloat(dashboard.balance);

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          ← Wapas
        </button>
        <h1 className="page-title">🛒 SPEND</h1>
      </div>

      {/* Balance */}
      <div className="info-card">
        <span className="info-label">Aapka Balance</span>
        <span className="info-value">Rs. {balance.toLocaleString()}</span>
      </div>

      {error && <p className="error-text" style={{ background: 'white', padding: '0.8rem', borderRadius: '10px' }}>{error}</p>}

      {/* ---- Result Screen ---- */}
      {result ? (
        <div className="section-card spend-result-card">
          {result.spent_amount > 0 ? (
            <>
              <div className="spend-result-icon">🛒</div>
              <h2 className="spend-result-title">Aapne {result.option_name} khareeda!</h2>
              <p className="spend-result-amount">Rs. {parseFloat(result.spent_amount).toLocaleString()} spend kiye</p>
            </>
          ) : (
            <>
              <div className="spend-result-icon">💡</div>
              <h2 className="spend-result-title">Smart Choice!</h2>
            </>
          )}

          <div className="result-card">
            <p className="result-message">{result.message}</p>
          </div>

          <p className="spend-new-balance">
            Naya balance: <strong>Rs. {parseFloat(result.new_balance).toLocaleString()}</strong>
          </p>

          <p className="spend-educational">
            Financial choices have consequences — har faisla aapke paisay ko affect karta hai!
          </p>

          <div className="spend-actions">
            <button className="primary-btn" onClick={handleNewRound} disabled={spending}>
              {spending ? 'Loading...' : 'Aur Choices Dekhein'}
            </button>
            <button className="secondary-btn" onClick={() => navigate('/dashboard')}>
              Dashboard par Wapas
            </button>
          </div>
        </div>
      ) : (
        /* ---- Scenario Selection ---- */
        <div className="section-card">
          <h2 className="section-title">{scenario.title}</h2>
          <p className="section-hint">Ek option choose karein:</p>

          <div className="spend-options-grid">
            {scenario.options.map((option) => {
              const isSave = option.id === 'save_instead';
              const disabled = !option.affordable && !isSave;
              return (
                <button
                  key={option.id}
                  className={`spend-option-card ${isSave ? 'save-option' : ''} ${disabled ? 'disabled-option' : ''}`}
                  onClick={() => !disabled && handleSpend(option)}
                  disabled={disabled || spending}
                >
                  <span className="spend-option-name">{option.name}</span>
                  {option.cost > 0 ? (
                    <span className="spend-option-cost">Rs. {option.cost}</span>
                  ) : (
                    <span className="spend-option-cost free">FREE</span>
                  )}
                  {disabled && (
                    <span className="spend-option-locked">Balance kam hai</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
