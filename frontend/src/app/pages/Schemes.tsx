import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router';
import { useLang } from '../context/LanguageContext';
import { useApp } from '../context/AppContext';
import { ChevronDown, ChevronUp, ArrowLeft, FileText, ExternalLink, Volume2, CheckCircle2, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

const domainColors: Record<string, string> = {
  Agriculture: '#138808', 
  Health: '#FF9933', 
  Education: '#000080', 
  Employment: '#8B5CF6', 
  'Social welfare': '#dc2626',
};

function getMatchReasons(scheme: any, profile: any, lang: 'en' | 'hi') {
  const reasons = [];
  
  if (scheme.name.includes('Farmer') || scheme.name.includes('Kisan')) {
    reasons.push(lang === 'hi' ? 'पेशा: किसान' : 'Occupation: Farmer');
  }
  if (scheme.name.includes('Women') || scheme.name.includes('Mahila')) {
    reasons.push(lang === 'hi' ? 'लिंग: महिला' : 'Gender: Female');
  }
  if (profile.age && parseInt(profile.age) >= 18) {
    reasons.push(lang === 'hi' ? 'उम्र: 18+' : 'Age: 18+');
  }
  if (profile.state) {
    reasons.push(lang === 'hi' ? `राज्य: ${profile.state}` : `State: ${profile.state}`);
  }
  if (profile.income && parseInt(profile.income) < 200000) {
    reasons.push(lang === 'hi' ? 'आमदनी: पात्र' : 'Income: Eligible');
  }
  
  return reasons.slice(0, 3);
}

export function Schemes() {
  const { lang, t } = useLang();
  const { schemes, gapValue, profile } = useApp();
  const navigate = useNavigate();
  const [activeDomain, setActiveDomain] = useState('All');
  const [sort, setSort] = useState('highest');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [listeningTo, setListeningTo] = useState<string | null>(null);

  const domains = ['All', 'Agriculture', 'Health', 'Education', 'Employment', 'Social welfare'];
  const domainKeys = ['filter.all', 'filter.agriculture', 'filter.health', 'filter.education', 'filter.employment', 'filter.social'];

  const filtered = schemes
    .filter(s => activeDomain === 'All' || s.domain === activeDomain)
    .sort((a, b) => sort === 'highest' ? b.benefit - a.benefit : sort === 'best' ? b.matchConfidence - a.matchConfidence : a.steps.length - b.steps.length);

  const handleListenToGuide = (schemeId: string) => {
    setListeningTo(listeningTo === schemeId ? null : schemeId);
    if (listeningTo !== schemeId) {
      setTimeout(() => setListeningTo(null), 5000);
    }
  };

  if (schemes.length === 0) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 text-center">
        <p className="text-muted-foreground mb-4">{t('scheme.empty')}</p>
        <button onClick={() => navigate('/chat')} className="px-6 py-2 rounded-full bg-primary text-primary-foreground">{t('scheme.update')}</button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative p-8 rounded-3xl bg-gradient-to-br from-[#FF9933] via-[#FF9933] to-[#138808] text-white mb-8 overflow-hidden shadow-2xl"
      >
        <div className="absolute inset-0 opacity-20">
          <div 
            className="absolute inset-0"
            style={{
              backgroundImage: `
                radial-gradient(circle at 20% 50%, rgba(255,255,255,0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 50%, rgba(255,255,255,0.2) 0%, transparent 50%)
              `
            }}
          />
        </div>
        <div className="relative z-10">
          <div className="flex items-start gap-3 mb-2">
            <Sparkles className="w-7 h-7 text-white" />
            <h1 
              style={{ fontSize: 'clamp(1.5rem, 4vw, 2rem)', fontWeight: 700, fontFamily: 'Lora, serif' }}
            >
              {t('schemes.gap_banner', { gap_value: gapValue.toLocaleString('en-IN'), count: schemes.length })}
            </h1>
          </div>
          <p className="text-white/90 ml-10" style={{ fontSize: '0.95rem' }}>
            {t('schemes.gap_sub', { state: profile.state, occupation: profile.occupation, age: profile.age, income: profile.income })}
          </p>
        </div>
      </motion.div>

      <div className="flex flex-wrap items-center gap-2 mb-6">
        <div className="flex flex-wrap gap-2">
          {domains.map((d, i) => (
            <motion.button
              key={d}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setActiveDomain(d)}
              className={`px-4 py-2 rounded-full border-2 transition-all shadow-sm ${
                activeDomain === d 
                  ? 'bg-gradient-to-r from-[#000080] to-[#000060] text-white border-[#000080] shadow-md' 
                  : 'border-border bg-white hover:border-[#FF9933] hover:bg-muted'
              }`}
              style={{ fontSize: '0.85rem', fontWeight: 600 }}
            >
              {t(domainKeys[i])}
            </motion.button>
          ))}
        </div>
        <select
          value={sort}
          onChange={e => setSort(e.target.value)}
          className="ml-auto px-4 py-2 rounded-xl border-2 border-border bg-white focus:border-[#FF9933] outline-none transition-all shadow-sm"
          style={{ fontSize: '0.85rem', fontWeight: 500 }}
        >
          <option value="highest">{t('sort.highest')}</option>
          <option value="easiest">{t('sort.easiest')}</option>
          <option value="best">{t('sort.best')}</option>
        </select>
      </div>

      <div className="space-y-5">
        <AnimatePresence>
          {filtered.map((scheme, index) => {
            const expanded = expandedId === scheme.id;
            const matchReasons = getMatchReasons(scheme, profile, lang);
            const isListening = listeningTo === scheme.id;
            
            return (
              <motion.div
                key={scheme.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="bg-white rounded-2xl border-2 border-border shadow-md hover:shadow-xl transition-all overflow-hidden"
              >
                <div className="p-5">
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div className="flex-1">
                      <h3 
                        style={{ fontWeight: 700, fontSize: '1.15rem', fontFamily: 'Lora, serif' }}
                        className="text-[#000080] mb-1"
                      >
                        {lang === 'hi' ? scheme.nameHi : scheme.name}
                      </h3>
                      <p className="text-muted-foreground" style={{ fontSize: '0.85rem' }}>
                        {lang === 'hi' ? scheme.ministryHi : scheme.ministry}
                      </p>
                    </div>
                    <span 
                      className="px-3 py-1.5 rounded-full text-white shrink-0 shadow-sm" 
                      style={{ 
                        backgroundColor: domainColors[scheme.domain] || '#666', 
                        fontSize: '0.75rem', 
                        fontWeight: 600 
                      }}
                    >
                      {scheme.domain}
                    </span>
                  </div>

                  {matchReasons.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {matchReasons.map((reason, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#138808]/10 border border-[#138808]/30"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5 text-[#138808]" />
                          <span 
                            className="text-[#138808]" 
                            style={{ fontSize: '0.75rem', fontWeight: 600 }}
                          >
                            {reason}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="flex items-center gap-4 mb-4">
                    <span 
                      className="text-[#138808]" 
                      style={{ fontSize: '1.25rem', fontWeight: 800, fontFamily: 'Lora, serif' }}
                    >
                      {t('scheme.per_year', { value: scheme.benefit.toLocaleString('en-IN') })}
                    </span>
                    <div className="flex-1 h-2.5 rounded-full bg-muted overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${scheme.matchConfidence * 100}%` }}
                        transition={{ duration: 0.8, ease: 'easeOut' }}
                        className="h-full rounded-full bg-gradient-to-r from-[#FF9933] to-[#138808]"
                      />
                    </div>
                    <span 
                      className="text-muted-foreground" 
                      style={{ fontSize: '0.8rem', fontWeight: 600 }}
                    >
                      {Math.round(scheme.matchConfidence * 100)}%
                    </span>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => setExpandedId(expanded ? null : scheme.id)}
                      className="px-5 py-2.5 rounded-full bg-gradient-to-r from-[#000080] to-[#000060] text-white flex items-center gap-2 hover:shadow-lg transition-all"
                      style={{ fontSize: '0.85rem', fontWeight: 600 }}
                    >
                      {t('scheme.how_apply')}
                      {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => navigate('/chat')}
                      className="px-5 py-2.5 rounded-full border-2 border-[#FF9933] text-[#FF9933] hover:bg-[#FF9933] hover:text-white transition-all"
                      style={{ fontSize: '0.85rem', fontWeight: 600 }}
                    >
                      {t('scheme.ask')}
                    </button>
                  </div>
                </div>

                <AnimatePresence>
                  {expanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                      className="border-t-2 border-border p-5 bg-gradient-to-b from-background/50 to-white space-y-5"
                    >
                      <p 
                        className="leading-relaxed text-foreground"
                        style={{ fontSize: '0.95rem' }}
                      >
                        {lang === 'hi' ? scheme.descriptionHi : scheme.description}
                      </p>

                      <div>
                        <h4 
                          className="text-[#000080] mb-3 flex items-center gap-2" 
                          style={{ fontWeight: 700, fontSize: '1rem', fontFamily: 'Lora, serif' }}
                        >
                          <FileText className="w-5 h-5" />
                          {t('detail.need')}
                        </h4>
                        <ol className="list-decimal list-inside space-y-2 ml-2">
                          {scheme.documents.map((d: any, i: number) => (
                            <li key={i} style={{ fontSize: '0.9rem' }}>
                              <span style={{ fontWeight: 600 }}>{lang === 'hi' ? d.nameHi : d.name}</span>
                              <span className="text-muted-foreground"> — {lang === 'hi' ? d.sourceHi : d.source}</span>
                            </li>
                          ))}
                        </ol>
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <h4 
                            className="text-[#000080] flex items-center gap-2" 
                            style={{ fontWeight: 700, fontSize: '1rem', fontFamily: 'Lora, serif' }}
                          >
                            {t('detail.steps')}
                          </h4>
                          <button
                            onClick={() => handleListenToGuide(scheme.id)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-full transition-all ${
                              isListening
                                ? 'bg-[#FF9933] text-white'
                                : 'bg-[#FF9933]/10 text-[#FF9933] hover:bg-[#FF9933]/20'
                            }`}
                            style={{ fontSize: '0.85rem', fontWeight: 600 }}
                          >
                            <Volume2 className={`w-4 h-4 ${isListening ? 'animate-pulse' : ''}`} />
                            {isListening 
                              ? (lang === 'hi' ? 'सुन रहे हैं...' : 'Listening...') 
                              : (lang === 'hi' ? 'सुनें' : 'Listen to Guide')
                            }
                          </button>
                        </div>
                        <ol className="list-decimal list-inside space-y-2 ml-2">
                          {scheme.steps.map((s: any, i: number) => (
                            <li 
                              key={i} 
                              className={isListening ? 'text-[#FF9933]' : ''}
                              style={{ fontSize: '0.9rem', fontWeight: isListening ? 600 : 400 }}
                            >
                              {lang === 'hi' ? s.stepHi : s.step}
                            </li>
                          ))}
                        </ol>
                      </div>

                      <div className="flex flex-wrap gap-3 pt-3">
                        <Link 
                          to={`/schemes/${scheme.slug}`} 
                          className="px-5 py-2.5 rounded-full bg-gradient-to-r from-[#138808] to-[#0f6d06] text-white flex items-center gap-2 hover:shadow-lg transition-all" 
                          style={{ fontSize: '0.9rem', fontWeight: 600 }}
                        >
                          <FileText className="w-4 h-4" /> {t('scheme.start')}
                        </Link>
                        {scheme.applyUrl && (
                          <a 
                            href={scheme.applyUrl} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            className="px-5 py-2.5 rounded-full border-2 border-border hover:border-[#138808] flex items-center gap-2 hover:bg-muted transition-all" 
                            style={{ fontSize: '0.9rem', fontWeight: 600 }}
                          >
                            <ExternalLink className="w-4 h-4" /> {t('scheme.apply_online')}
                          </a>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      <motion.button 
        whileHover={{ x: -5 }}
        onClick={() => navigate('/chat')} 
        className="mt-8 px-6 py-3 rounded-full border-2 border-border bg-white flex items-center gap-2 hover:bg-muted hover:border-[#FF9933] transition-all shadow-sm" 
        style={{ fontSize: '0.95rem', fontWeight: 600 }}
      >
        <ArrowLeft className="w-5 h-5" /> {t('scheme.back')}
      </motion.button>
    </div>
  );
}