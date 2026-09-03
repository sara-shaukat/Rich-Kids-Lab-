import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  getVaultLevelQuests,
  resolveVaultQuest,
  submitVaultReflection,
  getVaultChallenge,
  submitVaultChallenge,
  getLevel1Goal,
  completeLevel1,
  createGoal,
} from '../services/api';

const STORAGE_KEY = 'rkl_child_id';

/* Preset goal options for Level 1 setup */
const GOAL_PRESETS = [
  { id: 'football',   icon: '⚽', name: 'New Football',     amount: 2000 },
  { id: 'headphones', icon: '🎧', name: 'Headphones',       amount: 3000 },
  { id: 'art',        icon: '🎨', name: 'Art Supplies',     amount: 1500 },
  { id: 'game',       icon: '🎮', name: 'Video Game',       amount: 2500 },
  { id: 'bicycle',    icon: '🚲', name: 'Bicycle',          amount: 5000 },
];

/* Level 1 reflection options */
const LEVEL1_REFLECTION = [
  { id: 'saved',     icon: '💰', label: 'I saved regularly' },
  { id: 'earned',    icon: '💵', label: 'I earned more money' },
  { id: 'careful',   icon: '🧠', label: 'I made careful spending choices' },
  { id: 'mistake',   icon: '📝', label: 'I learned from a mistake' },
  { id: 'different', icon: '🔀', label: 'I used my money in different ways' },
];

export default function VaultLevel() {
  const navigate = useNavigate();
  const { level } = useParams();
  const levelNum = parseInt(level, 10);
  const isLevel1 = levelNum === 1;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // ── Level 1 state ──────────────────────────────────
  const [goalData, setGoalData] = useState(null);       // { has_goal, goal, level_complete, reflection_done }
  const [goalScreen, setGoalScreen] = useState(null);   // 'setup' | 'dashboard' | 'reflection' | 'complete' | 'level_done'
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [customName, setCustomName] = useState('');
  const [customAmount, setCustomAmount] = useState('');
  const [isCustom, setIsCustom] = useState(false);
  const [goalCreating, setGoalCreating] = useState(false);
  const [completingLevel, setCompletingLevel] = useState(false);

  // ── Quest state (levels 2-8) ───────────────────────
  const [quests, setQuests] = useState([]);
  const [currentQuest, setCurrentQuest] = useState(null);
  const [outcome, setOutcome] = useState(null);
  const [botLine, setBotLine] = useState('');
  const [resolving, setResolving] = useState(false);

  // ── Challenge state (levels 2-8) ───────────────────
  const [challengeMode, setChallengeMode] = useState(null);
  const [challenge, setChallenge] = useState(null);
  const [challengeAnswers, setChallengeAnswers] = useState({});
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0);
  const [challengeResult, setChallengeResult] = useState(null);

  const childId = localStorage.getItem(STORAGE_KEY);

  useEffect(() => {
    if (!childId) { navigate('/'); return; }
    if (isLevel1) loadGoalStatus();
    else loadQuests();
  }, [childId, levelNum]);

  // ── Level 1: load goal status ─────────────────────
  const loadGoalStatus = async () => {
    setLoading(true);
    try {
      const data = await getLevel1Goal(childId);
      setGoalData(data);
      if (data.level_complete && data.reflection_done) {
        setGoalScreen('level_done');
      } else if (data.has_goal && data.goal?.goal_reached) {
        setGoalScreen('reflection');
      } else if (data.has_goal) {
        setGoalScreen('dashboard');
      } else {
        setGoalScreen('setup');
      }
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  // ── Level 1: create goal ──────────────────────────
  const handleSetupGoal = async () => {
    setGoalCreating(true);
    try {
      let name, amount;
      if (isCustom) {
        name = customName.trim();
        amount = parseFloat(customAmount);
        if (!name) throw new Error('Goal ka naam likho!');
        if (!amount || amount <= 0) throw new Error('Target amount sahi likho!');
      } else if (selectedPreset) {
        name = selectedPreset.name;
        amount = selectedPreset.amount;
      } else {
        throw new Error('Ek goal select karo!');
      }
      await createGoal(childId, name, amount);
      await loadGoalStatus();
    } catch (err) {
      setError(err.message);
    }
    setGoalCreating(false);
  };

  // ── Level 1: submit reflection ────────────────────
  const handleLevel1Reflection = async (answerId) => {
    setCompletingLevel(true);
    try {
      await completeLevel1(childId, answerId);
      setGoalScreen('complete');
    } catch (err) {
      setError(err.message);
    }
    setCompletingLevel(false);
  };

  // ── Quest handlers (levels 2-8) ───────────────────
  const loadQuests = async () => {
    setLoading(true);
    try {
      const data = await getVaultLevelQuests(childId, levelNum);
      setQuests(data.quests || []);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const handleChoice = async (quest, choiceId) => {
    setResolving(true);
    try {
      const result = await resolveVaultQuest(childId, levelNum, quest.id, choiceId);
      setOutcome(result);
      setCurrentQuest(null);
    } catch (err) {
      setError(err.message);
    }
    setResolving(false);
  };

  const handleReflection = async (answerId) => {
    try {
      const result = await submitVaultReflection(childId, outcome.quest_id, answerId);
      setBotLine(result.bot_line);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleContinue = () => {
    setOutcome(null);
    setBotLine('');
    loadQuests();
  };

  // ── Challenge handlers (levels 2-8) ───────────────
  const startChallenge = async () => {
    try {
      const data = await getVaultChallenge(childId, levelNum);
      setChallenge(data);
      setChallengeAnswers({});
      setCurrentQuestionIdx(0);
      setChallengeMode('questions');
      setChallengeResult(null);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleChallengeAnswer = (questionId, answerId) => {
    setChallengeAnswers(prev => ({ ...prev, [questionId]: answerId }));
    const questions = challenge.questions;
    if (currentQuestionIdx < questions.length - 1) {
      setTimeout(() => setCurrentQuestionIdx(prev => prev + 1), 300);
    }
  };

  const handleSubmitChallenge = async () => {
    try {
      const result = await submitVaultChallenge(childId, levelNum, challengeAnswers);
      setChallengeResult(result);
      setChallengeMode('results');
    } catch (err) {
      setError(err.message);
    }
  };

  // ── Loading / Error ───────────────────────────────
  if (loading) {
    return <div className="page-container"><p className="loading-text">
      {isLevel1 ? 'Goal load ho raha hai...' : 'Quests load ho rahe hain...'}
    </p></div>;
  }

  if (error) {
    return (
      <div className="page-container">
        <p className="error-text">{error}</p>
        <button className="back-btn" onClick={() => navigate('/vault')}>← Vault Map</button>
      </div>
    );
  }

  // ════════════════════════════════════════════════════
  //  LEVEL 1 — YOUR FIRST GOAL
  // ════════════════════════════════════════════════════

  if (isLevel1) {

    // ── Level already complete ──────────────────────
    if (goalScreen === 'level_done') {
      return (
        <div className="vl-page">
          <nav className="vl-nav"><button className="vl-back" onClick={() => navigate('/vault')}>← Vault Map</button></nav>
          <div className="vl-done-screen">
            <div className="vl-done-badge">
              <span className="vl-done-icon">🏆</span>
              <h2 className="vl-done-title">Level 1 Complete</h2>
              <p className="vl-done-sub">Aapne apna pehla financial goal poora kiya!</p>
            </div>
            <p className="vl-unlock-msg">🔓 Challenge 2 is now unlocked.</p>
            <button className="vl-cta" onClick={() => navigate('/vault')}>Go to Vault Map →</button>
            <button className="vl-cert-btn" onClick={() => navigate(`/certificate/${childId}`)}>📜 View Certificate</button>
            <button className="vl-report-btn" onClick={() => navigate(`/reportcard/${childId}`)}>📊 Money Report Card</button>
          </div>
        </div>
      );
    }

    // ── Celebration after reflection ────────────────
    if (goalScreen === 'complete') {
      return (
        <div className="vl-page">
          <nav className="vl-nav"><button className="vl-back" onClick={() => navigate('/vault')}>← Vault Map</button></nav>
          <div className="vl-done-screen">
            <div className="vl-celebration">
              <span className="vl-confetti">🎉</span>
              <h1 className="vl-celebration-title">GOAL COMPLETE!</h1>
              <div className="vl-celebration-lines">
                <p>You made the decisions.</p>
                <p>You experienced the consequences.</p>
                <p>And you reached your goal.</p>
              </div>
            </div>
            <div className="vl-done-badge">
              <span className="vl-done-icon">🏆</span>
              <h2 className="vl-done-title">LEVEL 1 COMPLETE</h2>
            </div>
            <p className="vl-unlock-msg">🔓 Challenge 2 is now unlocked.</p>
            <button className="vl-cta" onClick={() => navigate('/vault')}>Go to Vault Map →</button>
            <button className="vl-cert-btn" onClick={() => navigate(`/certificate/${childId}`)}>📜 View Certificate</button>
            <button className="vl-report-btn" onClick={() => navigate(`/reportcard/${childId}`)}>📊 Money Report Card</button>
          </div>
        </div>
      );
    }

    // ── Reflection screen ───────────────────────────
    if (goalScreen === 'reflection') {
      return (
        <div className="vl-page">
          <nav className="vl-nav"><button className="vl-back" onClick={() => navigate('/vault')}>← Vault Map</button></nav>
          <div className="vl-reflect-screen">
            <div className="vl-reflect-banner">
              <span className="vl-reflect-icon">🎯</span>
              <h2 className="vl-reflect-title">GOAL REACHED!</h2>
              <p className="vl-reflect-name">{goalData.goal.name}</p>
              <p className="vl-reflect-amount">
                Rs. {goalData.goal.saved_amount.toLocaleString()} / Rs. {goalData.goal.target_amount.toLocaleString()}
              </p>
            </div>

            <div className="vl-reflect-card">
              <h3 className="vl-reflect-question">What helped you reach your goal?</h3>
              <p className="vl-reflect-hint">Apni journey ke baare mein socho...</p>
              <div className="vl-reflect-options">
                {LEVEL1_REFLECTION.map(opt => (
                  <button
                    key={opt.id}
                    className="vl-reflect-btn"
                    disabled={completingLevel}
                    onClick={() => handleLevel1Reflection(opt.id)}
                  >
                    <span className="vl-reflect-btn-icon">{opt.icon}</span>
                    <span className="vl-reflect-btn-label">{opt.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      );
    }

    // ── Goal setup ──────────────────────────────────
    if (goalScreen === 'setup') {
      return (
        <div className="vl-page">
          <div className="vl-setup">
            <nav className="vl-nav"><button className="vl-back" onClick={() => navigate('/vault')}>← Vault Map</button></nav>

            <div className="vl-setup-intro">
              <span className="vl-level-tag">LEVEL 1</span>
              <h1 className="vl-setup-title">Your First Goal</h1>
              <p className="vl-setup-desc">
                Choose something you want to save for. Then use your money skills to reach it.
              </p>
            </div>

            <h2 className="vl-setup-question">What are you saving for?</h2>

            <div className="vl-presets">
              {GOAL_PRESETS.map(g => (
                <button
                  key={g.id}
                  className={`vl-preset ${selectedPreset?.id === g.id && !isCustom ? 'active' : ''}`}
                  onClick={() => { setSelectedPreset(g); setIsCustom(false); }}
                >
                  <span className="vl-preset-icon">{g.icon}</span>
                  <span className="vl-preset-name">{g.name}</span>
                  <span className="vl-preset-amount">Rs. {g.amount.toLocaleString()}</span>
                </button>
              ))}
              <button
                className={`vl-preset vl-preset-custom ${isCustom ? 'active' : ''}`}
                onClick={() => setIsCustom(true)}
              >
                <span className="vl-preset-icon">✨</span>
                <span className="vl-preset-name">Something I choose</span>
                <span className="vl-preset-amount">Custom</span>
              </button>
            </div>

            {isCustom && (
              <div className="vl-custom-form">
                <div className="vl-field">
                  <label>Goal Name</label>
                  <input
                    type="text"
                    placeholder="e.g., Nintendo Switch"
                    value={customName}
                    onChange={e => setCustomName(e.target.value)}
                    maxLength={50}
                  />
                </div>
                <div className="vl-field">
                  <label>Target Amount (Rs.)</label>
                  <input
                    type="number"
                    placeholder="e.g., 3000"
                    value={customAmount}
                    onChange={e => setCustomAmount(e.target.value)}
                    min={100}
                    max={50000}
                  />
                </div>
              </div>
            )}

            <button
              className="vl-setup-btn"
              disabled={goalCreating || (!selectedPreset && !isCustom) || (isCustom && (!customName.trim() || !customAmount))}
              onClick={handleSetupGoal}
            >
              {goalCreating ? 'Setting up...' : 'Set My Goal →'}
            </button>
          </div>
        </div>
      );
    }

    // ── Goal dashboard (active goal) ────────────────
    if (goalScreen === 'dashboard' && goalData?.goal) {
      const goal = goalData.goal;
      const pct = Math.min(goal.progress_pct, 100);

      // Journey milestones based on existing data
      const milestones = [
        { label: 'Goal created', done: true },
        { label: 'First money saved', done: goal.saved_amount > 0 },
        { label: 'Keep making decisions', done: pct >= 50 },
        { label: 'Goal reached', done: pct >= 100 },
      ];

      return (
        <div className="vl-page">
          {/* 1. Top Navigation */}
          <nav className="vl-nav">
            <button className="vl-back" onClick={() => navigate('/vault')}>← Vault Map</button>
            <div className="vl-nav-right">
              <button className="vl-refresh" onClick={loadGoalStatus}>↻ Check my progress</button>
            </div>
          </nav>

          {/* Level label */}
          <div className="vl-header">
            <span className="vl-level-tag">LEVEL 1</span>
            <h1 className="vl-page-title">FIRST GOAL</h1>
          </div>

          {/* 2. Hero Goal Card */}
          <div className="vl-hero">
            <div className="vl-hero-label">YOUR MISSION</div>
            <div className="vl-hero-icon">{GOAL_PRESETS.find(p => p.name === goal.name)?.icon || '🎯'}</div>
            <h2 className="vl-hero-name">{goal.name}</h2>

            <div className="vl-hero-amounts">
              <span className="vl-hero-saved">Rs. {goal.saved_amount.toLocaleString()}</span>
              <span className="vl-hero-sep"> / </span>
              <span className="vl-hero-target">Rs. {goal.target_amount.toLocaleString()}</span>
            </div>

            {/* Journey progress bar */}
            <div className="vl-journey-bar">
              <div className="vl-journey-track">
                <div className="vl-journey-fill" style={{ width: `${pct}%` }} />
                <div className="vl-journey-marker" style={{ left: `${pct}%` }}>
                  <span className="vl-journey-dot" />
                </div>
              </div>
              <div className="vl-journey-labels">
                <span className="vl-journey-start">START</span>
                <span className="vl-journey-pct">{pct}% COMPLETE</span>
                <span className="vl-journey-end">🏆 GOAL</span>
              </div>
            </div>
          </div>

          {/* 3. Mission Text */}
          <div className="vl-mission">
            <h3 className="vl-mission-heading">How will you get there?</h3>
            <p className="vl-mission-text">Every money decision changes your journey.</p>
          </div>

          {/* 4. Action Cards */}
          <div className="vl-actions">
            <button className="vl-action vl-action-save" onClick={() => navigate('/save')}>
              <span className="vl-action-icon">💰</span>
              <div className="vl-action-body">
                <span className="vl-action-title">SAVE</span>
                <span className="vl-action-desc">Put money toward your goal</span>
              </div>
              <span className="vl-action-arrow">→</span>
            </button>

            <button className="vl-action vl-action-spend" onClick={() => navigate('/spend')}>
              <span className="vl-action-icon">🛍️</span>
              <div className="vl-action-body">
                <span className="vl-action-title">SPEND</span>
                <span className="vl-action-desc">Make a choice and see the trade-off</span>
              </div>
              <span className="vl-action-arrow">→</span>
            </button>

            <button className="vl-action vl-action-grow" onClick={() => navigate('/grow')}>
              <span className="vl-action-icon">📈</span>
              <div className="vl-action-body">
                <span className="vl-action-title">GROW</span>
                <span className="vl-action-desc">Try to make your money grow</span>
              </div>
              <span className="vl-action-arrow">→</span>
            </button>

            <button className="vl-action vl-action-give" onClick={() => navigate('/give')}>
              <span className="vl-action-icon">💝</span>
              <div className="vl-action-body">
                <span className="vl-action-title">GIVE</span>
                <span className="vl-action-desc">Help someone while balancing your goal</span>
              </div>
              <span className="vl-action-arrow">→</span>
            </button>
          </div>

          {/* 5. Money Lab — Star Action */}
          <div className="vl-lab" onClick={() => navigate('/lab')} role="button" tabIndex={0}>
            <div className="vl-lab-left">
              <span className="vl-lab-icon">🧪</span>
            </div>
            <div className="vl-lab-body">
              <span className="vl-lab-tag">MONEY LAB</span>
              <h3 className="vl-lab-title">Start a business. Make decisions. See what happens.</h3>
              <p className="vl-lab-sub">Your choices can make or lose money.</p>
            </div>
            <span className="vl-lab-cta">TRY MONEY LAB →</span>
          </div>

          {/* 6. Goal Journey Timeline */}
          <div className="vl-timeline">
            <h3 className="vl-timeline-heading">YOUR JOURNEY</h3>
            <div className="vl-timeline-track">
              {milestones.map((m, i) => (
                <div key={i} className={`vl-timeline-step ${m.done ? 'done' : ''}`}>
                  <div className="vl-timeline-dot" />
                  {i < milestones.length - 1 && <div className="vl-timeline-line" />}
                  <span className="vl-timeline-label">{m.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      );
    }
  }

  // ════════════════════════════════════════════════════
  //  LEVELS 2-8 — QUEST + CHALLENGE FLOW (unchanged)
  // ════════════════════════════════════════════════════

  const pendingQuests = quests.filter(q => !q.is_done);
  const doneQuests = quests.filter(q => q.is_done);
  const allQuestsDone = pendingQuests.length === 0 && quests.length > 0;

  // Challenge questions screen
  if (challengeMode === 'questions' && challenge) {
    const question = challenge.questions[currentQuestionIdx];
    const totalQuestions = challenge.questions.length;
    const allAnswered = Object.keys(challengeAnswers).length === totalQuestions;
    const currentAnswered = challengeAnswers[question.id];

    return (
      <div className="vault-level-container">
        <div className="vault-level-outcome challenge-screen">
          <div className="challenge-header">
            <h2 className="challenge-title">🏆 {challenge.title}</h2>
            <p className="challenge-progress">
              Question {currentQuestionIdx + 1} of {totalQuestions}
            </p>
          </div>

          <div className="challenge-question">
            <p className="challenge-question-text">{question.question}</p>
            <div className="challenge-options">
              {question.options.map(opt => (
                <button
                  key={opt.id}
                  className={`challenge-option ${currentAnswered === opt.id ? 'selected' : ''}`}
                  onClick={() => handleChallengeAnswer(question.id, opt.id)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="challenge-dots">
            {challenge.questions.map((q, i) => (
              <span
                key={q.id}
                className={`challenge-dot ${i === currentQuestionIdx ? 'active' : ''} ${challengeAnswers[q.id] ? 'answered' : ''}`}
              />
            ))}
          </div>

          {allAnswered ? (
            <button className="vault-continue-btn" onClick={handleSubmitChallenge}>
              Submit Answers ✓
            </button>
          ) : (
            <p className="challenge-hint">Sab questions ke jawab do!</p>
          )}
        </div>
      </div>
    );
  }

  // Challenge results screen
  if (challengeMode === 'results' && challengeResult) {
    return (
      <div className="vault-level-container">
        <div className="vault-level-outcome challenge-screen">
          {challengeResult.passed ? (
            <div className="challenge-result-header passed">
              <span className="result-icon">🎉</span>
              <h2>Challenge Passed!</h2>
              <p className="result-score">
                {challengeResult.correct}/{challengeResult.total} correct — {challengeResult.score}%
              </p>
            </div>
          ) : (
            <div className="challenge-result-header failed">
              <span className="result-icon">📝</span>
              <h2>Almost There!</h2>
              <p className="result-score">
                {challengeResult.correct}/{challengeResult.total} correct — {challengeResult.pass_threshold || 2} needed to pass
              </p>
              <p className="result-retry-hint">Koi baat nahi — phir se try karo!</p>
            </div>
          )}

          <div className="challenge-results-list">
            {challengeResult.results.map((r, i) => (
              <div key={r.question_id} className={`challenge-result-item ${r.correct ? 'correct' : 'incorrect'}`}>
                <div className="result-item-header">
                  <span className="result-item-icon">{r.correct ? '✅' : '❌'}</span>
                  <span className="result-item-question">Q{i + 1}: {r.question}</span>
                </div>
                <p className="result-item-answer">Aapka jawab: {r.your_answer}</p>
                <p className="result-item-explanation">{r.explanation}</p>
              </div>
            ))}
          </div>

          {challengeResult.passed && challengeResult.level_complete && (
            <div className="level-complete-celebration">
              <p className="celebration-text">🏆 Level {levelNum} Complete! Level {challengeResult.level_unlocked} Unlocked! 🏆</p>
            </div>
          )}

          <div className="challenge-result-actions">
            {challengeResult.passed ? (
              <button className="vault-continue-btn" onClick={() => navigate('/vault')}>
                Go to Map →
              </button>
            ) : (
              <button className="vault-continue-btn" onClick={startChallenge}>
                Try Again →
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Quest outcome screen
  if (outcome) {
    return (
      <div className="vault-level-container">
        <div className="vault-level-outcome">
          <div className={`outcome-header outcome-${outcome.verdict}`}>
            <span className="outcome-icon">{outcome.was_wise ? '🌟' : '💭'}</span>
            <h2 className="outcome-headline">{outcome.headline}</h2>
          </div>

          <div className="outcome-body">
            {outcome.outcome_lines.map((line, i) => (
              <p key={i} className="outcome-line">{line}</p>
            ))}
          </div>

          {!botLine && outcome.reflection && (
            <div className="reflection-section">
              <h3 className="reflection-question">{outcome.reflection.question}</h3>
              <div className="reflection-options">
                {outcome.reflection.options.map(opt => (
                  <button
                    key={opt.id}
                    className="reflection-btn"
                    onClick={() => handleReflection(opt.id)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {botLine && (
            <div className="bot-response">
              <p className="bot-line">{botLine}</p>
            </div>
          )}

          <button className="vault-continue-btn" onClick={handleContinue}>
            Continue →
          </button>
        </div>
      </div>
    );
  }

  // Quest selection or quest scenario
  return (
    <div className="vault-level-container">
      <div className="vault-level-header">
        <button className="back-btn" onClick={() => navigate('/vault')}>← Vault Map</button>
        <h1 className="vault-level-title">Level {levelNum} Quests</h1>
      </div>

      {currentQuest ? (
        <div className="quest-scenario">
          <div className="quest-header">
            <span className="quest-icon">{currentQuest.icon}</span>
            <h2 className="quest-title">{currentQuest.title}</h2>
            <span className="quest-concept">{currentQuest.concept}</span>
          </div>

          <div className="scenario-lines">
            {currentQuest.scenario_lines.map((line, i) => (
              <p key={i} className="scenario-line">{line}</p>
            ))}
          </div>

          <div className="quest-choices">
            <h3>Kya karo ge?</h3>
            {currentQuest.choices.map(choice => (
              <button
                key={choice.id}
                className="choice-btn"
                disabled={resolving}
                onClick={() => handleChoice(currentQuest, choice.id)}
              >
                <span className="choice-label">{choice.label}</span>
                {choice.sub && <span className="choice-sub">{choice.sub}</span>}
              </button>
            ))}
          </div>

          <button className="back-to-quests" onClick={() => setCurrentQuest(null)}>
            ← Wapas
          </button>
        </div>
      ) : (
        <div className="quest-list">
          {/* Quest progress header */}
          <div className="vault-quest-progress">
            <div className="vault-quest-progress-info">
              <span className="vault-quest-progress-label">Quest Progress</span>
              <span className="vault-quest-progress-count">{doneQuests.length}/{quests.length}</span>
            </div>
            <div className="vault-quest-progress-bar">
              <div
                className="vault-quest-progress-fill"
                style={{ width: `${quests.length ? (doneQuests.length / quests.length) * 100 : 0}%` }}
              />
            </div>
            {allQuestsDone && (
              <p className="vault-quest-progress-done">Sab quests complete! 🎉 Ab challenge unlock ho gaya!</p>
            )}
          </div>

          {pendingQuests.length > 0 && (
            <div className="quest-section">
              <h3>🎯 Available Quests ({pendingQuests.length} remaining)</h3>
              {pendingQuests.map(quest => (
                <button
                  key={quest.id}
                  className="quest-card"
                  onClick={() => setCurrentQuest(quest)}
                >
                  <span className="quest-card-icon">{quest.icon}</span>
                  <div className="quest-card-info">
                    <span className="quest-card-title">{quest.title}</span>
                    <span className="quest-card-concept">{quest.concept}</span>
                  </div>
                  <span className="quest-card-arrow">→</span>
                </button>
              ))}
            </div>
          )}

          {doneQuests.length > 0 && (
            <div className="quest-section">
              <h3>Completed Quests ({doneQuests.length}/{quests.length})</h3>
              {doneQuests.map(quest => (
                <div key={quest.id} className="quest-card quest-done">
                  <span className="quest-card-icon">{quest.icon}</span>
                  <div className="quest-card-info">
                    <span className="quest-card-title">{quest.title}</span>
                    <span className="quest-card-done">✅ Done</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Challenge entry button */}
          {allQuestsDone && (
            <div className="challenge-entry">
              <button className="challenge-start-btn" onClick={startChallenge}>
                <span className="challenge-start-icon">🏆</span>
                <span className="challenge-start-text">Level Challenge Shuru Karo!</span>
              </button>
            </div>
          )}

          {quests.length === 0 && (
            <div className="no-quests">
              <p>No quests available for this level yet.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
