export const DISTRICTS = [
  {
    id: 'L1',
    rank: 'Money Rookie',
    name: 'Spawn District',
    blurb: 'First drop. Learn money, save a little, make one spend call.',
  },
  {
    id: 'L2',
    rank: 'Paisa Explorer',
    name: 'Fog Market',
    blurb: 'Need vs want. The fog lifts when you choose.',
  },
  {
    id: 'L3',
    rank: 'Smart Saver',
    name: 'Lock-In Peak',
    blurb: 'Goal on the hill. Wait, or spend now?',
  },
  {
    id: 'L4',
    rank: 'Money Strategist',
    name: 'Gatekeep',
    blurb: 'Three doors. You only get one.',
  },
  {
    id: 'L5',
    rank: 'Paisa Pro',
    name: 'Hustle District',
    blurb: 'Stall, cost, profit or loss.',
  },
  {
    id: 'L6',
    rank: 'Pro Max',
    name: 'Risk Biome',
    blurb: 'Invest. Don’t all-in on one bridge.',
  },
  {
    id: 'L7',
    rank: 'Money Champion',
    name: 'The Quad',
    blurb: 'Save, Spend, Grow, Give — one mission.',
  },
  {
    id: 'L8',
    rank: 'Young CEO',
    name: 'Apex Roof',
    blurb: 'The sky den. Long game.',
  },
];

export const QUESTS = {
  L3: {
    start: 650,
    goal: 1000,
    decisions: 3,
    line: 'Aap ke paas Rs. 650 hain. Goal: Rs. 1,000. Sirf 3 decisions. Kya strategy use karoge?',
  },
  L4: {
    start: 800,
    goal: 1200,
    decisions: 4,
    line: 'Rs. 800 ko Rs. 1,200 banana hai. Sirf 4 decisions.',
  },
  L5: {
    start: 900,
    goal: 1400,
    decisions: 4,
    line: 'Rs. 900 se start. Stall chalao. Profit ya loss — 4 decisions, goal Rs. 1,400.',
  },
  L6: {
    start: 1000,
    goal: 1500,
    decisions: 4,
    line: 'Rs. 1,000. Goal Rs. 1,500. Risk biome: sara paisa ek jagah mat lagana.',
  },
  L7: {
    start: 1200,
    goal: 2000,
    decisions: 5,
    line: 'The Quad: Save, Spend, Grow, Give — sab use karo. Rs. 1,200 → Rs. 2,000.',
  },
  L8: {
    start: 2000,
    goal: 3500,
    decisions: 6,
    line: 'Apex Roof. Lamba plan. Rs. 2,000 ko Rs. 3,500. 6 decisions.',
  },
};

export const TOOLS = [
  { id: 'save', label: 'SAVE', hint: 'Bachao', path: '/save' },
  { id: 'spend', label: 'SPEND', hint: 'Kharch', path: '/spend' },
  { id: 'grow', label: 'GROW', hint: 'Barhao', path: '/grow' },
  { id: 'give', label: 'GIVE', hint: 'Do', path: '/give' },
];
