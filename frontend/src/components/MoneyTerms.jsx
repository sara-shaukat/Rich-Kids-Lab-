import { useState } from 'react';

// Kid-friendly financial glossary — the story of one rupee:
// price set → revenue earned → costs paid → profit or loss
const TERMS = [
  {
    icon: '🏷️',
    name: 'Price (Qeemat)',
    formula: 'Price = ek item ki qeemat',
    desc: 'Aap decide karte ho ki ek item kitne ka bechna hai. Sasti price = zyada customers. Mehngi price = kam customers, par har sale mein zyada paisa!',
  },
  {
    icon: '💵',
    name: 'Revenue (Kamai)',
    formula: 'Revenue = Items Sold × Price',
    desc: 'Bikri se mila hua TOTAL paisa. 10 bracelets × Rs. 50 = Rs. 500 revenue. Yeh aapki kamai hai — abhi tak kharcha minus NAHI kiya!',
  },
  {
    icon: '📦',
    name: 'Cost (Kharcha)',
    formula: 'Cost = banane mein laga paisa',
    desc: 'Cheezein banane ya kharidne mein jitna paisa laga. Jaise bracelet ke liye dhaaga aur moti ka paisa.',
  },
  {
    icon: '📈',
    name: 'Profit (Faida)',
    formula: 'Profit = Revenue − Cost',
    desc: 'Jab kamai kharche se ZYADA ho — jo bach ke aaya, woh profit hai! Revenue Rs. 500 − Cost Rs. 300 = Rs. 200 profit 🎉',
  },
  {
    icon: '📉',
    name: 'Loss (Nuksan)',
    formula: 'Loss = jab Cost > Revenue',
    desc: 'Jab kharcha kamai se zyada ho jaye. Ghabrao mat — har loss ek lesson hai! Aaj samjho, kal better faisla lo.',
  },
  {
    icon: '🛒',
    name: 'Stock',
    formula: 'Stock = bechne ke liye items',
    desc: 'Aapke paas kitne items bechne ke liye ready hain. Stock khatam = bikri band! Zyada stock aur kam customers = paisa phas gaya.',
  },
  {
    icon: '💰',
    name: 'Cash (Wallet)',
    formula: 'Cash = abhi ka paisa',
    desc: 'Is waqt aapke paas jitna paisa hai. Isi se naya stock khareedte ho — cash khatam to business ruk jata hai!',
  },
];

export default function MoneyTerms() {
  const [open, setOpen] = useState(false);

  return (
    <div className="money-terms">
      <button className="money-terms-toggle" onClick={() => setOpen(!open)}>
        <span className="money-terms-toggle-text">
          📖 Paise ki Bhasha
          <small> — yeh shabd kya kehte hain?</small>
        </span>
        <span className="money-terms-arrow">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="money-terms-list">
          {TERMS.map((t) => (
            <div key={t.name} className="money-term-item">
              <span className="money-term-icon">{t.icon}</span>
              <div className="money-term-body">
                <strong className="money-term-name">{t.name}</strong>
                <span className="money-term-formula">{t.formula}</span>
                <p className="money-term-desc">{t.desc}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
