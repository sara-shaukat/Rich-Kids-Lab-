import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DISTRICTS, QUESTS, TOOLS } from '../data/paisaDuniya';

const STORAGE_KEY = 'rkl_child_id';

function statusOf(id, completed, currentId) {
  if (completed.includes(id)) return 'clear';
  if (id === currentId) return 'torch';
  const idx = DISTRICTS.findIndex((d) => d.id === id);
  const cur = DISTRICTS.findIndex((d) => d.id === currentId);
  if (idx === cur + 1) return 'next';
  return 'fog';
}

export default function PaisaMap() {
  const navigate = useNavigate();
  const childId = localStorage.getItem(STORAGE_KEY);
  const [theme, setTheme] = useState('duniya');
  const [completed, setCompleted] = useState(['L1', 'L2']);
  const [currentId, setCurrentId] = useState('L3');
  const [showComplete, setShowComplete] = useState(false);
  const [justCleared, setJustCleared] = useState(null);

  const current = DISTRICTS.find((d) => d.id === currentId);
  const nextDistrict = DISTRICTS[DISTRICTS.findIndex((d) => d.id === currentId) + 1];
  const quest = QUESTS[currentId];
  const nextQuest = nextDistrict ? QUESTS[nextDistrict.id] : null;
  const clearedRank = useMemo(
    () => DISTRICTS.find((d) => d.id === justCleared) || current,
    [justCleared, current],
  );

  const enterNextQuest = () => {
    if (!nextDistrict) {
      setShowComplete(false);
      return;
    }
    setCompleted((prev) => (prev.includes(justCleared) ? prev : [...prev, justCleared]));
    setCurrentId(nextDistrict.id);
    setShowComplete(false);
    setJustCleared(null);
  };

  return (
    <div className={`paisa-map theme-${theme}`}>
      <header className="paisa-map-top">
        <button type="button" className="back-btn" onClick={() => navigate(childId ? '/dashboard' : '/')}>
          ← Wapas
        </button>
        <div className="paisa-map-brand">
          <p className="paisa-map-kicker">Paisa Duniya</p>
          <h1>Money map</h1>
        </div>
        <div className="paisa-rank-plate">
          <span className="paisa-rank-label">Rank</span>
          <strong>{current?.rank}</strong>
          <span className="paisa-rank-place">Abhi: {current?.name}</span>
        </div>
      </header>

      <div className="paisa-theme-row" role="group" aria-label="Map theme">
        <button
          type="button"
          className={theme === 'duniya' ? 'paisa-theme-chip on' : 'paisa-theme-chip'}
          onClick={() => setTheme('duniya')}
        >
          Paisa Duniya
        </button>
        <button
          type="button"
          className={theme === 'roofline' ? 'paisa-theme-chip on' : 'paisa-theme-chip'}
          onClick={() => setTheme('roofline')}
        >
          Roofline
          <span className="paisa-theme-unlock">Spawn clear</span>
        </button>
      </div>

      <ol className="paisa-spine" aria-label="Districts">
        {DISTRICTS.map((d) => {
          const st = statusOf(d.id, completed, currentId);
          return (
            <li key={d.id} className={`paisa-chunk paisa-chunk-${st}`}>
              <div className="paisa-chunk-rail" aria-hidden="true">
                {st === 'torch' && <span className="paisa-torch" title="You are here" />}
                {st === 'clear' && <span className="paisa-stamp" />}
                {st === 'next' && <span className="paisa-gate" />}
                {st === 'fog' && <span className="paisa-fog-dot" />}
              </div>
              <div className="paisa-chunk-body">
                <p className="paisa-chunk-rank">{d.rank}</p>
                <h2>{st === 'fog' ? '???' : d.name}</h2>
                {st !== 'fog' && <p className="paisa-chunk-blurb">{d.blurb}</p>}
                {st === 'fog' && <p className="paisa-chunk-blurb">Band ilaqa. Fog ke peeche.</p>}
                {st === 'torch' && <p className="paisa-chunk-tag">Abhi yahan ho</p>}
                {st === 'clear' && <p className="paisa-chunk-tag">Mission complete</p>}
                {st === 'next' && <p className="paisa-chunk-tag">Agli jagah — pehle yeh mission</p>}
              </div>
            </li>
          );
        })}
      </ol>

      {quest && !showComplete && (
        <section className="paisa-quest" aria-label="Current quest">
          <p className="paisa-quest-kicker">Quest · {current.name}</p>
          <p className="paisa-quest-line">{quest.line}</p>
          <p className="paisa-quest-meta">
            Rs. {quest.start.toLocaleString()} → Rs. {quest.goal.toLocaleString()} · {quest.decisions} decisions
          </p>
          <div className="paisa-tools">
            {TOOLS.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`paisa-tool paisa-tool-${t.id}`}
                onClick={() => childId && navigate(t.path)}
                disabled={!childId}
              >
                <span>{t.label}</span>
                <small>{t.hint}</small>
              </button>
            ))}
          </div>
          {!childId && (
            <p className="paisa-quest-note">Tools dashboard pe chalenge jab session start ho.</p>
          )}
          <button
            type="button"
            className="paisa-primary"
            onClick={() => {
              setJustCleared(currentId);
              setShowComplete(true);
            }}
          >
            Decisions done — check mission
          </button>
        </section>
      )}

      {showComplete && (
        <div className="paisa-complete" role="dialog" aria-labelledby="paisa-complete-title">
          <div className="paisa-complete-card">
            <p className="paisa-complete-kicker">Mission complete</p>
            <h2 id="paisa-complete-title">You passed the {clearedRank.rank} challenge.</h2>
            <p className="paisa-complete-rank">Rank: {clearedRank.rank}</p>
            {nextDistrict && (
              <p className="paisa-complete-unlock">{nextDistrict.name} unlocked.</p>
            )}
            {nextQuest && (
              <div className="paisa-next-quest">
                <p className="paisa-quest-kicker">Next mission</p>
                <p>{nextQuest.line}</p>
              </div>
            )}
            <div className="paisa-tools paisa-tools-preview">
              {TOOLS.map((t) => (
                <span key={t.id} className={`paisa-tool paisa-tool-${t.id}`}>
                  <span>{t.label}</span>
                </span>
              ))}
            </div>
            <button type="button" className="paisa-primary" onClick={enterNextQuest}>
              {nextDistrict ? 'Enter next quest' : 'Stay on Apex Roof'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
