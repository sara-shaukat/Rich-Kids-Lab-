import { useState, useEffect } from 'react';

/**
 * Paisa Bot — CSS mascot with speech bubble.
 * 
 * Props:
 *   line: string — the text to show in speech bubble
 *   mode: "hype" | "roast" — visual mode (green glow / red tinge)
 *   size: "small" | "normal" | "large" — mascot size
 *   onClick: optional callback when mascot is clicked
 */
export default function Mascot({ line = '', mode = 'hype', size = 'normal', onClick }) {
  const [displayText, setDisplayText] = useState('');
  const [typing, setTyping] = useState(false);

  // Typewriter effect
  useEffect(() => {
    if (!line) {
      setDisplayText('');
      return;
    }
    setTyping(true);
    setDisplayText('');
    let i = 0;
    const interval = setInterval(() => {
      if (i < line.length) {
        setDisplayText(line.slice(0, i + 1));
        i++;
      } else {
        setTyping(false);
        clearInterval(interval);
      }
    }, 25);
    return () => clearInterval(interval);
  }, [line]);

  const sizeClass = size === 'small' ? 'mascot-small' : size === 'large' ? 'mascot-large' : '';

  return (
    <div className={`mascot-container mascot-${mode} ${sizeClass}`} onClick={onClick}>
      {/* Speech Bubble */}
      {line && (
        <div className={`speech-bubble speech-${mode}`}>
          <p className="speech-text">
            {displayText}
            {typing && <span className="cursor-blink">|</span>}
          </p>
          <div className="speech-tail" />
        </div>
      )}

      {/* Mascot Character */}
      <div className="mascot-body">
        {/* Money bag hat */}
        <div className="mascot-hat">
          <span className="hat-symbol">💰</span>
        </div>

        {/* Face */}
        <div className="mascot-face">
          {/* Eyes */}
          <div className="mascot-eyes">
            <div className={`eye eye-left ${mode === 'roast' ? 'eye-roast' : ''}`} />
            <div className={`eye eye-right ${mode === 'roast' ? 'eye-roast' : ''}`} />
          </div>

          {/* Mouth */}
          <div className={`mascot-mouth mouth-${mode}`} />

          {/* Cheeks (blush when hype) */}
          {mode === 'hype' && (
            <div className="mascot-cheeks">
              <div className="cheek cheek-left" />
              <div className="cheek cheek-right" />
            </div>
          )}
        </div>
      </div>

      {/* Mode indicator */}
      <div className={`mascot-indicator indicator-${mode}`}>
        {mode === 'roast' ? '🔥' : '✨'}
      </div>
    </div>
  );
}
