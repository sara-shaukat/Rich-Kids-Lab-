import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createSession, getSession } from '../services/api';
import Mascot from '../components/Mascot';

const STORAGE_KEY = 'rkl_child_id';

const WELCOME_TIPS = [
  "Money follows brother Money follows! 🤖💰",
  "Assalamu Alaikum! Paiso ki duniya mein welcome!",
  "Aaj kya seekhna hai? Paisa? Business? Investment?",
  "Tayyar ho? Apni paiso ki kahani shuru karo!",
];

export default function Welcome() {
  const [amount, setAmount] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const randomTip = WELCOME_TIPS[Math.floor(Math.random() * WELCOME_TIPS.length)];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const value = parseFloat(amount);
    if (!amount || isNaN(value) || value <= 0) {
      setError('Barah-e-karam ek valid amount darj karein jo 0 se zyada ho.');
      return;
    }

    setLoading(true);
    try {
      // Check if a valid session already exists before creating a new one
      const existingId = localStorage.getItem(STORAGE_KEY);
      if (existingId) {
        const existing = await getSession(existingId);
        if (existing) {
          // Valid session found — redirect to dashboard without creating new session
          navigate('/dashboard');
          return;
        }
        // Invalid/expired session — clear it
        localStorage.removeItem(STORAGE_KEY);
      }
      // No valid session — create new one
      const session = await createSession(value);
      localStorage.setItem(STORAGE_KEY, session.anonymous_id);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Kuch ghalt ho gaya. Dobara try karein.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="welcome-container welcome-v2">
      {/* Animated background particles */}
      <div className="welcome-bg-particles">
        <span>💰</span><span>📈</span><span>🚀</span><span>💎</span><span>⭐</span><span>🤲</span>
      </div>

      <div className="welcome-card welcome-card-v2">
        {/* Mascot greeting */}
        <Mascot line={randomTip} mode="hype" size="small" />

        <h1 className="welcome-title welcome-title-v2">Rich Kids Lab</h1>
        <p className="welcome-subtitle welcome-subtitle-v2">
          Apni paiso ki duniya banao! 🌍
        </p>
        <p className="welcome-tagline">
          Seekho. Khelo. Barho. Paisay ka khel mazay se!
        </p>

        <form onSubmit={handleSubmit} className="welcome-form">
          <label className="welcome-label">
            Aap ke paas kitne virtual paisay hain?
          </label>

          <div className="input-group">
            <span className="currency-prefix">Rs.</span>
            <input
              type="number"
              className="money-input"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="500"
              min="1"
              step="1"
              disabled={loading}
            />
          </div>

          {error && <p className="error-text">{error}</p>}

          <button type="submit" className="start-btn start-btn-v2" disabled={loading}>
            {loading ? 'Starting...' : 'Shuru Karein! 🚀'}
          </button>
        </form>

        <p className="welcome-note">
          Ye virtual paisay hain — real paisay nahi. Seekhne ke liye khelo!
        </p>
      </div>
    </div>
  );
}
