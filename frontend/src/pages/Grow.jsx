import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDashboard, getGrowTemplates, startBusiness, invest, exploreSkill, generateAIIdeas, startAIBusiness } from '../services/api';

const STORAGE_KEY = 'rkl_child_id';

export default function Grow() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState(null);
  const [templates, setTemplates] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('business');
  const [error, setError] = useState('');

  // Business state — multi-step flow: 'interests' → 'businesses' → 'result'
  const [businessStep, setBusinessStep] = useState('interests');
  const [selectedInterests, setSelectedInterests] = useState([]);
  const [recommendResult, setRecommendResult] = useState(null);
  const [businessResult, setBusinessResult] = useState(null);
  const [businessLoading, setBusinessLoading] = useState(false);

  // Investment state — multi-step: 'intro' → 'select' → 'confirm' → 'result' → 'diversify'
  const [investStep, setInvestStep] = useState('intro');
  const [investOption, setInvestOption] = useState(null);
  const [investAmount, setInvestAmount] = useState('');
  const [investResult, setInvestResult] = useState(null);
  const [investLoading, setInvestLoading] = useState(false);
  const [diversifyAnswer, setDiversifyAnswer] = useState(null);

  // Skill Lab state — 4-step: 'pick' → 'discover' → 'challenge' → 'connect'
  const [skillStep, setSkillStep] = useState('pick');
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [challengeAnswer, setChallengeAnswer] = useState(null);
  const [practiceText, setPracticeText] = useState('');
  const [skillResult, setSkillResult] = useState(null);
  const [skillLoading, setSkillLoading] = useState(false);

  const childId = localStorage.getItem(STORAGE_KEY);

  const loadData = async () => {
    if (!childId) { navigate('/'); return; }
    try {
      const [dash, tmpl] = await Promise.all([
        getDashboard(childId),
        getGrowTemplates(childId),
      ]);
      if (!dash) { localStorage.removeItem(STORAGE_KEY); navigate('/'); return; }
      setDashboard(dash);
      setTemplates(tmpl);
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

  // ---- Business: interest toggle ----
  const toggleInterest = (interestId) => {
    setSelectedInterests((prev) =>
      prev.includes(interestId) ? prev.filter((i) => i !== interestId) : [...prev, interestId]
    );
  };

  // ---- Business: get AI-generated ideas ----
  const handleGetRecommendations = async () => {
    setBusinessLoading(true);
    setError('');
    try {
      const result = await generateAIIdeas(childId, selectedInterests);
      if (result.ideas && result.ideas.length > 0) {
        // Transform AI ideas to match the expected format
        const aiBusinesses = result.ideas.map(idea => ({
          ...idea,
          ai_generated: true,
          affordable: true, // AI already filters by budget
          match_score: 1, // All AI ideas are "recommended"
        }));
        setRecommendResult({ business: aiBusinesses, message: result.message });
      } else {
        // Fallback to standard templates if AI fails
        setRecommendResult({ business: [], message: result.message || 'AI ideas available nahi hain. Standard templates try karein!' });
      }
      setBusinessStep('businesses');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusinessLoading(false);
    }
  };

  // ---- Business: start simulation ----
  const handleBusiness = async (business) => {
    setBusinessLoading(true);
    setError('');
    try {
      // Check if this is an AI-generated idea or standard template
      if (business.ai_generated || business.description.includes('AI-generated')) {
        // AI-generated business
        const result = await startAIBusiness(childId, business);
        setBusinessResult(result);
      } else {
        // Standard template
        const result = await startBusiness(childId, business.id);
        setBusinessResult(result);
      }
      setBusinessStep('result');
      await refreshDashboard();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusinessLoading(false);
    }
  };

  // ---- Business: reset flow ----
  const resetBusinessFlow = () => {
    setBusinessStep('interests');
    setSelectedInterests([]);
    setRecommendResult(null);
    setBusinessResult(null);
  };

  // ---- Investment ----
  const handleInvestConfirm = async () => {
    const amount = parseFloat(investAmount);
    if (isNaN(amount) || amount <= 0) { setError('Amount 0 se zyada hona chahiye.'); return; }
    if (amount > balance) { setError(`Aapke paas sirf Rs. ${balance} hain.`); return; }
    setInvestLoading(true);
    setError('');
    try {
      const result = await invest(childId, amount, investOption.id);
      setInvestResult(result);
      setInvestStep('result');
      await refreshDashboard();
    } catch (err) {
      setError(err.message);
    } finally {
      setInvestLoading(false);
    }
  };

  const resetInvestFlow = () => {
    setInvestStep('intro');
    setInvestOption(null);
    setInvestAmount('');
    setInvestResult(null);
    setDiversifyAnswer(null);
  };

  // ---- Skill Lab ----
  const handleSkillSelect = (skill) => {
    setSelectedSkill(skill);
    setChallengeAnswer(null);
    setPracticeText('');
    setSkillResult(null);
    setSkillStep('discover');
  };

  const handleSkillChallengeSubmit = async () => {
    if (!challengeAnswer) { setError('Ek option select karein.'); return; }
    setSkillLoading(true);
    setError('');
    try {
      const result = await exploreSkill(
        childId,
        selectedSkill.id,
        null,
        challengeAnswer,
        practiceText || null,
      );
      setSkillResult(result);
      setSkillStep('connect');
      await refreshDashboard();
    } catch (err) {
      setError(err.message);
    } finally {
      setSkillLoading(false);
    }
  };

  const resetSkillFlow = () => {
    setSkillStep('pick');
    setSelectedSkill(null);
    setChallengeAnswer(null);
    setPracticeText('');
    setSkillResult(null);
  };

  if (loading || !dashboard || !templates) {
    return <div className="page-container"><p className="loading-text">Load ho raha hai...</p></div>;
  }

  const balance = parseFloat(dashboard.balance);

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>← Wapas</button>
        <h1 className="page-title">🌱 GROW</h1>
      </div>

      {/* Balance */}
      <div className="info-card">
        <span className="info-label">Aapka Balance</span>
        <span className="info-value">Rs. {balance.toLocaleString()}</span>
      </div>

      {error && <p className="error-text" style={{ background: 'white', padding: '0.8rem', borderRadius: '10px' }}>{error}</p>}

      {/* Tabs */}
      <div className="grow-tabs">
        <button className={`grow-tab ${activeTab === 'business' ? 'active' : ''}`} onClick={() => { setActiveTab('business'); setError(''); }}>Business</button>
        <button className={`grow-tab ${activeTab === 'invest' ? 'active' : ''}`} onClick={() => { setActiveTab('invest'); setError(''); }}>Investment</button>
        <button className={`grow-tab ${activeTab === 'skill' ? 'active' : ''}`} onClick={() => { setActiveTab('skill'); setError(''); }}>Skill</button>
      </div>

      {/* ======== BUSINESS TAB ======== */}
      {activeTab === 'business' && (
        <div className="section-card">

          {/* Step 3: Result */}
          {businessStep === 'result' && businessResult && (
            <div className="grow-result-card">
              <div className="grow-result-icon">🚀</div>
              <h2 className="grow-result-title">{businessResult.message}</h2>
              <div className="business-sim-card">
                <div className="sim-row"><span>Cost:</span><span className="sim-cost">Rs. {parseFloat(businessResult.cost)}</span></div>
                <div className="sim-row"><span>Revenue:</span><span className="sim-revenue">Rs. {parseFloat(businessResult.actual_revenue)}</span></div>
                <div className="sim-row"><span>Actual Profit:</span><span className="sim-profit">Rs. {parseFloat(businessResult.actual_profit)}</span></div>
                <div className="sim-row"><span>Expected Range:</span><span>Rs. {parseFloat(businessResult.expected_profit_min)} – Rs. {parseFloat(businessResult.expected_profit_max)}</span></div>
                <div className="sim-row"><span>Skills:</span><span>{businessResult.skills.join(', ')}</span></div>
              </div>
              <p className="grow-disclaimer">{businessResult.disclaimer}</p>
              <p className="grow-new-balance">Naya balance: <strong>Rs. {parseFloat(businessResult.wallet_balance).toLocaleString()}</strong></p>
              <button className="secondary-btn" onClick={resetBusinessFlow} style={{ marginTop: '1rem' }}>
                Doosra Business Try Karein
              </button>
            </div>
          )}

          {/* Step 2: Ranked businesses with AI pitches */}
          {businessStep === 'businesses' && recommendResult && (
            <>
              <h2 className="section-title">AI Recommendations</h2>
              <p className="section-hint">{recommendResult.message}</p>
              {recommendResult.business.length === 0 ? (
                <p className="section-hint">Aapke paas koi business afford karne ke liye paise nahi hain. Pehle SAVE karein!</p>
              ) : (
                <div className="business-grid">
                  {recommendResult.business.map((t) => (
                    <button
                      key={t.id}
                      className={`business-card ${!t.affordable ? 'disabled-option' : ''} ${t.match_score > 0 ? 'recommended' : ''}`}
                      onClick={() => t.affordable && handleBusiness(t)}
                      disabled={!t.affordable || businessLoading}
                    >
                      {t.match_score > 0 && <span className="business-badge">✨ Recommended</span>}
                      <span className="business-name">{t.name}</span>
                      <span className="business-pitch">{t.pitch}</span>
                      <span className="business-cost">Cost: Rs. {t.cost}</span>
                      <span className="business-profit">Expected Profit: ~Rs. {t.expected_profit_min}–{t.expected_profit_max}</span>
                      <span className="business-skills">{t.skills.join(', ')}</span>
                    </button>
                  ))}
                </div>
              )}
              <button className="secondary-btn" onClick={resetBusinessFlow} style={{ marginTop: '1rem' }}>
                ← Dobara Interest Choose Karein
              </button>
            </>
          )}

          {/* Step 1: Interest picker */}
          {businessStep === 'interests' && (
            <>
              <h2 className="section-title">Aapko kya pasand hai?</h2>
              <p className="section-hint">Apne interests select karein — hum aapke liye best business ideas suggest karein ge!</p>
              <div className="interest-grid">
                {templates.interest_options.map((opt) => (
                  <button
                    key={opt.id}
                    className={`interest-chip ${selectedInterests.includes(opt.id) ? 'selected' : ''}`}
                    onClick={() => toggleInterest(opt.id)}
                  >
                    <span className="interest-icon">{opt.icon}</span>
                    <span className="interest-label">{opt.label}</span>
                    {selectedInterests.includes(opt.id) && <span className="interest-check">✓</span>}
                  </button>
                ))}
              </div>
              <button
                className="primary-btn grow-btn-action"
                style={{ marginTop: '1.2rem' }}
                onClick={handleGetRecommendations}
                disabled={businessLoading}
              >
                {businessLoading ? 'Soch raha hoon...' : 'Business Ideas Dikhayein 🚀'}
              </button>
              <p className="section-hint" style={{ marginTop: '0.8rem', textAlign: 'center' }}>
                Interest skip karna hai? Bas button dabayein — sab businesses dikhayein ge!
              </p>
            </>
          )}
        </div>
      )}

      {/* ======== INVESTMENT TAB ======== */}
      {activeTab === 'invest' && (
        <div className="section-card">
          {/* Step 5: Diversification mini-lesson */}
          {investStep === 'diversify' && investResult && (
            <div className="invest-diversify-card">
              <h2 className="section-title">💡 Ek sawal:</h2>
              <p className="section-subtitle">Kya aap apna sara virtual paisa yahan invest karte?</p>
              {diversifyAnswer === null && (
                <div className="diversify-buttons">
                  <button className="diversify-btn diversify-yes" onClick={() => setDiversifyAnswer('yes')}>Haan</button>
                  <button className="diversify-btn diversify-no" onClick={() => setDiversifyAnswer('no')}>Nahi</button>
                </div>
              )}
              {diversifyAnswer === 'no' && (
                <div className="diversify-answer">
                  <p className="diversify-good">✅ Bohat acha socha!</p>
                  <p className="diversify-lesson">Different options ko samajhna risk ko manage karne mein help karta hai. Apna sara paisa ek jagah lagana risky ho sakta hai.</p>
                </div>
              )}
              {diversifyAnswer === 'yes' && (
                <div className="diversify-answer">
                  <p className="diversify-warn">⚠️ Interesting choice!</p>
                  <p className="diversify-lesson">Lekin agar isi option mein loss ho gaya to aapka bohat sara virtual paisa lose ho sakta hai. Isliye kehte hain: "Don't put all your eggs in one basket!"</p>
                </div>
              )}
              <p className="grow-disclaimer" style={{ marginTop: '1rem' }}>Ye sirf educational simulation hai. Real financial advice nahi hai.</p>
              <div className="invest-result-actions">
                <button className="secondary-btn" onClick={resetInvestFlow}>Try Again</button>
                <button className="secondary-btn" onClick={() => { resetInvestFlow(); setActiveTab('business'); }}>Back to GROW</button>
                <button className="primary-btn" onClick={() => navigate('/dashboard')}>Go to Dashboard</button>
              </div>
            </div>
          )}

          {/* Step 4: Result + Educational moment */}
          {investStep === 'result' && investResult && !diversifyAnswer && (
            <div className="grow-result-card">
              <div className="grow-result-icon">{investResult.is_profit ? '🎉' : '😬'}</div>
              <h2 className="grow-result-title">
                {investResult.is_profit ? 'Your investment grew!' : 'Oh no! Investment kam ho gayi.'}
              </h2>
              <div className="invest-result-card">
                <div className="sim-row"><span>Invested:</span><span>Rs. {parseFloat(investResult.invested_amount)}</span></div>
                <div className="sim-row"><span>Change:</span><span className={investResult.is_profit ? 'sim-profit' : 'sim-loss'}>{investResult.return_percentage > 0 ? '+' : ''}{investResult.return_percentage}%</span></div>
                <div className="sim-row"><span>{investResult.is_profit ? 'Profit:' : 'Loss:'}</span><span className={investResult.is_profit ? 'sim-profit' : 'sim-loss'}>Rs. {Math.abs(parseFloat(investResult.profit_loss)).toFixed(2)}</span></div>
                <div className="sim-row"><span>Final value:</span><span>Rs. {parseFloat(investResult.outcome_amount).toFixed(2)}</span></div>
              </div>
              <p className="grow-educational">
                {investResult.is_profit
                  ? `Is simulation mein aapka virtual paisa Rs. ${Math.abs(parseFloat(investResult.profit_loss)).toFixed(2)} barha. Real life mein investment ka result different ho sakta hai.`
                  : 'Investment mein loss bhi ho sakta hai. Isi liye risk samajhna important hai.'
                }
              </p>
              <div className="invest-learn-box">
                <h3 className="learn-title">📚 What did you learn?</h3>
                <p className="learn-text">
                  {investResult.is_profit
                    ? 'Investment se profit ho sakta hai, lekin profit guaranteed nahi hota.'
                    : 'Jitna zyada risk, utna zyada chance ke result bohat change ho sakta hai.'
                  }
                </p>
                <p className="learn-tip">💡 Smart tip: Apna sara paisa ek hi jagah lagana zaroori nahi hota.</p>
              </div>
              <p className="grow-new-balance">Naya balance: <strong>Rs. {parseFloat(investResult.wallet_balance).toLocaleString()}</strong></p>
              <button className="primary-btn" onClick={() => setInvestStep('diversify')} style={{ marginTop: '1rem' }}>
                Aage barho →
              </button>
            </div>
          )}

          {/* Step 3: Confirmation */}
          {investStep === 'confirm' && investOption && (
            <div className="invest-confirm-card">
              <h2 className="section-title">Confirm karein:</h2>
              <div className="invest-confirm-box">
                <p className="confirm-text">Aap Rs. {investAmount} invest kar rahe hain:</p>
                <div className="confirm-option">
                  <span className="confirm-icon">{investOption.icon}</span>
                  <span className="confirm-name">{investOption.name}</span>
                </div>
                <p className="confirm-risk">Risk: {investOption.id.charAt(0).toUpperCase() + investOption.id.slice(1)}</p>
                <p className="confirm-range">Possible outcome: {investOption.range}</p>
              </div>
              <p className="section-hint">Ready to see what happens?</p>
              <div className="invest-confirm-buttons">
                <button className="secondary-btn" onClick={() => setInvestStep('select')}>← Wapas</button>
                <button className="primary-btn grow-btn-action" onClick={handleInvestConfirm} disabled={investLoading}>
                  {investLoading ? 'Processing...' : 'Run Simulation 🎲'}
                </button>
              </div>
              <p className="grow-disclaimer">Ye sirf educational simulation hai.</p>
            </div>
          )}

          {/* Step 2: Select option + amount */}
          {investStep === 'select' && (
            <>
              <h2 className="section-title">Investment Option Choose Karein</h2>
              <p className="section-hint">Ye fictional educational simulation hai. Real companies/stocks nahi hain.</p>
              <div className="invest-options-grid">
                {templates.investment_options.map((opt) => (
                  <button
                    key={opt.id}
                    className={`invest-option-card invest-risk-${opt.id} ${investOption?.id === opt.id ? 'selected' : ''}`}
                    onClick={() => setInvestOption(opt)}
                  >
                    <span className="invest-option-icon">{opt.icon}</span>
                    <span className="invest-option-name">{opt.name}</span>
                    <span className={`invest-option-risk risk-label-${opt.id}`}>
                      {opt.id === 'low' ? 'Low Risk' : opt.id === 'medium' ? 'Medium Risk' : 'High Risk'}
                    </span>
                    <span className="invest-option-desc">{opt.description}</span>
                    <span className="invest-option-range">{opt.range}</span>
                  </button>
                ))}
              </div>
              {investOption && (
                <>
                  <div className="form-group" style={{ marginTop: '1.2rem' }}>
                    <label>Kitna virtual paisa invest karna hai? (Rs.)</label>
                    <input
                      type="number"
                      className="form-input"
                      value={investAmount}
                      onChange={(e) => setInvestAmount(e.target.value)}
                      min="1"
                      max={balance}
                      placeholder={`Max: Rs. ${balance}`}
                    />
                  </div>
                  <div className="invest-select-buttons">
                    <button className="secondary-btn" onClick={() => setInvestStep('intro')}>← Wapas</button>
                    <button
                      className="primary-btn grow-btn-action"
                      onClick={() => {
                        const amt = parseFloat(investAmount);
                        if (isNaN(amt) || amt <= 0) { setError('Amount 0 se zyada hona chahiye.'); return; }
                        if (amt > balance) { setError(`Aapke paas sirf Rs. ${balance} hain.`); return; }
                        setError('');
                        setInvestStep('confirm');
                      }}
                    >
                      Aage barho →
                    </button>
                  </div>
                </>
              )}
            </>
          )}

          {/* Step 1: Intro */}
          {investStep === 'intro' && (
            <div className="invest-intro-card">
              <h2 className="invest-intro-title">Chalo investment ka game khelte hain! 💰</h2>
              <p className="invest-intro-text">
                Investment mein paisa barh bhi sakta hai aur kam bhi ho sakta hai.
                <br />
                Is game mein hum sirf <strong>virtual paisay</strong> use karenge.
              </p>
              <div className="invest-virtual-money">
                <span className="virtual-label">Your virtual money:</span>
                <span className="virtual-amount">Rs. {balance.toLocaleString()}</span>
              </div>
              <p className="invest-sim-label">🎮 SIMULATION — Educational game only</p>
              <button className="primary-btn grow-btn-action" onClick={() => setInvestStep('select')} style={{ marginTop: '1rem' }}>
                Start Game →
              </button>
            </div>
          )}
        </div>
      )}

      {/* ======== SKILL TAB ======== */}
      {activeTab === 'skill' && (
        <div className="section-card">

          {/* Step progress bar */}
          {selectedSkill && (
            <div className="skill-lab-progress">
              {['pick', 'discover', 'challenge', 'connect'].map((step, i) => (
                <div key={step} className={`skill-progress-step ${skillStep === step ? 'active' : ''}`}>
                  <span className="skill-progress-num">{i + 1}</span>
                  <span className="skill-progress-label">{['Pick', 'Discover', 'Challenge', 'Connect'][i]}</span>
                </div>
              ))}
            </div>
          )}

          {/* Step 4: CONNECT — Result + financial literacy connection */}
          {skillStep === 'connect' && skillResult && (
            <div className="grow-result-card">
              <div className="grow-result-icon">🎉</div>
              <h2 className="grow-result-title">Challenge Complete!</h2>

              {/* Challenge result */}
              <div className={`skill-challenge-result ${skillResult.is_correct ? 'correct' : 'wrong'}`}>
                <p className="challenge-verdict">
                  {skillResult.is_correct ? '✅ Sahi jawab!' : '❌ Galat jawab — lekin seekhna zaroori hai!'}
                </p>
                <p className="challenge-explanation">{skillResult.explanation}</p>
              </div>

              {/* Financial literacy connection */}
              <div className="skill-connect-card">
                <h3 className="connect-title">💰 Skill → Future</h3>
                <p className="connect-text">{skillResult.connect_text}</p>
                <p className="connect-disclaimer">⚠️ Income guaranteed nahi hoti. Skill ko useful banane ke liye practice aur learning zaroori hai.</p>
              </div>

              {/* Earning potential */}
              <p className="skill-earning">{skillResult.earning_potential}</p>

              {/* Business link */}
              {skillResult.linked_business_ids && skillResult.linked_business_ids.length > 0 && (
                <div className="skill-business-link">
                  <p className="business-link-title">🧪 Skill Lab ke baad ek experiment karna hai?</p>
                  <button className="secondary-btn" onClick={() => { resetSkillFlow(); setActiveTab('business'); }}>
                    TRY A BUSINESS →
                  </button>
                </div>
              )}

              {/* Learn more placeholder */}
              <div className="skill-learn-more">
                <p className="learn-more-title">📚 Want to learn more?</p>
                <button className="secondary-btn" disabled style={{ opacity: 0.5 }}>Learn More (Coming Soon)</button>
              </div>

              <div className="invest-result-actions">
                <button className="secondary-btn" onClick={resetSkillFlow}>Try Another Skill</button>
                <button className="secondary-btn" onClick={() => { resetSkillFlow(); }}>Back to GROW</button>
                <button className="primary-btn" onClick={() => navigate('/dashboard')}>Go to Dashboard</button>
              </div>
            </div>
          )}

          {/* Step 3: CHALLENGE */}
          {skillStep === 'challenge' && selectedSkill && selectedSkill.challenge && (
            <div className="skill-challenge-card">
              <h2 className="section-title">🧠 Mini Challenge</h2>
              <p className="challenge-question">{selectedSkill.challenge.question}</p>
              <div className="challenge-options">
                {selectedSkill.challenge.options.map((opt) => (
                  <button
                    key={opt.id}
                    className={`challenge-option ${challengeAnswer === opt.id ? 'selected' : ''}`}
                    onClick={() => setChallengeAnswer(opt.id)}
                  >
                    <span className="option-letter">{opt.id.toUpperCase()}</span>
                    <span className="option-text">{opt.text}</span>
                  </button>
                ))}
              </div>

              {/* Optional practice text (Writing skill only) */}
              {selectedSkill.optional_practice && (
                <div className="skill-optional-practice">
                  <p className="practice-label">✏️ Optional Practice:</p>
                  <p className="practice-prompt">{selectedSkill.optional_practice}</p>
                  <textarea
                    className="form-input practice-textarea"
                    value={practiceText}
                    onChange={(e) => setPracticeText(e.target.value)}
                    placeholder="Yahan likhein... (optional)"
                    rows={3}
                  />
                  <p className="practice-note">Ye optional hai — sirf practice ke liye. Aapka jawab save hoga.</p>
                </div>
              )}

              <div className="invest-select-buttons">
                <button className="secondary-btn" onClick={() => setSkillStep('discover')}>← Wapas</button>
                <button className="primary-btn grow-btn-action" onClick={handleSkillChallengeSubmit} disabled={skillLoading}>
                  {skillLoading ? 'Processing...' : 'Submit Challenge 🧪'}
                </button>
              </div>
            </div>
          )}

          {/* Step 2: DISCOVER */}
          {skillStep === 'discover' && selectedSkill && !skillResult && (
            <div className="skill-discover-card">
              <div className="discover-header">
                <span className="discover-icon">{selectedSkill.icon}</span>
                <h2 className="discover-title">{selectedSkill.name} LAB</h2>
                <p className="discover-tagline">Let's experiment! 🧪</p>
              </div>

              <div className="discover-section">
                <h3 className="discover-step-title">🔍 DISCOVER</h3>
                <p className="discover-text">{selectedSkill.discover}</p>
              </div>

              <div className="discover-section">
                <h3 className="discover-step-title">📝 KAISE SHURU KAREIN?</h3>
                <p className="discover-steps">{selectedSkill.steps}</p>
              </div>

              <div className="discover-actions">
                <button className="secondary-btn" onClick={resetSkillFlow}>← Wapas</button>
                <button className="primary-btn grow-btn-action" onClick={() => setSkillStep('challenge')}>
                  Start Challenge 🧪
                </button>
              </div>
            </div>
          )}

          {/* Step 1: PICK */}
          {skillStep === 'pick' && (
            <>
              <h2 className="section-title">🧪 SKILL LAB</h2>
              <p className="section-hint">Kon si cheez tumhein sab se zyada pasand hai? Apni pasand choose karo 👀</p>
              <div className="skill-grid">
                {templates.skills.map((s) => (
                  <button key={s.id} className="skill-card" onClick={() => handleSkillSelect(s)}>
                    <span className="skill-card-icon">{s.icon}</span>
                    <span className="skill-card-name">{s.name}</span>
                    <span className="skill-card-why">{s.discover || s.why}</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
