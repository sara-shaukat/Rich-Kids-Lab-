import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { askMentor } from '../services/api';
import { getDashboard } from '../services/api';
import useSpeech from '../hooks/useSpeech';
import Mascot from '../components/Mascot';

const STORAGE_KEY = 'rkl_child_id';

const QUICK_CHIPS = [
  'Mujhe nahi pata, kya karun?',
  'Mera goal kaise complete karun?',
  'Investment kya hoti hai?',
  'Paisay kaise bachaun?',
];

export default function Mentor() {
  const navigate = useNavigate();
  const childId = localStorage.getItem(STORAGE_KEY);

  const [messages, setMessages] = useState([]); // {role, text, urdu?, provider?}
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [autoSpeak, setAutoSpeak] = useState(true);

  const {
    sttSupported,
    listening,
    transcript,
    startListening,
    stopListening,
    micError,
    clearMicError,
    ttsSupported,
    urduVoice,
    speaking,
    speak,
    stopSpeaking,
  } = useSpeech();

  const messagesRef = useRef(null);

  // Auto-scroll to the newest message
  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  useEffect(() => {
    if (!childId) { navigate('/'); return; }
    // Verify the session quietly (dashboard call doubles as the check)
    getDashboard(childId).then((dash) => {
      if (!dash) { localStorage.removeItem(STORAGE_KEY); navigate('/'); }
    });
  }, []);

  if (!childId) return null;

  const canSpeak = ttsSupported && Boolean(urduVoice);

  const sendMessage = async (text) => {
    const message = (text || '').trim();
    if (!message || loading) return;

    setError('');
    clearMicError();
    setInput('');
    const childMsg = { role: 'child', text: message };
    const history = [...messages, childMsg]
      .slice(-10)
      .map((m) => ({ role: m.role, text: m.text }));
    setMessages((prev) => [...prev, childMsg]);
    setLoading(true);

    try {
      const result = await askMentor(childId, message, history);
      const mentorMsg = {
        role: 'mentor',
        text: result.response,
        urdu: result.response_urdu,
        provider: result.provider,
      };
      setMessages((prev) => [...prev, mentorMsg]);
      if (autoSpeak && canSpeak) speak(result.response_urdu);
    } catch (err) {
      setError(err.message || 'Mentor se jawab nahi mila.');
    } finally {
      setLoading(false);
    }
  };

  const handleMicClick = () => {
    if (listening) {
      stopListening(); // stop + send what was heard
    } else {
      startListening((finalText) => sendMessage(finalText));
    }
  };

  return (
    <div className="page-container mentor-page">
      {/* Header */}
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          ← Wapas
        </button>
        <h1 className="page-title">🤖 AI MENTOR</h1>
        {canSpeak && (
          <button
            className={`speaker-toggle ${autoSpeak ? 'on' : 'off'}`}
            onClick={() => { setAutoSpeak(!autoSpeak); if (autoSpeak) stopSpeaking(); }}
            title={autoSpeak ? 'Jawab bol kar sunao' : 'Jawab sirf likha hua'}
          >
            {autoSpeak ? '🔊' : '🔇'}
          </button>
        )}
      </div>

      {/* Paisa Bot */}
      <Mascot
        line="Assalamu Alaikum! Main Paisa Bot hoon — poochho kuch bhi!"
        mode="hype"
        size="small"
      />

      {/* Messages */}
      <div className="chat-messages" ref={messagesRef}>
        {messages.length === 0 && (
          <div className="chat-chips">
            {QUICK_CHIPS.map((chip) => (
              <button key={chip} className="chat-chip" onClick={() => sendMessage(chip)}>
                {chip}
              </button>
            ))}
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={`chat-bubble ${m.role === 'child' ? 'chat-bubble-child' : 'chat-bubble-mentor'}`}
            dir="auto"
          >
            <p className="chat-bubble-text">{m.text}</p>
            {m.role === 'mentor' && (
              <div className="chat-bubble-footer">
                {canSpeak && (
                  <button
                    className="bubble-speak-btn"
                    onClick={() => speak(m.urdu)}
                    title="Dobara suno"
                  >
                    🔊
                  </button>
                )}
                {m.provider && <span className="chat-provider-tag">{m.provider}</span>}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="chat-bubble chat-bubble-mentor chat-typing">
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        )}
      </div>

      {speaking && (
        <button className="stop-speak-btn" onClick={stopSpeaking}>
          ⏹ Ruk jao
        </button>
      )}

      {error && <p className="error-text chat-error">{error}</p>}

      {/* Input row */}
      <div className="chat-input-row">
        <input
          className="chat-input"
          type="text"
          dir="auto"
          value={listening ? (transcript || 'bolo... main sun raha hoon') : input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') sendMessage(input); }}
          placeholder="Paisa Bot se kuch poochho..."
          disabled={loading || listening}
          maxLength={500}
        />
        {sttSupported && (
          <button
            className={`mic-btn ${listening ? 'listening' : ''}`}
            onClick={handleMicClick}
            disabled={loading}
            title={listening ? 'Bas karo — ab bhejo' : 'Bol kar poochho'}
          >
            {listening ? '⏹' : '🎤'}
          </button>
        )}
        <button
          className="chat-send-btn"
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
        >
          ➤
        </button>
      </div>
      {listening && (
        <p className="mic-hint">Sun raha hoon... Urdu mein bolo — thora rukne par khud bhej dunga</p>
      )}
      {!listening && micError && (
        <p className="mic-error" role="alert">🎤 {micError}</p>
      )}
    </div>
  );
}
