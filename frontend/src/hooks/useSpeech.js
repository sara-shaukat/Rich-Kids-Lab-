import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * useSpeech — voice input (SpeechRecognition, ur-PK) and voice output
 * (speechSynthesis with an Urdu voice) for the AI Mentor.
 *
 * All Web Speech APIs are browser built-ins: free, no keys, no dependencies.
 * Every capability degrades gracefully — the chat always works with text.
 *
 * Listening flow (kid-friendly):
 *   tap 🎤 → listen CONTINUOUSLY (pauses to think are fine) → auto-send
 *   ~2.5s after the last heard word, or right away when the kid taps ⏹.
 *   Failures (permission denied, network, silence...) are surfaced as
 *   Roman Urdu hints via `micError` — never silently swallowed.
 */

// Quiet pause after speech before auto-sending (ms)
const AUTO_SEND_SILENCE_MS = 2500;
// Hard stop when nothing at all is said (ms)
const NO_SPEECH_TIMEOUT_MS = 10000;

// Kid-friendly hints for SpeechRecognition error codes
const MIC_ERROR_HINTS = {
  'not-allowed':
    'Mic ki permission chahiye! Address bar ke 🔒 (ya 🎤) icon par click kar ke Microphone "Allow" karo.',
  'service-not-allowed':
    'Mic ki permission chahiye! Browser settings mein is site ke liye Microphone "Allow" karo.',
  'audio-capture':
    'Mic nahi mil raha. Check karo ke microphone theek se laga hai.',
  'network':
    'Voice service se connection nahi ho paya. Internet check karo — ya type kar ke bhej do.',
  'language-not-supported':
    'Is browser mein Urdu voice input available nahi. Type kar ke bhej do.',
  'no-speech':
    'Kuch sunayi nahi diya. Mic ke qareeb aa kar phir se bolo!',
};

export default function useSpeech() {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState(''); // live (interim) transcript
  const [speaking, setSpeaking] = useState(false);
  const [micError, setMicError] = useState(''); // why the mic stopped early

  // Urdu TTS voice (loaded async in most browsers)
  const [urduVoice, setUrduVoice] = useState(null);
  const recognitionRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const noSpeechTimerRef = useRef(null);
  const finalTextRef = useRef('');
  const onFinalRef = useRef(null);
  const sawErrorRef = useRef(false);

  const SpeechRecognitionClass =
    typeof window !== 'undefined' &&
    (window.SpeechRecognition || window.webkitSpeechRecognition);

  const sttSupported = Boolean(SpeechRecognitionClass);
  const ttsSupported =
    typeof window !== 'undefined' && 'speechSynthesis' in window;

  // Pick an Urdu voice once the voice list loads
  useEffect(() => {
    if (!ttsSupported) return undefined;
    const pickVoice = () => {
      const voices = window.speechSynthesis.getVoices();
      const urdu = voices.find((v) => v.lang && v.lang.toLowerCase().startsWith('ur'));
      setUrduVoice(urdu || null);
    };
    pickVoice();
    window.speechSynthesis.addEventListener('voiceschanged', pickVoice);
    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', pickVoice);
    };
  }, [ttsSupported]);

  // Stop everything when the hook unmounts
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch { /* ignore */ }
      }
      clearTimers();
      if (ttsSupported) window.speechSynthesis.cancel();
    };
  }, [ttsSupported]);

  const clearTimers = () => {
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    if (noSpeechTimerRef.current) clearTimeout(noSpeechTimerRef.current);
    silenceTimerRef.current = null;
    noSpeechTimerRef.current = null;
  };

  /**
   * Start listening. onFinal(transcript) fires once with everything heard.
   * Keeps the mic open while the kid pauses to think; auto-sends after a
   * short silence or when stopListening() is called. Sets `micError` with a
   * kid-friendly hint when the browser refuses (permission, network, ...).
   */
  const startListening = useCallback(
    (onFinal) => {
      if (!sttSupported || recognitionRef.current) return;

      setMicError('');
      // Don't let the mic hear the bot's own voice
      if (ttsSupported) window.speechSynthesis.cancel();

      const recognition = new SpeechRecognitionClass();
      recognition.lang = 'ur-PK'; // kids speak Urdu
      recognition.interimResults = true;
      recognition.continuous = true; // pauses to think are fine — no cut-off

      finalTextRef.current = '';
      onFinalRef.current = onFinal;
      sawErrorRef.current = false;

      recognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const result = event.results[i];
          if (result.isFinal) {
            finalTextRef.current += result[0].transcript;
          } else {
            interim += result[0].transcript;
          }
        }
        const heard = (finalTextRef.current + interim).trim();
        setTranscript(heard);

        // Re-arm the auto-send clock on every new sound
        clearTimers();
        if (heard) {
          silenceTimerRef.current = setTimeout(() => {
            try { recognition.stop(); } catch { /* ignore */ }
          }, AUTO_SEND_SILENCE_MS);
        } else {
          noSpeechTimerRef.current = setTimeout(() => {
            try { recognition.stop(); } catch { /* ignore */ }
          }, NO_SPEECH_TIMEOUT_MS);
        }
      };

      recognition.onerror = (event) => {
        if (event.error === 'aborted') return; // deliberate cancel — not a failure
        sawErrorRef.current = true;
        setMicError(
          MIC_ERROR_HINTS[event.error] ||
          'Mic mein masla aaya. Dobara try karo — ya type kar ke bhej do.'
        );
      };

      recognition.onend = () => {
        clearTimers();
        recognitionRef.current = null;
        setListening(false);
        setTranscript('');
        const text = finalTextRef.current.trim();
        const cb = onFinalRef.current;
        onFinalRef.current = null;
        if (text && cb) {
          cb(text);
        } else if (!text && !sawErrorRef.current) {
          // Ended without hearing anything and without a reported error
          setMicError('Kuch sunayi nahi diya. Dobara 🎤 dabao aur bolo!');
        }
      };

      recognitionRef.current = recognition;
      setListening(true);
      setTranscript('');

      // If the kid never speaks at all, stop gracefully after a while
      noSpeechTimerRef.current = setTimeout(() => {
        try { recognition.stop(); } catch { /* ignore */ }
      }, NO_SPEECH_TIMEOUT_MS);

      try {
        recognition.start();
      } catch {
        clearTimers();
        recognitionRef.current = null;
        setListening(false);
      }
    },
    [sttSupported, ttsSupported, SpeechRecognitionClass],
  );

  /**
   * Stop listening and send whatever was heard so far.
   * (Tap ⏹ after speaking = send now — friendlier than discarding.)
   */
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { /* ignore */ }
    }
  }, []);

  /** Dismiss the mic hint (e.g. when sending a typed message). */
  const clearMicError = useCallback(() => setMicError(''), []);

  /** Speak Urdu-script text with the Urdu voice. */
  const speak = useCallback(
    (text) => {
      if (!ttsSupported || !text) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'ur-PK';
      utterance.rate = 0.95; // slightly slower for kids
      if (urduVoice) utterance.voice = urduVoice;
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);
      setSpeaking(true);
      window.speechSynthesis.speak(utterance);
    },
    [ttsSupported, urduVoice],
  );

  /** Stop any speech in progress. */
  const stopSpeaking = useCallback(() => {
    if (ttsSupported) window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [ttsSupported]);

  return {
    // input
    sttSupported,
    listening,
    transcript,
    startListening,
    stopListening,
    micError,
    clearMicError,
    // output
    ttsSupported,
    urduVoice,
    speaking,
    speak,
    stopSpeaking,
  };
}
