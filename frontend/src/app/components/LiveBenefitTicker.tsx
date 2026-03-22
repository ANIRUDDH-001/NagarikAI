import React, { useState, useEffect } from 'react';
import { useLang } from '../context/LanguageContext';
import { motion, AnimatePresence } from 'motion/react';

const benefits = [
  { state: 'Rajasthan', amount: 2000 },
  { state: 'Bihar', amount: 5000 },
  { state: 'Uttar Pradesh', amount: 12000 },
  { state: 'Maharashtra', amount: 8000 },
  { state: 'West Bengal', amount: 3500 },
  { state: 'Madhya Pradesh', amount: 6000 },
];

const benefitsHi = [
  { state: 'राजस्थान', amount: 2000 },
  { state: 'बिहार', amount: 5000 },
  { state: 'उत्तर प्रदेश', amount: 12000 },
  { state: 'महाराष्ट्र', amount: 8000 },
  { state: 'पश्चिम बंगाल', amount: 3500 },
  { state: 'मध्य प्रदेश', amount: 6000 },
];

export function LiveBenefitTicker() {
  const { lang, t } = useLang();
  const [index, setIndex] = useState(0);
  const data = lang === 'hi' ? benefitsHi : benefits;

  useEffect(() => {
    const interval = setInterval(() => {
      setIndex(prev => (prev + 1) % data.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [data.length]);

  return (
    <div className="h-12 flex items-center justify-center overflow-hidden">
      <AnimatePresence mode="wait">
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.4 }}
          className="flex items-center gap-2 text-white/90"
          style={{ fontSize: '0.9rem' }}
        >
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span>
            {lang === 'hi' 
              ? `${data[index].state} में किसी ने ₹${data[index].amount.toLocaleString()}/माह प्राप्त किया`
              : `Someone in ${data[index].state} just found ₹${data[index].amount.toLocaleString()}/month`
            }
          </span>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
