import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  startMoneyLab, getLabState, setupMoneyLab,
  advanceMoneyLab, decideMoneyLab, reflectMoneyLab,
} from '../services/api';
import MoneyTerms from '../components/MoneyTerms';

const STORAGE_KEY = 'rkl_child_id';

export default function MoneyLab() {
  const navigate = useNavigate();
  const childId = localStorage.getItem(STORAGE_KEY);

  const [phase, setPhase] = useState('loading'); // loading, intro, business, investment, pricing, setup, daily, decision, finished
  const [error, setError] = useState('');

  // Config from start endpoint
  const [businesses, setBusinesses] = useState([]);
  const [investmentOptions, setInvestmentOptions] = useState([]);
  const [pricingOptions, setPricingOptions] = useState([]);
  const [balance, setBalance] = useState(0);

  // Choices
  const [businessId, setBusinessId] = useState(null);
  const [investmentId, setInvestmentId] = useState(null);
  const [pricingId, setPricingId] = useState(null);

  // Simulation
  const [dayResult, setDayResult] = useState(null); // latest day's response
  const [stateSummary, setStateSummary] = useState(null); // running totals
  const [businessInfo, setBusinessInfo] = useState(null);
  const [finalResult, setFinalResult] = useState(null);
  const [botLine, setBotLine] = useState('');

  // ── Init ──────────────────────────────────────────
  useEffect(() => {
    if (!childId) { navigate('/'); return; }
    init();
  }, [childId]);

  const init = async () => {
    try {
      // Check for existing experiment to resume
      const existing = await getLabState(childId);
      if (existing && existing.state && existing.state.phase === 'running') {
        // Resume mid-experiment
        setStateSummary(existing.state);
        setBusinessInfo(existing.business);
        setBusinessId(existing.state.business_id);
        setInvestmentId(existing.state.investment_id);
        setPricingId(existing.state.pricing_id);
        setBalance(existing.wallet_balance);
        setDayResult({
          day: existing.state.day,
          outcome: existing.state.daily_outcomes?.slice(-1)[0] || null,
          event: null,
          state: existing.state,
        });
        setPhase('daily');
        return;
      }
      if (existing && existing.state && existing.state.phase === 'finished') {
        // Experiment already done — show results and pre-load new experiment config
        setStateSummary(existing.state);
        setBalance(existing.wallet_balance);
        try {
          const data = await startMoneyLab(childId);
          setBusinesses(data.businesses || []);
          setInvestmentOptions(data.investment_options || []);
          setPricingOptions(data.pricing_options || []);
          sessionStorage.setItem('lab_activity_id', String(data.activity_id));
        } catch { /* non-critical */ }
        setPhase('finished');
        return;
      }
    } catch { /* no existing experiment */ }

    try {
      const data = await startMoneyLab(childId);
      setBusinesses(data.businesses || []);
      setInvestmentOptions(data.investment_options || []);
      setPricingOptions(data.pricing_options || []);
      setBalance(data.balance);
      sessionStorage.setItem('lab_activity_id', String(data.activity_id));
      setPhase('intro');
    } catch (err) {
      setError(err.message);
      setPhase('error');
    }
  };

  // ── Handlers ──────────────────────────────────────
  const handleBusiness = (id) => { setBusinessId(id); setPhase('investment'); };
  const handleInvestment = (id) => { setInvestmentId(id); setPhase('pricing'); };

  const handlePricing = async (id) => {
    setPricingId(id);
    setPhase('setup');
    try {
      const res = await setupMoneyLab(childId, businessId, investmentId, id);
      setBalance(prev => {
        // Balance was reduced by cost during setup
        return res.state ? res.state.cash + res.state.total_costs : prev;
      });
      setBusinessInfo({ name: res.business_name, icon: res.business_icon });
      setDayResult(res);
      setStateSummary(res.state);
      setPhase('daily');
    } catch (err) {
      setError(err.message);
      setPhase('pricing');
    }
  };

  const handleNextDay = async () => {
    setPhase('loading_next');
    try {
      const res = await advanceMoneyLab(childId);
      if (res.needs_decision) {
        setDayResult(res);
        setStateSummary(res.state);
        setPhase('decision');
      } else if (res.finished) {
        setFinalResult(res);
        setBalance(res.balance_after);
        setStateSummary(null);
        setPhase('finished');
      } else {
        setDayResult(res);
        setStateSummary(res.state);
        setPhase('daily');
      }
    } catch (err) {
      setError(err.message);
      setPhase('daily');
    }
  };

  const handleDecision = async (decisionId) => {
    setPhase('loading_next');
    try {
      const res = await decideMoneyLab(childId, decisionId);
      setDayResult(res);
      setStateSummary(res.state);
      setPhase('daily');
    } catch (err) {
      setError(err.message);
      setPhase('decision');
    }
  };

  const handleReflection = async (reflectionId) => {
    try {
      const res = await reflectMoneyLab(childId, reflectionId);
      setBotLine(res.bot_line);
    } catch { /* non-critical */ }
  };

  const handleTryAgain = () => {
    setPhase('loading');
    setError('');
    setBusinessId(null);
    setInvestmentId(null);
    setPricingId(null);
    setDayResult(null);
    setStateSummary(null);
    setFinalResult(null);
    setBotLine('');
    setBusinessInfo(null);
    // If config already loaded (from resume), skip to intro
    if (businesses.length > 0) {
      setPhase('intro');
    } else {
      init();
    }
  };

  // ── Loading / Error ───────────────────────────────
  if (phase === 'loading') {
    return (
      <div className="lab-v2-container">
        <p className="lab-loading-text">🧪 Money Lab khul raha hai...</p>
      </div>
    );
  }
  if (phase === 'error') {
    return (
      <div className="lab-v2-container">
        <p className="lab-error-text">{error}</p>
        <button className="lab-back-btn" onClick={() => navigate('/dashboard')}>← Dashboard</button>
      </div>
    );
  }
  if (phase === 'loading_next') {
    return (
      <div className="lab-v2-container">
        <div className="lab-loading-spinner">
          <span className="lab-spinner-icon">⚙️</span>
          <p>Agla din aa raha hai...</p>
        </div>
      </div>
    );
  }

  const selectedBiz = businesses.find(b => b.id === businessId);

  // ── CEO Certificate helpers (frontend-only) ──────────
  const getCEOCertificate = () => {
    const profit = finalResult
      ? parseFloat(finalResult.profit_loss)
      : (stateSummary ? stateSummary.total_revenue - stateSummary.total_costs : 0);
    const starting = finalResult ? parseFloat(finalResult.starting_money) : 500;
    const ratio = profit / starting;

    let grade = 'B', gradeLine = 'Profitable CEO — shabash!';
    if (ratio >= 0.6) { grade = 'A+'; gradeLine = 'Business Superstar! 🌟'; }
    else if (ratio >= 0.25) { grade = 'A'; gradeLine = 'Zabardast kamai! 🚀'; }
    else if (ratio > 0) { grade = 'B+'; gradeLine = 'Profit banaya — well played!'; }
    else { grade = 'C'; gradeLine = 'Brave try — seekhne wala CEO!'; }

    const risk = selectedBiz?.risk;
    let archetype = { icon: '⚖️', title: 'Balanced Businessperson', line: 'Risk aur safety ka perfect mix!' };
    if (risk === 'high' || pricingId === 'premium') {
      archetype = { icon: '🦅', title: 'Daring Risk-Taker', line: 'Bade sapne, bade faisle!' };
    } else if (risk === 'low' && pricingId !== 'premium') {
      archetype = { icon: '🛡️', title: 'Smart Saver', line: 'Safe khela, solid plan!' };
    }

    const revenue = finalResult ? finalResult.total_revenue : (stateSummary?.total_revenue || 0);
    const customers = finalResult ? finalResult.total_customers : (stateSummary?.total_customers || 0);

    return { grade, gradeLine, archetype, revenue, customers, profit };
  };

  // ── Render ────────────────────────────────────────
  return (
    <div className="lab-v2-container">
      {/* Header */}
      <header className="lab-v2-header">
        <button className="lab-back-btn" onClick={() => navigate('/dashboard')}>← Dashboard</button>
        <div className="lab-v2-title">
          <span className="lab-v2-icon">🧪</span>
          <h1>MONEY LAB</h1>
        </div>
        <div className="lab-v2-balance">
          Wallet: <strong>Rs. {typeof balance === 'number' ? balance : Number(balance).toFixed(0)}</strong>
        </div>
      </header>

      {/* Error banner */}
      {error && <div className="lab-error-banner">{error}</div>}

      {/* ─── INTRO ─── */}
      {phase === 'intro' && (
        <section className="lab-v2-intro">
          <div className="lab-intro-card">
            <span className="lab-intro-flask">🧪</span>
            <h2>Rs. 500 ko 7 din mein barhao!</h2>
            <div className="lab-intro-steps">
              <span>🏪 Business kholo</span>
              <span>💰 Paise kamao</span>
              <span>🧠 Smart decisions lo</span>
            </div>
            <p className="lab-intro-hint">
              ⚠️ Har decision ka asar hota hai — kabhi profit, kabhi loss!
            </p>
            <button className="lab-start-btn" onClick={() => setPhase('business')}>
              Chalo Shuru Karte Hain! 🚀
            </button>
          </div>
        </section>
      )}

      {/* ─── BUSINESS SELECTION ─── */}
      {phase === 'business' && (
        <section className="lab-v2-step">
          <h2>🏪 Apna Business Choose Karo!</h2>
          <p className="lab-step-hint">Har business ka apna style hai 🎯</p>
          <div className="lab-choice-grid">
            {businesses.map(biz => (
              <button key={biz.id} className={`lab-choice-card lab-biz-${biz.risk}`} onClick={() => handleBusiness(biz.id)}>
                <span className="card-icon">{biz.icon}</span>
                <span className="card-name">{biz.name}</span>
                <div className="card-footer">
                  <span className={`card-risk risk-${biz.risk}`}>
                    {biz.risk === 'low' ? '🟢 Safe' : biz.risk === 'medium' ? '🟡 Medium' : '🔴 Risky'}
                  </span>
                  <span className="card-cost">Rs. {biz.base_cost}+</span>
                </div>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* ─── INVESTMENT ─── */}
      {phase === 'investment' && selectedBiz && (
        <section className="lab-v2-step">
          <div className="lab-selected-badge">{selectedBiz.icon} {selectedBiz.name}</div>
          <h2>💰 Kitna Invest Karo?</h2>
          <p className="lab-step-hint">Zyada invest = zyada stock = zyada risk aur reward.</p>
          <div className="lab-choice-grid">
            {investmentOptions.map(opt => {
              const cost = selectedBiz.base_cost * opt.multiplier;
              const remaining = 500 - cost;
              return (
                <button key={opt.id} className="lab-choice-card" onClick={() => handleInvestment(opt.id)}>
                  <span className="card-icon">{opt.id === 'small' ? '🪙' : opt.id === 'medium' ? '💰' : '💎'}</span>
                  <span className="card-name">{opt.label}</span>
                  <span className="card-cost-big">Rs. {cost}</span>
                  <span className="card-desc">{opt.description}</span>
                  <span className="card-sub">📦 {opt.multiplier * 20} units · 💵 Rs. {remaining} bachega</span>
                </button>
              );
            })}
          </div>
          <button className="lab-go-back" onClick={() => setPhase('business')}>← Business Badlo</button>
        </section>
      )}

      {/* ─── PRICING ─── */}
      {phase === 'pricing' && (
        <section className="lab-v2-step">
          <div className="lab-selected-badge">
            {selectedBiz?.icon} {selectedBiz?.name} · {investmentOptions.find(i => i.id === investmentId)?.label}
          </div>
          <h2>🏷️ Qeemat Kya Rakho?</h2>
          <p className="lab-step-hint">Sasti qeemat = zyada customers. Mehngi = zyada per sale.</p>
          <div className="lab-choice-grid">
            {pricingOptions.map(opt => (
              <button key={opt.id} className="lab-choice-card" onClick={() => handlePricing(opt.id)}>
                <span className="card-icon">
                  {opt.id === 'cheap' ? '🏷️' : opt.id === 'normal' ? '💵' : '✨'}
                </span>
                <span className="card-name">{opt.label}</span>
                <span className="card-desc">{opt.description}</span>
                {opt.demand_hint && <span className="card-sub">👥 {opt.demand_hint}</span>}
              </button>
            ))}
          </div>
          <button className="lab-go-back" onClick={() => setPhase('investment')}>← Invest Badlo</button>
        </section>
      )}

      {/* ─── SETUP (loading Day 1) ─── */}
      {phase === 'setup' && (
        <div className="lab-loading-spinner">
          <span className="lab-spinner-icon">🏪</span>
          <p>{selectedBiz?.name} khul raha hai...</p>
        </div>
      )}

      {/* ─── DAILY VIEW ─── */}
      {phase === 'daily' && dayResult && stateSummary && (
        <section className="lab-v2-daily">
          {/* Day header */}
          <div className="lab-day-header">
            <h2>Day {stateSummary.day} / 7</h2>
            <div className="lab-day-progress">
              {[1,2,3,4,5,6,7].map(d => (
                <span key={d} className={`lab-dot ${d <= stateSummary.day ? 'filled' : ''} ${d === 4 ? 'decision' : ''}`} />
              ))}
            </div>
          </div>

          {/* Business badge */}
          <div className="lab-biz-badge">
            <span>{businessInfo?.icon || '🏪'}</span>
            <span>{businessInfo?.name || 'Business'}</span>
          </div>

          {/* Event card */}
          {dayResult.event && (
            <div className="lab-event-card">
              <span className="event-icon">{dayResult.event.icon}</span>
              <div>
                <strong>{dayResult.event.name}</strong>
                <p>{dayResult.event.message}</p>
              </div>
            </div>
          )}

          {/* Story */}
          {dayResult.outcome && (
            <div className="lab-story-card">
              <span className="lab-story-emoji">
                {dayResult.outcome.units_sold > 5 ? '🤩' : dayResult.outcome.units_sold > 0 ? '😊' : '😅'}
              </span>
              <p>{dayResult.outcome.story}</p>
              {dayResult.outcome.ran_out_of_stock && (
                <p className="lab-warning">😱 Stock khatam! Kuch customers ko khali haath jana pada.</p>
              )}
            </div>
          )}

          {/* Today's numbers */}
          {dayResult.outcome && (
            <div className="lab-day-numbers">
              <div className="lab-stat">
                <span className="stat-icon">👥</span>
                <span className="stat-val">{dayResult.outcome.customers}</span>
                <span className="stat-label">Customers</span>
              </div>
              <div className="lab-stat">
                <span className="stat-icon">🛒</span>
                <span className="stat-val">{dayResult.outcome.units_sold}</span>
                <span className="stat-label">Sold</span>
              </div>
              <div className="lab-stat">
                <span className="stat-icon">💵</span>
                <span className="stat-val">Rs. {dayResult.outcome.revenue}</span>
                <span className="stat-label">Revenue</span>
              </div>
              <div className="lab-stat">
                <span className="stat-icon">📦</span>
                <span className="stat-val">{stateSummary.stock}</span>
                <span className="stat-label">Stock Left</span>
              </div>
            </div>
          )}

          {/* Demand hint */}
          {dayResult.outcome && (
            <p className="lab-demand-hint">
              Your pricing: {pricingOptions.find(p => p.id === pricingId)?.label || '—'} ·
              Potential demand: {dayResult.outcome.potential_demand_low}–{dayResult.outcome.potential_demand_high} customers/day
            </p>
          )}

          {/* Running totals */}
          <div className="lab-running-totals">
            <span>Cash: <strong>Rs. {stateSummary.cash}</strong></span>
            <span>Revenue: <strong>Rs. {stateSummary.total_revenue}</strong></span>
            <span>Costs: <strong>Rs. {stateSummary.total_costs}</strong></span>
            <span className={stateSummary.profit_loss >= 0 ? 'profit' : 'loss'}>
              P/L: <strong>{stateSummary.profit_loss >= 0 ? '+' : ''}Rs. {stateSummary.profit_loss}</strong>
            </span>
          </div>

          {/* Money terms glossary — tap to learn */}
          <MoneyTerms />

          {/* Next button */}
          <button
            className="lab-next-btn"
            onClick={handleNextDay}
          >
            {stateSummary.day >= 7 ? '📊 Final Results Dekho' :
             stateSummary.day >= 6 ? 'Last Day →' :
             'Next Day →'}
          </button>
        </section>
      )}

      {/* ─── DECISION (Day 4) ─── */}
      {phase === 'decision' && dayResult && stateSummary && (
        <section className="lab-v2-decision">
          <div className="lab-day-header">
            <h2>Day 4 / 7 — Decision Day</h2>
            <div className="lab-day-progress">
              {[1,2,3,4,5,6,7].map(d => (
                <span key={d} className={`lab-dot ${d <= 4 ? 'filled' : ''} ${d === 4 ? 'decision' : ''}`} />
              ))}
            </div>
          </div>

          <div className="lab-decision-card">
            <h3>🤔 4 din ho gaye. Apni strategy adjust karo!</h3>
            <p>Ab tak: Rs. {stateSummary.total_revenue} revenue, {stateSummary.total_customers} customers, stock: {stateSummary.stock}</p>
            <div className="lab-decision-grid">
              {dayResult.decisions.map(d => (
                <button
                  key={d.id}
                  className={`lab-decision-btn ${d.disabled ? 'disabled' : ''}`}
                  onClick={() => !d.disabled && handleDecision(d.id)}
                  disabled={d.disabled}
                >
                  <span className="dec-label">{d.label}</span>
                  <span className="dec-desc">{d.description}</span>
                  {d.cost && <span className="dec-cost">Cost: Rs. {d.cost} → +{d.stock_gain} stock</span>}
                  {d.disabled && <span className="dec-disabled">Not enough cash</span>}
                </button>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ─── FINISHED ─── */}
      {phase === 'finished' && (
        <section className="lab-v2-finished">
          {finalResult ? (
            <>
              {/* Result header */}
              <div className={`lab-result-header ${finalResult.is_profit ? 'profit' : 'loss'}`}>
                <div className="lab-confetti">
                  {finalResult.is_profit
                    ? ['🎉','🎊','✨','🌟','💫','🎉','🎊','✨'].map((e,i) => (
                        <span key={i} className="confetti-piece" style={{left: `${10+i*11}%`, animationDelay: `${i*0.15}s`}}>{e}</span>
                      ))
                    : ['📉','😢','💪','📚'].map((e,i) => (
                        <span key={i} className="confetti-piece" style={{left: `${15+i*20}%`, animationDelay: `${i*0.2}s`}}>{e}</span>
                      ))
                  }
                </div>
                <span className="result-emoji">{finalResult.is_profit ? '🎉' : '📉'}</span>
                <h2>{finalResult.is_profit ? 'PROFIT!' : 'LOSS!'}</h2>
                <span className="result-pl">
                  {finalResult.is_profit ? '+' : ''}Rs. {finalResult.profit_loss}
                </span>
                <p className="result-cheer">
                  {finalResult.is_profit
                    ? finalResult.profit_loss > 2000 ? '🏆 Business genius!' : '💪 Shabash!'
                    : '📚 Seekhne ko mila — agli baar better hoga!'}
                </p>
              </div>

              {/* Final report card */}
              <div className="lab-final-card">
                <h3>🧪 Your 7-Day Results</h3>
                <div className="lab-final-row">
                  <span>Business</span><strong>{finalResult.business_icon} {finalResult.business_name}</strong>
                </div>
                <div className="lab-final-row">
                  <span>Starting Money</span><strong>Rs. {finalResult.starting_money}</strong>
                </div>
                <div className="lab-final-row">
                  <span>Total Revenue</span><strong className="revenue">Rs. {finalResult.total_revenue}</strong>
                </div>
                <div className="lab-final-row">
                  <span>Total Costs</span><strong className="cost">Rs. {finalResult.total_costs}</strong>
                </div>
                <div className="lab-final-row">
                  <span>Customers</span><strong>{finalResult.total_customers}</strong>
                </div>
                <div className="lab-final-row">
                  <span>Items Sold</span><strong>{finalResult.total_units_sold}</strong>
                </div>
                <div className="lab-final-divider" />
                <div className="lab-final-row highlight">
                  <span>Final Cash</span><strong>Rs. {finalResult.final_cash}</strong>
                </div>
                <div className={`lab-final-row highlight ${finalResult.is_profit ? 'profit' : 'loss'}`}>
                  <span>{finalResult.is_profit ? 'Profit' : 'Loss'}</span>
                  <strong>{finalResult.is_profit ? '+' : ''}Rs. {finalResult.profit_loss}</strong>
                </div>
              </div>

              {/* CEO CERTIFICATE — the wow moment */}
              {(() => {
                const cert = getCEOCertificate();
                return (
                  <div className="ceo-certificate">
                    <div className="ceo-cert-ribbon">🏆 OFFICIAL AWARD 🏆</div>
                    <p className="ceo-cert-presented">This certifies that</p>
                    <h3 className="ceo-cert-name">The CEO of {finalResult.business_name} {finalResult.business_icon}</h3>
                    <p className="ceo-cert-completed">successfully ran a 7-day business experiment</p>

                    <div className="ceo-cert-archetype">
                      <span className="archetype-icon">{cert.archetype.icon}</span>
                      <div>
                        <strong className="archetype-title">{cert.archetype.title}</strong>
                        <p className="archetype-line">{cert.archetype.line}</p>
                      </div>
                    </div>

                    <div className="ceo-cert-stats">
                      <span>💵 Rs. {cert.revenue} revenue</span>
                      <span>👥 {cert.customers} customers</span>
                      <span className={cert.profit >= 0 ? 'pos' : 'neg'}>
                        {cert.profit >= 0 ? '+' : ''}Rs. {cert.profit} {cert.profit >= 0 ? 'profit' : 'lesson'}
                      </span>
                    </div>

                    <div className="ceo-cert-grade-row">
                      <div className="ceo-cert-grade">
                        <span className="grade-letter">{cert.grade}</span>
                        <span className="grade-label">CEO Grade</span>
                      </div>
                      <p className="ceo-cert-grade-line">{cert.gradeLine}</p>
                    </div>

                    <div className="ceo-cert-seal">
                      ⭐ Rich Kids Lab ⭐
                    </div>
                  </div>
                );
              })()}

              {/* Money terms glossary — learn the words */}
              <MoneyTerms />

              {/* Balance change */}
              <div className="lab-balance-change">
                <span>Wallet: Rs. {finalResult.balance_before}</span>
                <span className="arrow">→</span>
                <span className={finalResult.is_profit ? 'up' : 'down'}>
                  Rs. {finalResult.balance_after}
                </span>
              </div>

              {/* Real world card */}
              {finalResult.real_world && (
                <div className="lab-real-world">
                  <span>🍎</span>
                  <div>
                    <strong>{finalResult.real_world.title}</strong>
                    <p>{finalResult.real_world.text}</p>
                  </div>
                </div>
              )}

              {/* Reflection */}
              {finalResult.reflection && !botLine && (
                <div className="lab-reflection">
                  <h3>{finalResult.reflection.question}</h3>
                  <div className="lab-reflection-grid">
                    {finalResult.reflection.options.map(opt => (
                      <button key={opt.id} className="lab-reflect-btn" onClick={() => handleReflection(opt.id)}>
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {botLine && (
                <div className="lab-bot-line">
                  <span>🤖</span>
                  <p>{botLine}</p>
                </div>
              )}
            </>
          ) : stateSummary ? (
            /* Finished but no finalResult (resumed) — show summary */
            <div className="lab-final-card">
              <h3>🧪 Experiment Complete</h3>
              <p>Phase: {stateSummary.phase} · Cash: Rs. {stateSummary.cash}</p>
              <p>Revenue: Rs. {stateSummary.total_revenue} · Costs: Rs. {stateSummary.total_costs}</p>
            </div>
          ) : null}

          {/* Post-experiment actions */}
          <div className="lab-post-actions">
            <button className="lab-action-btn save" onClick={() => navigate('/save')}>💰 Save</button>
            <button className="lab-action-btn grow" onClick={() => navigate('/grow')}>📈 Grow</button>
            <button className="lab-action-btn give" onClick={() => navigate('/give')}>❤️ Give</button>
          </div>

          <button className="lab-try-again" onClick={handleTryAgain}>
            🔄 Phir Se Try Karo!
          </button>
        </section>
      )}
    </div>
  );
}
