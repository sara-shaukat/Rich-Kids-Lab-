import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDashboard, getGoals, createGoal, saveToGoal } from '../services/api';

const STORAGE_KEY = 'rkl_child_id';

export default function Save() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState(null);
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(true);

  // Goal creation form
  const [goalName, setGoalName] = useState('');
  const [goalTarget, setGoalTarget] = useState('');
  const [createError, setCreateError] = useState('');
  const [creating, setCreating] = useState(false);

  // Save form
  const [saveAmount, setSaveAmount] = useState('');
  const [saveError, setSaveError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState(null);

  const childId = localStorage.getItem(STORAGE_KEY);

  const loadData = async () => {
    if (!childId) { navigate('/'); return; }
    const [dash, goalList] = await Promise.all([
      getDashboard(childId),
      getGoals(childId),
    ]);
    if (!dash) { localStorage.removeItem(STORAGE_KEY); navigate('/'); return; }
    setDashboard(dash);
    setGoals(goalList);
    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  const activeGoal = goals.find((g) => g.status === 'active') || null;

  // ---- Create goal ----
  const handleCreateGoal = async (e) => {
    e.preventDefault();
    setCreateError('');

    const target = parseFloat(goalTarget);
    if (!goalName.trim()) { setCreateError('Goal ka naam likhein.'); return; }
    if (isNaN(target) || target <= 0) { setCreateError('Target amount 0 se zyada hona chahiye.'); return; }

    setCreating(true);
    try {
      await createGoal(childId, goalName.trim(), target);
      setGoalName('');
      setGoalTarget('');
      await loadData();
    } catch (err) {
      setCreateError(err.message);
    } finally {
      setCreating(false);
    }
  };

  // ---- Save money ----
  const handleSave = async (e) => {
    e.preventDefault();
    setSaveError('');
    setSaveResult(null);

    const amount = parseFloat(saveAmount);
    if (isNaN(amount) || amount <= 0) { setSaveError('Amount 0 se zyada hona chahiye.'); return; }

    setSaving(true);
    try {
      const result = await saveToGoal(activeGoal.id, childId, amount);
      setSaveResult(result);
      setSaveAmount('');
      await loadData();
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading || !dashboard) {
    return <div className="page-container"><p className="loading-text">Load ho raha hai...</p></div>;
  }

  const balance = parseFloat(dashboard.balance);

  return (
    <div className="page-container page-save">
      {/* Header */}
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          ← Wapas
        </button>
        <h1 className="page-title">💰 SAVE</h1>
      </div>

      {/* Current Balance */}
      <div className="info-card">
        <span className="info-label">Aapka Balance</span>
        <span className="info-value">Rs. {balance.toLocaleString()}</span>
      </div>

      {/* ---- Create Goal Section ---- */}
      {!activeGoal ? (
        <div className="section-card">
          <h2 className="section-title">Naya Goal Banayein</h2>
          <p className="section-hint">Aap kya khareedna chahte ho? Uska goal set karein!</p>

          <form onSubmit={handleCreateGoal} className="form-stack">
            <div className="form-group">
              <label>Goal ka naam</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g., Headphones"
                value={goalName}
                onChange={(e) => setGoalName(e.target.value)}
                disabled={creating}
              />
            </div>
            <div className="form-group">
              <label>Kitna chahiye? (Rs.)</label>
              <input
                type="number"
                className="form-input"
                placeholder="8000"
                min="1"
                value={goalTarget}
                onChange={(e) => setGoalTarget(e.target.value)}
                disabled={creating}
              />
            </div>
            {createError && <p className="error-text">{createError}</p>}
            <button type="submit" className="primary-btn" disabled={creating}>
              {creating ? 'Ban raha hai...' : 'Goal Banayein'}
            </button>
          </form>
        </div>
      ) : (
        /* ---- Active Goal + Save Section ---- */
        <div className="section-card">
          <h2 className="section-title">Mera Goal: {activeGoal.name}</h2>

          {/* Progress */}
          <div className="goal-progress-block">
            <div className="progress-bar large">
              <div
                className="progress-fill"
                style={{
                  width: `${Math.min(100, (parseFloat(activeGoal.saved_amount) / parseFloat(activeGoal.target_amount)) * 100)}%`,
                }}
              />
            </div>
            <div className="progress-stats">
              <span>Rs. {parseFloat(activeGoal.saved_amount).toLocaleString()} saved</span>
              <span>Rs. {parseFloat(activeGoal.target_amount).toLocaleString()} target</span>
            </div>
            <p className="progress-pct">
              {Math.round((parseFloat(activeGoal.saved_amount) / parseFloat(activeGoal.target_amount)) * 100)}% complete
            </p>
          </div>

          {/* Save Form */}
          {activeGoal.status === 'active' && (
            <form onSubmit={handleSave} className="form-stack save-form">
              <label className="save-label">Aaj kitna save karna hai?</label>
              <div className="input-group compact">
                <span className="currency-prefix">Rs.</span>
                <input
                  type="number"
                  className="money-input"
                  placeholder="100"
                  min="1"
                  value={saveAmount}
                  onChange={(e) => setSaveAmount(e.target.value)}
                  disabled={saving}
                />
              </div>

              {/* Quick amount buttons */}
              <div className="quick-amounts">
                {[50, 100, 200, 500].filter(v => v <= balance).map((v) => (
                  <button
                    key={v}
                    type="button"
                    className="quick-btn"
                    onClick={() => setSaveAmount(String(v))}
                  >
                    Rs. {v}
                  </button>
                ))}
              </div>

              {saveError && <p className="error-text">{saveError}</p>}

              <button type="submit" className="primary-btn save-action" disabled={saving}>
                {saving ? 'Save ho raha hai...' : 'Save Karein!'}
              </button>
            </form>
          )}

          {/* Result message */}
          {saveResult && (
            <div className="result-card">
              <p className="result-message">{saveResult.message}</p>
              <p className="result-hint">
                Thora thora save karne se aap apne bade goals ko achieve kar sakte ho.
              </p>
            </div>
          )}

          {/* Goal completed banner */}
          {activeGoal.status === 'completed' && (
            <div className="completed-banner">
              🎉 Mubarak ho! Goal complete ho gaya!
            </div>
          )}
        </div>
      )}

      {/* Completed Goals History */}
      {goals.filter((g) => g.status === 'completed').length > 0 && (
        <div className="section-card">
          <h3 className="section-subtitle">Complete Goals</h3>
          {goals
            .filter((g) => g.status === 'completed')
            .map((g) => (
              <div key={g.id} className="completed-goal">
                <span>✅ {g.name}</span>
                <span>Rs. {parseFloat(g.target_amount).toLocaleString()}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
