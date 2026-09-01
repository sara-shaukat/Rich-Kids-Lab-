import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getQuests, resolveQuest, submitQuestReflection } from '../services/api';
import Mascot from '../components/Mascot';

const STORAGE_KEY = 'rkl_child_id';

export default function Quests() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [quests, setQuests] = useState([]);
  const [activeQuest, setActiveQuest] = useState(null);
  const [result, setResult] = useState(null);
  const [reflectAnswer, setReflectAnswer] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const childId = localStorage.getItem(STORAGE_KEY);

  const loadQuests = async () => {
    try {
      const data = await getQuests(childId);
      setQuests(data.quests || []);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (!childId) { navigate('/'); return; }
    loadQuests();
  }, []);

  const handleChoice = async (choice) => {
    setBusy(true);
    setError('');
    try {
      const res = await resolveQuest(childId, activeQuest.id, choice.id);
      setResult(res);
      setReflectAnswer(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleReflect = async (option) => {
    setReflectAnswer(option.id);
    setBusy(true);
    try {
      const res = await submitQuestReflection(childId, result.quest_id, option.id);
      setResult((prev) => ({
        ...prev,
        botLine: res.bot_line,
      }));
    } catch {
      // Save failed — still show the bot line locally (reflection is never graded)
      setResult((prev) => ({
        ...prev,
        botLine: option.bot_line,
      }));
    } finally {
      setBusy(false);
    }
  };

  const handleDone = () => {
    setResult(null);
    setActiveQuest(null);
    setReflectAnswer(null);
    setError('');
    setLoading(true);
    loadQuests();
  };

  if (!childId) return null;

  if (loading) {
    return <div className="page-container"><p className="loading-text">Load ho raha hai...</p></div>;
  }

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          ← Wapas
        </button>
        <h1 className="page-title">🗺️ QUESTS</h1>
      </div>

      {error && (
        <p className="error-text" style={{ background: 'white', padding: '0.8rem', borderRadius: '10px' }}>
          {error}
        </p>
      )}

      {/* ---- Reflection Screen (after a quest resolves) ---- */}
      {result ? (
        <div className="section-card quest-reflection">
          <div className={`quest-verdict quest-verdict-${result.verdict}`}>
            {result.verdict === 'win' ? '✅' : '💡'} {result.headline}
          </div>

          <h3 className="quest-section-label">Yahan kya hua</h3>
          <div className="quest-what-happened">
            {result.what_happened.map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>

          <h3 className="quest-section-label">{result.reflection.question}</h3>
          <div className="quest-reflect-options">
            {result.reflection.options.map((opt) => (
              <button
                key={opt.id}
                className={`quest-reflect-option ${reflectAnswer === opt.id ? 'selected' : ''}`}
                onClick={() => handleReflect(opt)}
                disabled={busy}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {result.botLine && (
            <Mascot line={result.botLine} mode="hype" size="small" />
          )}

          <div className="quest-meta">
            <span>Naya balance: <strong>Rs. {parseFloat(result.wallet_balance).toLocaleString()}</strong></span>
            {result.goal_name && (
              <span>
                {result.goal_name}: Rs. {parseFloat(result.goal_saved_amount).toLocaleString()} / Rs. {parseFloat(result.goal_target_amount).toLocaleString()}
                {result.goal_status === 'completed' ? ' ✅' : ''}
              </span>
            )}
          </div>

          <div className="spend-actions">
            <button className="primary-btn" onClick={handleDone}>
              Done — Quests par Wapas
            </button>
          </div>
        </div>
      ) : activeQuest ? (
        /* ---- Decision Card ---- */
        <div className="section-card quest-decision">
          <button className="quest-back-link" onClick={() => setActiveQuest(null)}>
            ← Quests
          </button>

          <div className="quest-title-row">
            <span className="quest-big-icon">{activeQuest.icon}</span>
            <div>
              <h2 className="quest-title">{activeQuest.title}</h2>
              <span className="quest-concept-tag">{activeQuest.concept}</span>
            </div>
          </div>

          <div className="quest-scenario">
            {activeQuest.scenario_lines.map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>

          <div className="quest-choices">
            {activeQuest.choices.map((choice) => (
              <button
                key={choice.id}
                className="quest-choice"
                onClick={() => handleChoice(choice)}
                disabled={busy}
              >
                <span className="quest-choice-label">{choice.label}</span>
                <span className="quest-choice-sub">{choice.sub}</span>
              </button>
            ))}
          </div>
          {busy && <p className="quest-busy">Quest resolve ho raha hai...</p>}
        </div>
      ) : (
        /* ---- Quest Slots List ---- */
        <>
          <div className="quest-intro">
            <p>Har quest mein EK mushkil faisla hota hai — 90 second se kam!</p>
          </div>

          {quests.map((q) => {
            if (q.status === 'available') {
              return (
                <button
                  key={q.id}
                  className="quest-slot quest-available"
                  onClick={() => setActiveQuest(q)}
                >
                  <span className="quest-slot-icon">{q.icon}</span>
                  <span className="quest-slot-text">
                    <span className="quest-slot-title">{q.title}</span>
                    <span className="quest-slot-sub">{q.concept} • ~1 minute</span>
                  </span>
                  <span className="quest-slot-arrow">→</span>
                </button>
              );
            }
            if (q.status === 'locked') {
              return (
                <div key={q.id} className="quest-slot quest-locked">
                  <span className="quest-slot-icon">🔒</span>
                  <span className="quest-slot-text">
                    <span className="quest-slot-title">{q.title}</span>
                    <span className="quest-slot-sub">{q.lock_reason}</span>
                  </span>
                </div>
              );
            }
            return (
              <div key={q.id} className="quest-slot quest-completed">
                <span className="quest-slot-icon">{q.verdict === 'win' ? '✅' : '💡'}</span>
                <span className="quest-slot-text">
                  <span className="quest-slot-title">{q.title}</span>
                  <span className="quest-slot-sub">{q.headline}</span>
                </span>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
