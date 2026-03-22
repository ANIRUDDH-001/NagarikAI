import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { useLang } from '../context/LanguageContext';
import { Mic, Send, MessageCircle, Search, HandHelping } from 'lucide-react';
import { motion } from 'motion/react';

export function Landing() {
  const { t } = useLang();
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [voiceState, setVoiceState] = useState<'default' | 'listening' | 'processing'>('default');

  const handleSubmit = (text?: string) => {
    const msg = text || input;
    if (!msg.trim()) return;
    navigate('/chat', { state: { initialMessage: msg } });
  };

  const handleVoice = () => {
    setVoiceState('listening');
    setTimeout(() => {
      setVoiceState('processing');
      setTimeout(() => {
        setVoiceState('default');
        navigate('/chat', { state: { initialMessage: t('example.1') } });
      }, 1200);
    }, 2000);
  };

  const examples = [t('example.1'), t('example.2'), t('example.3')];

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 opacity-5" style={{ background: 'radial-gradient(circle at 30% 50%, #FF9933 0%, transparent 50%), radial-gradient(circle at 70% 50%, #138808 0%, transparent 50%)' }} />
        <div className="max-w-4xl mx-auto px-4 py-16 md:py-24 text-center relative z-10">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-[#000080] mb-4"
            style={{ fontSize: 'clamp(1.75rem, 5vw, 2.75rem)', fontWeight: 900, lineHeight: 1.2 }}
          >
            {t('hero.headline')}
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-muted-foreground max-w-2xl mx-auto mb-10"
            style={{ fontSize: '1.1rem' }}
          >
            {t('hero.subtext')}
          </motion.p>

          {/* Voice Button */}
          <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }} className="mb-8">
            <button
              onClick={handleVoice}
              className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto shadow-lg transition-all ${
                voiceState === 'listening' ? 'bg-red-500 animate-pulse scale-110' :
                voiceState === 'processing' ? 'bg-[#FF9933] animate-spin' :
                'bg-[#FF9933] hover:bg-[#e8882d] hover:scale-105'
              }`}
            >
              <Mic className="w-8 h-8 text-white" />
            </button>
            <p className="mt-3 text-muted-foreground" style={{ fontSize: '0.875rem' }}>
              {voiceState === 'default' ? t('voice.tap') : voiceState === 'listening' ? t('voice.listening') : t('voice.processing')}
            </p>
          </motion.div>

          {/* Text Input */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="max-w-xl mx-auto mb-6">
            <div className="flex rounded-full border-2 border-border bg-white shadow-sm overflow-hidden focus-within:border-primary transition">
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                placeholder={t('input.placeholder')}
                className="flex-1 px-5 py-3 bg-transparent outline-none"
              />
              <button
                onClick={() => handleSubmit()}
                className="px-6 py-3 bg-[#138808] text-white hover:bg-[#0f6d06] transition flex items-center gap-2"
                style={{ fontWeight: 500, fontSize: '0.9rem' }}
              >
                <Send className="w-4 h-4" />
                {t('input.submit')}
              </button>
            </div>
          </motion.div>

          {/* Example Queries */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="flex flex-wrap justify-center gap-2">
            {examples.map((ex, i) => (
              <button
                key={i}
                onClick={() => handleSubmit(ex)}
                className="px-4 py-2 rounded-full border border-border bg-white hover:bg-muted text-muted-foreground hover:text-foreground transition"
                style={{ fontSize: '0.8rem' }}
              >
                "{ex}"
              </button>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Stats */}
      <section className="bg-[#000080] text-white py-8">
        <div className="max-w-5xl mx-auto px-4 grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
          {[
            { icon: '57%', text: t('stat.1') },
            { icon: '600M', text: t('stat.2') },
            { icon: '500+', text: t('stat.3') },
          ].map((s, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}>
              <div style={{ fontSize: '2rem', fontWeight: 900 }} className="text-[#FF9933]">{s.icon}</div>
              <p style={{ fontSize: '0.9rem' }} className="text-white/80 mt-1">{s.text}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="py-16 bg-white">
        <div className="max-w-5xl mx-auto px-4">
          <h2 className="text-center text-[#000080] mb-12" style={{ fontSize: '1.75rem', fontWeight: 700 }}>
            {t('how.heading')}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { icon: <MessageCircle className="w-8 h-8" />, title: t('how.1.title'), body: t('how.1.body'), color: '#FF9933' },
              { icon: <Search className="w-8 h-8" />, title: t('how.2.title'), body: t('how.2.body'), color: '#000080' },
              { icon: <HandHelping className="w-8 h-8" />, title: t('how.3.title'), body: t('how.3.body'), color: '#138808' },
            ].map((step, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15 }}
                className="text-center p-6 rounded-xl border border-border bg-background"
              >
                <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 text-white" style={{ backgroundColor: step.color }}>
                  {step.icon}
                </div>
                <div className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-muted text-foreground mb-3" style={{ fontSize: '0.875rem', fontWeight: 700 }}>
                  {i + 1}
                </div>
                <h3 style={{ fontWeight: 600 }} className="mb-2">{step.title}</h3>
                <p className="text-muted-foreground" style={{ fontSize: '0.9rem' }}>{step.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
