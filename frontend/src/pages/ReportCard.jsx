import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getReportCard } from '../services/api';

/**
 * ReportCard — AI Money Report Card.
 * Displays grades across 5 financial skill categories,
 * overall GPA, and an AI-generated commentary paragraph.
 */
export default function ReportCard() {
  const { anonymousId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!anonymousId) return;
    getReportCard(anonymousId)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [anonymousId]);

  if (loading) {
    return (
      <div className="rc-loading">
        <div className="rc-spinner" />
        <p>Generating your Money Report Card...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rc-error">
        <div className="rc-error-icon">📊</div>
        <h2>Report card not available</h2>
        <p>{error}</p>
        <button className="rc-back-btn" onClick={() => navigate('/dashboard')}>
          ← Back to Dashboard
        </button>
      </div>
    );
  }

  const gpaLabel =
    data.overall_gpa >= 3.5 ? 'Outstanding!' :
    data.overall_gpa >= 2.5 ? 'Good progress!' :
    data.overall_gpa >= 1.5 ? 'Keep learning!' :
    'Just getting started!';

  const gpaColor =
    data.overall_gpa >= 3.5 ? '#4CAF70' :
    data.overall_gpa >= 2.5 ? '#D9A441' :
    data.overall_gpa >= 1.5 ? '#E9785C' :
    '#6B6B6B';

  return (
    <div className="rc-page">
      {/* Toolbar */}
      <div className="rc-toolbar">
        <button className="rc-back-btn" onClick={() => navigate(-1)}>← Back</button>
        <button className="rc-print-btn" onClick={() => window.print()}>
          🖨️ Print / Save PDF
        </button>
        <Link to="/dashboard" className="rc-dash-link">Dashboard</Link>
      </div>

      {/* Report card */}
      <div className="rc-card">
        {/* Header */}
        <div className="rc-header">
          <span className="rc-logo">🏦</span>
          <h1 className="rc-org">Rich Kids Lab</h1>
          <div className="rc-divider" />
          <h2 className="rc-title">Money Report Card</h2>
          <p className="rc-subtitle">Your Financial Skills Assessment</p>
          <p className="rc-id">{anonymousId}</p>
        </div>

        {/* Grades table */}
        <div className="rc-grades">
          <div className="rc-grades-header">
            <span className="rc-col-subject">Subject</span>
            <span className="rc-col-score">Score</span>
            <span className="rc-col-grade">Grade</span>
          </div>
          {data.categories.map((cat) => (
            <div key={cat.id} className="rc-grade-row">
              <div className="rc-col-subject">
                <span className="rc-cat-icon">{cat.icon}</span>
                <div className="rc-cat-info">
                  <span className="rc-cat-name">{cat.name}</span>
                  <span className="rc-cat-detail">{cat.detail}</span>
                </div>
              </div>
              <div className="rc-col-score">
                <div className="rc-score-bar-bg">
                  <div
                    className="rc-score-bar-fill"
                    style={{
                      width: `${cat.score}%`,
                      background: cat.score >= 75 ? '#4CAF70' :
                                  cat.score >= 55 ? '#D9A441' :
                                  cat.score >= 35 ? '#E9785C' : '#ccc',
                    }}
                  />
                </div>
                <span className="rc-score-num">{cat.score}%</span>
              </div>
              <div className="rc-col-grade">
                <span
                  className="rc-grade-badge"
                  style={{
                    background: cat.grade === 'A' ? '#4CAF70' :
                                cat.grade === 'B' ? '#D9A441' :
                                cat.grade === 'C' ? '#E9785C' : '#ccc',
                    color: cat.grade <= 'B' ? '#fff' : '#242424',
                  }}
                >
                  {cat.grade}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Overall GPA */}
        <div className="rc-gpa-section">
          <div className="rc-gpa-row">
            <span className="rc-gpa-label">Overall GPA</span>
            <span className="rc-gpa-value" style={{ color: gpaColor }}>
              {data.overall_gpa.toFixed(1)} / 4.0
            </span>
          </div>
          <p className="rc-gpa-tag" style={{ color: gpaColor }}>{gpaLabel}</p>
        </div>

        {/* AI Commentary */}
        {data.commentary && (
          <div className="rc-commentary">
            <div className="rc-commentary-header">
              <span className="rc-commentary-icon">🤖</span>
              <h3 className="rc-commentary-title">
                Paisa Bot says:
                {data.ai_generated && (
                  <span className="rc-ai-badge">AI</span>
                )}
              </h3>
            </div>
            <p className="rc-commentary-text">{data.commentary}</p>
          </div>
        )}

        {/* Stats summary */}
        <div className="rc-stats-strip">
          <div className="rc-mini-stat">
            <span className="rc-mini-val">{data.stats.total_transactions}</span>
            <span className="rc-mini-label">Decisions</span>
          </div>
          <div className="rc-mini-stat">
            <span className="rc-mini-val">Rs. {data.stats.total_saved?.toLocaleString() || 0}</span>
            <span className="rc-mini-label">Saved</span>
          </div>
          <div className="rc-mini-stat">
            <span className="rc-mini-val">{data.stats.businesses_tried}</span>
            <span className="rc-mini-label">Businesses</span>
          </div>
          <div className="rc-mini-stat">
            <span className="rc-mini-val">{data.stats.skills_learned}</span>
            <span className="rc-mini-label">Skills</span>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="rc-actions">
        <Link to={`/certificate/${anonymousId}`} className="rc-cert-link">
          📜 View Certificate
        </Link>
        <Link to="/dashboard" className="rc-continue-btn">
          Continue Learning →
        </Link>
      </div>
    </div>
  );
}
