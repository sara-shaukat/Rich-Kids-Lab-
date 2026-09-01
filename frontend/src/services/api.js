/**
 * API service module — all backend calls in one place.
 * The Vite dev server proxies /api to localhost:8000.
 */

const API_BASE = '/api';

/**
 * Create a new child session with starting virtual money.
 * @param {number} startingBalance - must be > 0
 * @returns {Promise<{anonymous_id: string, wallet: {balance: string}, active_goal: object|null}>}
 */
export async function createSession(startingBalance) {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ starting_balance: startingBalance }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create session (${res.status})`);
  }
  return res.json();
}

/**
 * Get an existing child session by anonymous ID.
 * @param {string} anonymousId
 * @returns {Promise<{anonymous_id: string, wallet: {balance: string}, active_goal: object|null}>}
 */
export async function getSession(anonymousId) {
  const res = await fetch(`${API_BASE}/sessions/${anonymousId}`);
  if (!res.ok) {
    return null; // Session not found — caller should clear localStorage
  }
  return res.json();
}

/**
 * Get dashboard summary for a child.
 * @param {string} anonymousId
 * @returns {Promise<object>}
 */
export async function getDashboard(anonymousId) {
  const res = await fetch(`${API_BASE}/dashboard/${anonymousId}`);
  if (!res.ok) {
    return null;
  }
  return res.json();
}

/**
 * Health check.
 */
export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  return res.ok;
}

// ---- Goals ----

/**
 * Create a new goal.
 * @param {string} anonymousId
 * @param {string} name
 * @param {number} targetAmount
 * @returns {Promise<object>}
 */
export async function createGoal(anonymousId, name, targetAmount) {
  const res = await fetch(`${API_BASE}/goals`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      anonymous_id: anonymousId,
      name,
      target_amount: targetAmount,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Goal create failed.');
  }
  return res.json();
}

/**
 * Get all goals for a child.
 * @param {string} anonymousId
 * @returns {Promise<object[]>}
 */
export async function getGoals(anonymousId) {
  const res = await fetch(`${API_BASE}/goals/${anonymousId}`);
  if (!res.ok) return [];
  return res.json();
}

/**
 * Save money toward a goal.
 * @param {number} goalId
 * @param {string} anonymousId
 * @param {number} amount
 * @returns {Promise<object>}
 */
export async function saveToGoal(goalId, anonymousId, amount) {
  const res = await fetch(`${API_BASE}/goals/${goalId}/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      anonymous_id: anonymousId,
      amount,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Save failed.');
  }
  return res.json();
}

// ---- Spend ----

/**
 * Get spend scenarios for a child (with affordability flags).
 * @param {string} anonymousId
 * @returns {Promise<object>}
 */
export async function getSpendScenarios(anonymousId) {
  const res = await fetch(`${API_BASE}/transactions/spend/scenarios/${anonymousId}`);
  if (!res.ok) {
    throw new Error('Failed to load spend scenarios.');
  }
  return res.json();
}

/**
 * Spend on a selected option.
 * @param {string} anonymousId
 * @param {string} optionId
 * @returns {Promise<object>}
 */
export async function spend(anonymousId, optionId) {
  const res = await fetch(`${API_BASE}/transactions/spend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      anonymous_id: anonymousId,
      option_id: optionId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Spend failed.');
  }
  return res.json();
}

// ---- Grow ----

/**
 * Get grow templates (business + skills + investment options).
 * @param {string} anonymousId
 * @returns {Promise<object>}
 */
export async function getGrowTemplates(anonymousId) {
  const res = await fetch(`${API_BASE}/grow/templates/${anonymousId}`);
  if (!res.ok) {
    throw new Error('Failed to load GROW templates.');
  }
  return res.json();
}

/**
 * Start a business simulation.
 * @param {string} anonymousId
 * @param {string} templateId
 * @returns {Promise<object>}
 */
export async function startBusiness(anonymousId, templateId) {
  const res = await fetch(`${API_BASE}/grow/business`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anonymous_id: anonymousId, template_id: templateId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Business failed.');
  }
  return res.json();
}

/**
 * Get personalized business recommendations based on interests.
 * @param {string} anonymousId
 * @param {string[]} interests
 * @returns {Promise<object>}
 */
export async function recommendBusinesses(anonymousId, interests) {
  const res = await fetch(`${API_BASE}/grow/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anonymous_id: anonymousId, interests }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Recommendation failed.');
  }
  return res.json();
}

/**
 * Run an investment simulation.
 * @param {string} anonymousId
 * @param {number} amount
 * @param {string} riskLevel - 'low', 'medium', or 'high'
 * @returns {Promise<object>}
 */
export async function invest(anonymousId, amount, riskLevel) {
  const res = await fetch(`${API_BASE}/grow/invest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anonymous_id: anonymousId, amount, risk_level: riskLevel }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Investment failed.');
  }
  return res.json();
}

/**
 * Explore a skill card and optionally complete a challenge.
 * @param {string} anonymousId
 * @param {string} skillId
 * @param {string|null} practiceAnswer - legacy practice answer
 * @param {string|null} challengeAnswer - challenge option ID ('a','b','c','d')
 * @param {string|null} practiceText - optional free-text practice (e.g. Writing skill)
 * @returns {Promise<object>}
 */
export async function exploreSkill(anonymousId, skillId, practiceAnswer = null, challengeAnswer = null, practiceText = null) {
  const res = await fetch(`${API_BASE}/grow/skill`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      anonymous_id: anonymousId,
      skill_id: skillId,
      practice_answer: practiceAnswer,
      challenge_answer: challengeAnswer,
      practice_text: practiceText,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Skill exploration failed.');
  }
  return res.json();
}

// ---- Quests ----

/**
 * Get the 3 quest cards with their current states
 * (locked / available / completed).
 * @param {string} anonymousId
 * @returns {Promise<{anonymous_id: string, quests: object[]}>}
 */
export async function getQuests(anonymousId) {
  const res = await fetch(`${API_BASE}/quests/${anonymousId}`);
  if (!res.ok) {
    throw new Error('Failed to load quests.');
  }
  return res.json();
}

/**
 * Resolve a quest choice — executes the real wallet/goal action.
 * @param {string} anonymousId
 * @param {string} questId
 * @param {string} choiceId
 * @returns {Promise<object>}
 */
export async function resolveQuest(anonymousId, questId, choiceId) {
  const res = await fetch(`${API_BASE}/quests/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      anonymous_id: anonymousId,
      quest_id: questId,
      choice_id: choiceId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Quest resolve failed.');
  }
  return res.json();
}

/**
 * Store the child's reflection answer on a completed quest.
 * @param {string} anonymousId
 * @param {string} questId
 * @param {string} answerId
 * @returns {Promise<{quest_id: string, answer_id: string, bot_line: string}>}
 */
export async function submitQuestReflection(anonymousId, questId, answerId) {
  const res = await fetch(`${API_BASE}/quests/reflect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      anonymous_id: anonymousId,
      quest_id: questId,
      answer_id: answerId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Reflection failed.');
  }
  return res.json();
}

// ---- Mentor ----

/**
 * Ask the AI Mentor a question. History lives client-side (SPEC §16).
 * @param {string} anonymousId
 * @param {string} message
 * @param {Array<{role: "child"|"mentor", text: string}>} history
 * @returns {Promise<{response: string, response_urdu: string, provider: string}>}
 */
export async function askMentor(anonymousId, message, history = []) {
  const res = await fetch(`${API_BASE}/mentor`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      anonymous_id: anonymousId,
      message,
      history,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Mentor failed.');
  }
  return res.json();
}

// ---- Give ----

/**
 * Get available cause categories for giving.
 * @returns {Promise<object[]>}
 */
export async function getCauses() {
  const res = await fetch(`${API_BASE}/transactions/give/causes`);
  if (!res.ok) {
    throw new Error('Failed to load causes.');
  }
  return res.json();
}

/**
 * Donate virtual money to a cause.
 * @param {string} anonymousId
 * @param {number} amount
 * @param {string|null} causeId
 * @returns {Promise<object>}
 */
export async function giveDonation(anonymousId, amount, causeId = null) {
  const res = await fetch(`${API_BASE}/transactions/give`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      anonymous_id: anonymousId,
      amount,
      cause_id: causeId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Donation failed.');
  }
  return res.json();
}
