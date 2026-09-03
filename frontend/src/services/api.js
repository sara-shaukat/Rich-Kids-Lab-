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

// ---- Money Vault ----

/**
 * Get the Money Vault map state (all 8 levels with lock/unlock status).
 * @param {string} anonymousId
 * @returns {Promise<object>} - { anonymous_id, vault_level, levels: [...] }
 */
export async function getVaultMap(anonymousId) {
  const res = await fetch(`${API_BASE}/vault/map/${anonymousId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Vault map failed to load.');
  }
  return res.json();
}

/**
 * Get the status of a specific level.
 * @param {string} anonymousId
 * @param {number} level - Level number (1-8)
 * @returns {Promise<object>} - { level, name, status, quests_done, challenge_passed, ... }
 */
export async function getVaultLevel(anonymousId, level) {
  const res = await fetch(`${API_BASE}/vault/level/${anonymousId}/${level}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Level status failed to load.');
  }
  return res.json();
}

/**
 * Mark a quest as done within a level.
 * @param {string} anonymousId
 * @param {number} level - Level number (1-8)
 * @param {string} questId - Quest ID to mark as done
 * @returns {Promise<object>} - { quests_done, level_complete }
 */
export async function completeVaultQuest(anonymousId, level, questId) {
  const res = await fetch(`${API_BASE}/vault/level/${level}/quest/${questId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anonymous_id: anonymousId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Quest completion failed.');
  }
  return res.json();
}

/**
 * Mark the level-end challenge as passed.
 * @param {string} anonymousId
 * @param {number} level - Level number (1-8)
 * @param {number} score - Challenge score (default 100)
 * @returns {Promise<object>} - { challenge_passed, level_complete, level_unlocked }
 */
export async function passVaultChallenge(anonymousId, level, score = 100) {
  const res = await fetch(`${API_BASE}/vault/level/${level}/challenge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anonymous_id: anonymousId, score }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Challenge completion failed.');
  }
  return res.json();
}

/**
 * Get all quests for a specific vault level.
 * @param {string} anonymousId
 * @param {number} level - Level number (1-8)
 * @returns {Promise<object>} - { level, quests: [...] }
 */
export async function getVaultLevelQuests(anonymousId, level) {
  const res = await fetch(`${API_BASE}/vault/quests/${anonymousId}/${level}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to load level quests.');
  }
  return res.json();
}

/**
 * Resolve a vault quest choice (scenario → choice → consequence).
 * @param {string} anonymousId
 * @param {number} level - Level number (1-8)
 * @param {string} questId - Quest ID
 * @param {string} choiceId - Choice ID
 * @returns {Promise<object>} - { quest_id, choice_id, headline, outcome_lines, ... }
 */
export async function resolveVaultQuest(anonymousId, level, questId, choiceId) {
  const res = await fetch(`${API_BASE}/vault/quest/${level}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      anonymous_id: anonymousId, 
      quest_id: questId,
      choice_id: choiceId 
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Quest resolution failed.');
  }
  return res.json();
}

/**
 * Submit a reflection answer for a vault quest.
 * @param {string} anonymousId
 * @param {string} questId - Quest ID
 * @param {string} answerId - Reflection answer ID
 * @returns {Promise<object>} - { bot_line }
 */
export async function submitVaultReflection(anonymousId, questId, answerId) {
  const res = await fetch(`${API_BASE}/vault/quest/reflect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      anonymous_id: anonymousId, 
      quest_id: questId,
      answer_id: answerId 
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Reflection submission failed.');
  }
  return res.json();
}

/**
 * Get the level-end challenge questions.
 * @param {string} anonymousId
 * @param {number} level - Level number (1-8)
 * @returns {Promise<object>} - { level, title, pass_threshold, questions: [...] }
 */
export async function getVaultChallenge(anonymousId, level) {
  const res = await fetch(`${API_BASE}/vault/challenge/${anonymousId}/${level}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to load challenge.');
  }
  return res.json();
}

/**
 * Submit answers for a level challenge.
 * @param {string} anonymousId
 * @param {number} level - Level number (1-8)
 * @param {object} answers - { questionId: answerId }
 * @returns {Promise<object>} - { passed, score, correct, total, results, level_complete, level_unlocked }
 */
export async function submitVaultChallenge(anonymousId, level, answers) {
  const res = await fetch(`${API_BASE}/vault/challenge/${level}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anonymous_id: anonymousId, answers }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Challenge submission failed.');
  }
  return res.json();
}

// ---- Money Lab V2 — 7-Day Experiment ----

// ---- Level 1 — First Goal ----

/**
 * Get the Level 1 goal status (goal info, progress, completion state).
 * @param {string} anonymousId
 * @returns {Promise<{has_goal: boolean, goal: object|null, level_complete: boolean, reflection_done: boolean}>}
 */
export async function getLevel1Goal(anonymousId) {
  const res = await fetch(`${API_BASE}/vault/goal/${anonymousId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to load Level 1 goal.');
  }
  return res.json();
}

/**
 * Complete Level 1 after goal reflection.
 * @param {string} anonymousId
 * @param {string} reflectionAnswer
 * @returns {Promise<{level_complete: boolean, level_unlocked: number|null, already_completed: boolean}>}
 */
export async function completeLevel1(anonymousId, reflectionAnswer) {
  const res = await fetch(`${API_BASE}/vault/goal/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      anonymous_id: anonymousId,
      reflection_answer: reflectionAnswer,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to complete Level 1.');
  }
  return res.json();
}

/**
 * Get Level 1 completion certificate data.
 * @param {string} anonymousId
 * @returns {Promise<object>} - certificate data
 */
export async function getCertificate(anonymousId) {
  const res = await fetch(`${API_BASE}/vault/certificate/${anonymousId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to load certificate.');
  }
  return res.json();
}

/**
 * Get Money Report Card for a child.
 * @param {string} anonymousId
 * @returns {Promise<object>} - report card data with grades + commentary
 */
export async function getReportCard(anonymousId) {
  const res = await fetch(`${API_BASE}/vault/reportcard/${anonymousId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to load report card.');
  }
  return res.json();
}

/**
 * Start a Money Lab experiment — grants Rs. 500 virtual money.
 * @param {string} anonymousId
 * @returns {Promise<object>} - { activity_id, balance, grant, businesses, investment_options, pricing_options }
 */
export async function startMoneyLab(anonymousId) {
  const res = await fetch(`${API_BASE}/vault/lab/start/${anonymousId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to start experiment.');
  }
  return res.json();
}

/**
 * Get current experiment state (for recovery / polling).
 * @param {string} anonymousId
 * @returns {Promise<object>} - { activity_id, state, business, wallet_balance }
 */
export async function getLabState(anonymousId) {
  const res = await fetch(`${API_BASE}/vault/lab/state/${anonymousId}`);
  if (!res.ok) return null;
  return res.json();
}

/**
 * Submit business/investment/pricing choices and simulate Day 1.
 * @param {string} anonymousId
 * @param {string} businessId
 * @param {string} investment
 * @param {string} pricing
 * @returns {Promise<object>} - Day 1 result + state summary
 */
export async function setupMoneyLab(anonymousId, businessId, investment, pricing) {
  const res = await fetch(`${API_BASE}/vault/lab/setup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      anonymous_id: anonymousId,
      business_id: businessId,
      investment,
      pricing,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Setup failed.');
  }
  return res.json();
}

/**
 * Advance to the next day — returns result, decision prompt, or final results.
 * @param {string} anonymousId
 * @returns {Promise<object>}
 */
export async function advanceMoneyLab(anonymousId) {
  const res = await fetch(`${API_BASE}/vault/lab/advance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anonymous_id: anonymousId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to advance.');
  }
  return res.json();
}

/**
 * Apply a mid-game decision and advance to the next day.
 * @param {string} anonymousId
 * @param {string} decisionId
 * @returns {Promise<object>}
 */
export async function decideMoneyLab(anonymousId, decisionId) {
  const res = await fetch(`${API_BASE}/vault/lab/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      anonymous_id: anonymousId,
      decision_id: decisionId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Decision failed.');
  }
  return res.json();
}

/**
 * Submit reflection for a Money Lab experiment.
 * @param {string} anonymousId
 * @param {string} reflectionId
 * @returns {Promise<object>} - { bot_line }
 */
export async function reflectMoneyLab(anonymousId, reflectionId) {
  const res = await fetch(`${API_BASE}/vault/lab/reflect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      anonymous_id: anonymousId,
      reflection_id: reflectionId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Reflection failed.');
  }
  return res.json();
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
 * Generate AI-powered business ideas based on child's interests.
 * @param {string} anonymousId
 * @param {string[]} interests - array of interest IDs
 * @returns {Promise<object>} - { ideas: [...], message: string }
 */
export async function generateAIIdeas(anonymousId, interests) {
  const res = await fetch(`${API_BASE}/grow/ai-ideas`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anonymous_id: anonymousId, interests }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'AI idea generation failed.');
  }
  return res.json();
}

/**
 * Start a business simulation with an AI-generated business idea.
 * @param {string} anonymousId
 * @param {object} businessIdea - the full business idea object from generateAIIdeas
 * @returns {Promise<object>}
 */
export async function startAIBusiness(anonymousId, businessIdea) {
  const res = await fetch(`${API_BASE}/grow/ai-business`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anonymous_id: anonymousId, business_idea: businessIdea }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'AI business simulation failed.');
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
