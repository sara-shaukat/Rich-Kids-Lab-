import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getVaultMap, passVaultChallenge } from '../services/api';

const STORAGE_KEY = 'rkl_child_id';

/* Node positions on the island (percentage-based for responsive layout) */
const NODE_POS = {
  1: { x: 14, y: 68 },
  2: { x: 28, y: 50 },
  3: { x: 18, y: 32 },
  4: { x: 38, y: 24 },
  5: { x: 56, y: 20 },
  6: { x: 72, y: 36 },
  7: { x: 62, y: 56 },
  8: { x: 82, y: 72 },
};

/* SVG path between two points with a slight curve */
function connPath(x1, y1, x2, y2) {
  const mx = (x1 + x2) / 2;
  const my = Math.min(y1, y2) - 4;
  return `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`;
}

/* Circular progress arc for node ring */
function progressArc(pct, r = 27) {
  if (pct <= 0) return '';
  const c = 30;
  const angle = (Math.min(pct, 100) / 100) * 2 * Math.PI;
  const ex = c + r * Math.sin(angle);
  const ey = c - r * Math.cos(angle);
  const large = pct > 50 ? 1 : 0;
  return `M ${c} ${c - r} A ${r} ${r} 0 ${large} 1 ${ex} ${ey}`;
}

export default function Vault() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [mapData, setMapData] = useState(null);
  const [error, setError] = useState('');
  const [testMode, setTestMode] = useState(false);
  const [testResult, setTestResult] = useState('');

  const childId = localStorage.getItem(STORAGE_KEY);

  const loadMap = async () => {
    if (!childId) { navigate('/'); return; }
    try {
      const data = await getVaultMap(childId);
      setMapData(data);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  useEffect(() => { loadMap(); }, [childId, navigate]);

  const handleTestPassChallenge = async (level) => {
    setTestResult(`Passing Level ${level} challenge...`);
    try {
      const result = await passVaultChallenge(childId, level, 100);
      if (result.level_complete) {
        setTestResult(`Level ${level} COMPLETED! Level ${result.level_unlocked || 'none'} unlocked.`);
      } else {
        setTestResult(`Challenge passed, but level not complete (quests pending).`);
      }
      await loadMap();
    } catch (err) {
      setTestResult(`Error: ${err.message}`);
    }
  };

  if (loading) {
    return <div className="vm-loading"><div className="vm-loading-spinner" /><p>Loading the island...</p></div>;
  }

  if (error) {
    return (
      <div className="vm-error">
        <p>{error}</p>
        <button className="vm-back-btn" onClick={() => navigate('/dashboard')}>← Dashboard</button>
      </div>
    );
  }

  const levels = mapData?.levels || [];
  const completedCount = levels.filter(l => l.status === 'completed').length;

  /* Build connections array */
  const connections = [];
  for (let i = 0; i < levels.length - 1; i++) {
    const curr = levels[i];
    const next = levels[i + 1];
    const p1 = NODE_POS[curr.level];
    const p2 = NODE_POS[next.level];
    if (!p1 || !p2) continue;
    let status = 'locked';
    if (curr.status === 'completed' && next.status === 'completed') status = 'completed';
    else if (curr.status === 'completed') status = 'open';
    connections.push({ from: p1, to: p2, status, fromLevel: curr.level });
  }

  return (
    <div className="vm-container">
      {/* ---- Header ---- */}
      <header className="vm-header">
        <button className="vm-back-btn" onClick={() => navigate('/dashboard')}>← Dashboard</button>
        <div className="vm-title-area">
          <h1 className="vm-title">Money Vault Island</h1>
        </div>
        <div className="vm-progress-pill">
          <span className="vm-progress-text">{completedCount}/{levels.length}</span>
          <div className="vm-progress-track">
            <div className="vm-progress-fill" style={{ width: `${(completedCount / levels.length) * 100}%` }} />
          </div>
        </div>
      </header>

      {/* ---- Test Mode Toggle ---- */}
      {testMode && (
        <div className="vm-test-bar">
          <span className="vm-test-label">Test Mode ON</span>
          {testResult && <span className="vm-test-result">{testResult}</span>}
        </div>
      )}
      <button className="vm-test-toggle" onClick={() => setTestMode(!testMode)}>
        {testMode ? '🧪' : '🔒'}
      </button>

      {/* ---- Isometric World Map ---- */}
      <div className="vm-world">
        <div className="vm-map-frame">

          {/* Terrain SVG */}
          <svg className="vm-terrain" viewBox="0 0 900 600" preserveAspectRatio="none">
            <defs>
              {/* Sky-to-ocean gradient */}
              <linearGradient id="vm-ocean" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#1a6b8a" />
                <stop offset="40%" stopColor="#2196a6" />
                <stop offset="100%" stopColor="#3bbcd4" />
              </linearGradient>
              <linearGradient id="vm-ocean-deep" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#0d4f6b" />
                <stop offset="100%" stopColor="#1a6b8a" />
              </linearGradient>
              {/* Mountain gradients */}
              <linearGradient id="vm-mtn1" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f5f5f5" />
                <stop offset="25%" stopColor="#9e9e9e" />
                <stop offset="60%" stopColor="#6d6052" />
                <stop offset="100%" stopColor="#5d4e3c" />
              </linearGradient>
              <linearGradient id="vm-mtn2" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#e0e0e0" />
                <stop offset="20%" stopColor="#8d8070" />
                <stop offset="100%" stopColor="#5a4d3d" />
              </linearGradient>
              <linearGradient id="vm-mtn3" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#bdbdbd" />
                <stop offset="30%" stopColor="#7a6d5d" />
                <stop offset="100%" stopColor="#4e4232" />
              </linearGradient>
              {/* Sand gradient */}
              <linearGradient id="vm-sand" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#f5e6c8" />
                <stop offset="50%" stopColor="#e8d5a8" />
                <stop offset="100%" stopColor="#dcc9a3" />
              </linearGradient>
              {/* Grass gradient */}
              <linearGradient id="vm-grass" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4a8c2a" />
                <stop offset="100%" stopColor="#3d7a22" />
              </linearGradient>
              {/* Castle wall gradient */}
              <linearGradient id="vm-castle-wall" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#c8b89a" />
                <stop offset="100%" stopColor="#a89878" />
              </linearGradient>
              {/* Water shimmer pattern */}
              <pattern id="vm-waves" x="0" y="0" width="60" height="20" patternUnits="userSpaceOnUse">
                <path d="M 0 10 Q 15 5 30 10 Q 45 15 60 10" stroke="rgba(255,255,255,0.12)" strokeWidth="1.5" fill="none" />
              </pattern>
              <filter id="vm-shadow"><feDropShadow dx="0" dy="3" stdDeviation="3" floodOpacity="0.3" /></filter>
              <filter id="vm-glow"><feGaussianBlur stdDeviation="4" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
            </defs>

            {/* ===== DEEP OCEAN ===== */}
            <rect width="900" height="600" fill="url(#vm-ocean-deep)" />
            <rect width="900" height="600" fill="url(#vm-ocean)" opacity="0.7" />
            {/* Wave pattern overlay */}
            <rect width="900" height="600" fill="url(#vm-waves)" />

            {/* Ocean depth variation */}
            <ellipse cx="120" cy="80" rx="100" ry="60" fill="#0d4f6b" opacity="0.3" />
            <ellipse cx="800" cy="550" rx="120" ry="70" fill="#0d4f6b" opacity="0.25" />

            {/* Surface wave highlights */}
            <path d="M 0,50 Q 40,42 80,50 Q 120,58 160,50" stroke="rgba(255,255,255,0.18)" strokeWidth="2" fill="none" />
            <path d="M 700,30 Q 740,22 780,30 Q 820,38 860,30" stroke="rgba(255,255,255,0.15)" strokeWidth="2" fill="none" />
            <path d="M 30,550 Q 70,542 110,550 Q 150,558 190,550" stroke="rgba(255,255,255,0.12)" strokeWidth="1.5" fill="none" />
            <path d="M 750,570 Q 790,562 830,570 Q 870,578 900,572" stroke="rgba(255,255,255,0.1)" strokeWidth="1.5" fill="none" />
            <path d="M 50,200 Q 80,194 110,200" stroke="rgba(255,255,255,0.12)" strokeWidth="1" fill="none" />
            <path d="M 810,450 Q 840,444 870,450" stroke="rgba(255,255,255,0.1)" strokeWidth="1" fill="none" />

            {/* Ships in ocean */}
            <text x="50" y="105" fontSize="22" opacity="0.7">⛵</text>
            <text x="830" y="530" fontSize="18" opacity="0.6">🚢</text>
            <text x="20" y="480" fontSize="14" opacity="0.5">🐟</text>

            {/* ===== SHALLOW WATER / REEF ===== */}
            <path d="M 60,310 C 50,170 170,30 370,25 C 530,15 700,40 810,120 C 890,185 910,320 880,440 C 850,530 730,590 560,590 C 400,595 240,585 140,540 C 65,500 45,415 60,310 Z"
              fill="#3bbcd4" opacity="0.45" />
            {/* Foam ring around island */}
            <path d="M 80,315 C 72,185 185,50 375,40 C 520,30 685,55 795,130 C 870,190 890,315 865,425 C 840,515 720,575 560,575 C 405,580 255,570 160,530 C 85,495 65,410 80,315 Z"
              fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="4" />

            {/* ===== ISLAND BASE (sand) ===== */}
            <path d="M 110,310 C 105,195 210,75 380,60 C 510,48 660,72 760,140 C 840,195 855,305 835,400 C 815,480 710,540 560,545 C 420,548 270,540 180,500 C 115,465 95,400 110,310 Z"
              fill="url(#vm-sand)" />
            {/* Sand texture dots */}
            {[150,200,280,350,500,580,650,720,180,420,620,750].map((sx, i) => (
              <circle key={`sd${i}`} cx={sx} cy={[470,510,520,530,535,525,500,470,440,540,510,455][i]} r={1.5} fill="#c4a87a" opacity={0.4} />
            ))}

            {/* ===== MAIN GRASSLANDS ===== */}
            <path d="M 145,300 C 140,200 235,100 390,85 C 500,75 635,95 730,155 C 800,200 820,295 800,380 C 785,455 690,510 555,515 C 425,520 290,512 205,475 C 150,445 130,390 145,300 Z"
              fill="url(#vm-grass)" />
            {/* Grass highlights */}
            <ellipse cx="350" cy="320" rx="130" ry="80" fill="#5a9e35" opacity="0.4" />
            <ellipse cx="600" cy="370" rx="110" ry="65" fill="#5a9e35" opacity="0.3" />
            <ellipse cx="250" cy="430" rx="80" ry="45" fill="#5a9e35" opacity="0.25" />

            {/* ===== MOUNTAIN RANGE (dramatic peaks) ===== */}
            {/* Far background mountain (largest, behind everything) */}
            <polygon points="280,200 420,60 560,200" fill="url(#vm-mtn3)" filter="url(#vm-shadow)" />
            {/* Snow cap */}
            <polygon points="390,85 420,60 450,85 440,95 430,80 420,90 410,78 400,92" fill="#f5f5f5" />
            {/* Snow streaks */}
            <line x1="405" y1="100" x2="395" y2="140" stroke="rgba(255,255,255,0.3)" strokeWidth="2" />
            <line x1="435" y1="95" x2="445" y2="135" stroke="rgba(255,255,255,0.25)" strokeWidth="1.5" />

            {/* Left peak */}
            <polygon points="180,240 300,100 420,240" fill="url(#vm-mtn2)" filter="url(#vm-shadow)" />
            {/* Snow cap left */}
            <polygon points="275,120 300,100 325,120 318,132 310,115 300,125 290,112 282,128" fill="#eee" />
            {/* Mountain face shading */}
            <polygon points="300,100 420,240 360,240" fill="rgba(0,0,0,0.1)" />

            {/* Right peak */}
            <polygon points="440,230 570,80 700,230" fill="url(#vm-mtn1)" filter="url(#vm-shadow)" />
            {/* Snow cap right */}
            <polygon points="543,102 570,80 597,102 590,115 582,96 570,108 558,94 550,110" fill="#fff" />
            {/* Snow streaks */}
            <line x1="555" y1="115" x2="545" y2="160" stroke="rgba(255,255,255,0.35)" strokeWidth="2" />
            <line x1="585" y1="110" x2="595" y2="155" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" />
            {/* Mountain face shading */}
            <polygon points="570,80 700,230 635,230" fill="rgba(0,0,0,0.08)" />

            {/* Small foothills */}
            <polygon points="220,260 280,210 340,260" fill="#7a6d5d" opacity="0.5" />
            <polygon points="600,255 650,215 700,255" fill="#7a6d5d" opacity="0.4" />

            {/* ===== DESERT / SANDY AREA (lower right) ===== */}
            <path d="M 580,400 C 610,370 680,360 730,380 C 770,395 790,430 775,470 C 755,505 700,520 650,510 C 600,500 565,465 560,440 C 555,420 560,405 580,400 Z"
              fill="#e8d5a8" />
            {/* Sand dune ridges */}
            <path d="M 600,410 Q 650,395 700,410" stroke="#d4c090" strokeWidth="1.5" fill="none" opacity="0.6" />
            <path d="M 590,435 Q 650,420 720,440" stroke="#d4c090" strokeWidth="1" fill="none" opacity="0.5" />
            <path d="M 610,460 Q 660,448 710,465" stroke="#d4c090" strokeWidth="1" fill="none" opacity="0.4" />
            {/* Palm trees in desert */}
            <text x="620" y="405" fontSize="22">🌴</text>
            <text x="710" y="430" fontSize="18">🌴</text>
            <text x="670" y="475" fontSize="15">🌴</text>
            {/* Cactus */}
            <text x="745" y="450" fontSize="14">🌵</text>

            {/* ===== RIVER (winding through island) ===== */}
            <path d="M 330,65 C 345,110 315,170 340,240 C 360,300 330,370 350,430 C 365,480 345,510 360,545"
              stroke="#3bbcd4" strokeWidth="18" fill="none" strokeLinecap="round" opacity="0.7" />
            <path d="M 332,70 C 347,115 317,175 342,245 C 362,305 332,375 352,435 C 367,485 347,515 362,545"
              stroke="#7dd3f0" strokeWidth="8" fill="none" strokeLinecap="round" opacity="0.45" />
            {/* River foam */}
            <path d="M 335,120 Q 340,125 335,130" stroke="rgba(255,255,255,0.4)" strokeWidth="2" fill="none" />
            <path d="M 345,290 Q 350,295 345,300" stroke="rgba(255,255,255,0.35)" strokeWidth="2" fill="none" />
            <path d="M 340,400 Q 345,405 340,410" stroke="rgba(255,255,255,0.3)" strokeWidth="2" fill="none" />

            {/* Bridge over river */}
            <rect x="325" y="265" width="45" height="20" rx="3" fill="#a08060" />
            <rect x="325" y="265" width="45" height="4" rx="2" fill="#c0a070" />
            <line x1="330" y1="269" x2="330" y2="282" stroke="#8b6f4e" strokeWidth="2" />
            <line x1="338" y1="269" x2="338" y2="282" stroke="#8b6f4e" strokeWidth="2" />
            <line x1="346" y1="269" x2="346" y2="282" stroke="#8b6f4e" strokeWidth="2" />
            <line x1="354" y1="269" x2="354" y2="282" stroke="#8b6f4e" strokeWidth="2" />
            <line x1="362" y1="269" x2="362" y2="282" stroke="#8b6f4e" strokeWidth="2" />

            {/* ===== CASTLE (main, near top-center) ===== */}
            {/* Castle base / main wall */}
            <rect x="410" y="185" width="80" height="50" rx="2" fill="url(#vm-castle-wall)" filter="url(#vm-shadow)" />
            {/* Battlements */}
            <rect x="408" y="180" width="12" height="12" fill="#b8a888" />
            <rect x="424" y="180" width="12" height="12" fill="#b8a888" />
            <rect x="440" y="180" width="12" height="12" fill="#b8a888" />
            <rect x="456" y="180" width="12" height="12" fill="#b8a888" />
            <rect x="472" y="180" width="12" height="12" fill="#b8a888" />
            {/* Left tower */}
            <rect x="400" y="160" width="20" height="75" rx="1" fill="#b0a080" />
            <polygon points="400,160 410,140 420,160" fill="#8b4040" />
            <rect x="406" y="195" width="8" height="12" rx="1" fill="#6d5c40" />
            {/* Right tower */}
            <rect x="480" y="155" width="22" height="80" rx="1" fill="#b0a080" />
            <polygon points="480,155 491,132 502,155" fill="#8b4040" />
            <rect x="486" y="190" width="8" height="12" rx="1" fill="#6d5c40" />
            {/* Gate */}
            <path d="M 440,235 L 440,218 Q 450,210 460,218 L 460,235" fill="#5d4030" />
            {/* Flag on right tower */}
            <line x1="491" y1="132" x2="491" y2="115" stroke="#666" strokeWidth="1.5" />
            <polygon points="491,115 508,120 491,125" fill="#e53935" />
            {/* Castle windows */}
            <rect x="425" y="200" width="5" height="8" rx="1" fill="#5d4e3c" />
            <rect x="465" y="200" width="5" height="8" rx="1" fill="#5d4e3c" />

            {/* Second smaller castle (lower left) */}
            <rect x="225" y="360" width="45" height="30" rx="1" fill="#b8a888" filter="url(#vm-shadow)" />
            <rect x="222" y="356" width="8" height="8" fill="#a89878" />
            <rect x="234" y="356" width="8" height="8" fill="#a89878" />
            <rect x="246" y="356" width="8" height="8" fill="#a89878" />
            <rect x="258" y="356" width="8" height="8" fill="#a89878" />
            <rect x="220" y="340" width="14" height="50" rx="1" fill="#a89878" />
            <polygon points="220,340 227,322 234,340" fill="#8b4040" />
            <line x1="227" y1="322" x2="227" y2="308" stroke="#666" strokeWidth="1" />
            <polygon points="227,308 238,312 227,316" fill="#1565c0" />
            <rect x="256" y="340" width="14" height="50" rx="1" fill="#a89878" />
            <polygon points="256,340 263,325 270,340" fill="#8b4040" />
            <path d="M 240,390 L 240,378 Q 248,372 256,378 L 256,390" fill="#5d4030" />

            {/* ===== FOREST AREAS ===== */}
            {/* Dense forest (left side) */}
            <text x="160" y="250" fontSize="26">🌲</text>
            <text x="185" y="270" fontSize="22">🌲</text>
            <text x="145" y="285" fontSize="20">🌲</text>
            <text x="200" y="245" fontSize="18">🌲</text>
            <text x="170" y="300" fontSize="24">🌲</text>
            <text x="210" y="290" fontSize="16">🌲</text>
            <text x="150" y="320" fontSize="19">🌲</text>

            {/* Scattered trees */}
            <text x="460" y="170" fontSize="18">🌲</text>
            <text x="700" y="260" fontSize="22">🌲</text>
            <text x="735" y="295" fontSize="18">🌲</text>
            <text x="155" y="380" fontSize="18">🌲</text>

            {/* Deciduous trees (meadow area) */}
            <text x="400" y="400" fontSize="22">🌳</text>
            <text x="440" y="420" fontSize="18">🌳</text>
            <text x="520" y="460" fontSize="20">🌳</text>
            <text x="380" y="445" fontSize="16">🌳</text>

            {/* Bushes and flowers */}
            <text x="320" y="360" fontSize="13">🌿</text>
            <text x="480" y="440" fontSize="11">🌿</text>
            <text x="560" y="350" fontSize="12">🌿</text>
            <text x="430" y="340" fontSize="11">🌸</text>
            <text x="510" y="480" fontSize="10">🌺</text>
            <text x="350" y="480" fontSize="10">🌻</text>

            {/* Animals */}
            <text x="530" y="400" fontSize="13">🦌</text>
            <text x="310" y="145" fontSize="14">🦅</text>
            <text x="680" y="340" fontSize="11">🐦</text>
            <text x="450" y="500" fontSize="10">🐇</text>

            {/* Rocks and boulders */}
            <text x="690" y="500" fontSize="16">🪨</text>
            <text x="150" y="465" fontSize="14">🪨</text>
            <text x="760" y="380" fontSize="12">🪨</text>

            {/* Water features */}
            <text x="300" y="480" fontSize="11">🪷</text>
            <text x="340" y="500" fontSize="9">🪷</text>

            {/* Treasure chest near final level */}
            <text x="770" y="440" fontSize="18">💰</text>
            <text x="785" y="450" fontSize="12">✨</text>

            {/* Dirt paths connecting areas */}
            <path d="M 170,400 C 200,360 260,320 320,290 C 370,265 420,250 470,260"
              stroke="#b8a882" strokeWidth="5" fill="none" strokeLinecap="round" opacity="0.45" />
            <path d="M 470,260 C 530,275 580,310 620,340 C 660,370 700,410 740,430"
              stroke="#b8a882" strokeWidth="4" fill="none" strokeLinecap="round" opacity="0.4" />

            {/* ===== CONNECTION PATHS ===== */}
            {connections.map((c, i) => {
              const color = c.status === 'completed' ? '#4caf50' : c.status === 'open' ? '#ffb74d' : '#9e9e9e';
              const dash = c.status === 'locked' ? '6 4' : 'none';
              return (
                <g key={`conn-${i}`}>
                  <path d={connPath(c.from.x * 9, c.from.y * 6, c.to.x * 9, c.to.y * 6)}
                    stroke="rgba(0,0,0,0.2)" strokeWidth="6" fill="none" strokeLinecap="round"
                    strokeDasharray={dash} transform="translate(0,3)" />
                  <path d={connPath(c.from.x * 9, c.from.y * 6, c.to.x * 9, c.to.y * 6)}
                    stroke={color} strokeWidth="3.5" fill="none" strokeLinecap="round"
                    strokeDasharray={dash} />
                  {c.status !== 'locked' && (
                    <circle cx={c.to.x * 9} cy={c.to.y * 6} r="5" fill={color} stroke="rgba(0,0,0,0.2)" strokeWidth="1" />
                  )}
                </g>
              );
            })}

            {/* ===== NODE SHADOWS ===== */}
            {levels.map(level => {
              const pos = NODE_POS[level.level];
              if (!pos) return null;
              return (
                <ellipse key={`shadow-${level.level}`}
                  cx={pos.x * 9} cy={pos.y * 6 + 6} rx="26" ry="10"
                  fill="rgba(0,0,0,0.25)" />
              );
            })}
          </svg>

          {/* ---- Interactive HTML Nodes ---- */}
          {levels.map(level => {
            const pos = NODE_POS[level.level];
            if (!pos) return null;

            const isCompleted = level.status === 'completed';
            const isAvailable = level.status === 'available';
            const isInProgress = level.status === 'in_progress';
            const isLocked = level.status === 'locked';
            const isActive = isAvailable || isInProgress;

            const totalQuests = level.quests_done?.length + (level.quests_pending?.length || 0) || 0;
            const pct = level.level === 1 && level.goal_progress_pct != null
              ? level.goal_progress_pct
              : (totalQuests > 0 ? ((level.quests_done?.length || 0) / totalQuests) * 100 : 0);

            const ringColor = isCompleted ? '#4caf50' : isInProgress ? '#ffb74d' : isAvailable ? '#ffd700' : '#9e9e9e';
            const bgColor = isCompleted ? '#2e7d32' : isInProgress ? '#e65100' : isAvailable ? '#f9a825' : '#757575';
            const icon = isLocked ? '🔒' : level.icon;

            return (
              <div key={level.level} className={`vm-node vm-node-${level.status}`}
                style={{ left: `${pos.x}%`, top: `${pos.y}%` }}>

                {/* Test mode pass button */}
                {testMode && !isLocked && !isCompleted && (
                  <button className="vm-test-pass" onClick={(e) => { e.stopPropagation(); handleTestPassChallenge(level.level); }}>
                    ✅ Pass
                  </button>
                )}

                <button className="vm-node-btn" disabled={isLocked}
                  onClick={() => { if (!isLocked) navigate(`/vault/${level.level}`); }}>

                  {/* Progress arc SVG */}
                  <svg className="vm-node-ring" viewBox="0 0 60 60">
                    <circle cx="30" cy="30" r="27" fill="none" stroke={ringColor} strokeWidth="2.5" opacity="0.2" />
                    {(isCompleted || isInProgress) && pct > 0 && (
                      <path d={progressArc(pct)} fill="none" stroke={ringColor} strokeWidth="3" strokeLinecap="round" />
                    )}
                    {isCompleted && pct === 0 && (
                      <circle cx="30" cy="30" r="27" fill="none" stroke={ringColor} strokeWidth="3" />
                    )}
                  </svg>

                  <div className="vm-node-circle" style={{ background: bgColor }}>
                    <span className="vm-node-icon">{icon}</span>
                  </div>

                  {isActive && <span className="vm-node-ping" />}
                </button>

                <div className="vm-node-label">
                  <span className="vm-node-name">{isLocked ? '???' : level.name}</span>
                  {isCompleted && <span className="vm-node-check">✓</span>}
                  {isInProgress && level.level === 1 && level.goal_name && (
                    <span className="vm-node-quests vm-node-goal">
                      {level.goal_name} ({level.goal_progress_pct || 0}%)
                    </span>
                  )}
                  {isInProgress && level.level !== 1 && (
                    <span className="vm-node-quests">
                      {level.quests_done?.length || 0}q | {level.challenge_passed ? '✅' : '⏳'}
                    </span>
                  )}
                </div>
              </div>
            );
          })}

          {/* Atmospheric fog overlay */}
          <div className="vm-fog" />
        </div>
      </div>

      {/* ---- Side Quests ---- */}
      <div className="vm-actions">
        <button className="vm-action-btn" onClick={() => navigate('/quests')}>
          <span>🗺️</span> Aaj ke Quests
        </button>
      </div>
    </div>
  );
}
