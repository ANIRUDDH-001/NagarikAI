import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { useLang } from '../context/LanguageContext';
import { useApp } from '../context/AppContext';
import { mockSchemes, botResponses } from '../utils/mockData';
import { Mic, Send, Volume2, Check, ChevronRight } from 'lucide-react';
import { v4Fallback } from '../utils/uuid';

export function Chat() {
  const { lang, t } = useLang();
  const { profile, setProfile, chatState, setChatState, messages, addMessage, setSchemes, setGapValue, gapValue, isLoggedIn } = useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [voiceState, setVoiceState] = useState<'default' | 'listening' | 'processing'>('default');
  const [showSavePrompt, setShowSavePrompt] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Init first bot message
  useEffect(() => {
    if (messages.length === 0) {
      addMessage({ id: v4Fallback(), role: 'bot', text: t('chat.first') });
    }
    // Handle initial message from landing
    const state = location.state as any;
    if (state?.initialMessage) {
      setTimeout(() => handleSend(state.initialMessage), 500);
      window.history.replaceState({}, '');
    }
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, typing]);

  const handleSend = (text?: string) => {
    const msg = text || input;
    if (!msg.trim()) return;
    setInput('');
    addMessage({ id: v4Fallback(), role: 'user', text: msg });
    setTyping(true);

    setTimeout(() => {
      const match = botResponses.find(r => msg.toLowerCase().includes(r.trigger)) || botResponses[2];
      const reply = lang === 'hi' ? match.hi : match.en;

      setProfile({
        state: match.profile.state,
        occupation: match.profile.occupation,
        age: match.profile.age,
        income: match.profile.income,
        category: match.profile.category,
        bpl: match.profile.bpl,
        gender: match.profile.gender,
      });
      setSchemes(mockSchemes);
      const total = mockSchemes.reduce((s, sc) => s + sc.benefit, 0);
      setGapValue(total);
      setChatState('match');
      setShowSavePrompt(!isLoggedIn);

      addMessage({ id: v4Fallback(), role: 'bot', text: reply });
      setTyping(false);
    }, 2000);
  };

  const handleVoice = () => {
    setVoiceState('listening');
    setTimeout(() => {
      setVoiceState('processing');
      setTimeout(() => {
        setVoiceState('default');
        handleSend(t('example.1'));
      }, 1000);
    }, 1500);
  };

  const profileFields = [
    { key: 'state', label: t('profile.state'), value: profile.state },
    { key: 'occupation', label: t('profile.occupation'), value: profile.occupation },
    { key: 'age', label: t('profile.age'), value: profile.age },
    { key: 'income', label: t('profile.income'), value: profile.income },
    { key: 'category', label: t('profile.category'), value: profile.category },
    { key: 'bpl', label: t('profile.bpl'), value: profile.bpl },
    { key: 'gender', label: t('profile.gender'), value: profile.gender },
  ];

  return (
    <div className="max-w-7xl mx-auto flex h-[calc(100vh-5rem)] relative">
      {/* Chat Column */}
      <div className="flex-1 flex flex-col min-w-0">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map(msg => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] md:max-w-[60%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-[#FF9933] text-white rounded-br-sm'
                  : 'bg-white border border-border rounded-bl-sm shadow-sm'
              }`}>
                {msg.role === 'bot' && (
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-5 h-5 rounded-full bg-[#000080] flex items-center justify-center">
                      <span className="text-white" style={{ fontSize: '0.5rem', fontWeight: 700 }}>JS</span>
                    </div>
                    <button className="text-muted-foreground hover:text-foreground"><Volume2 className="w-3.5 h-3.5" /></button>
                  </div>
                )}
                <p style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>{msg.text}</p>
              </div>
            </div>
          ))}
          {typing && (
            <div className="flex justify-start">
              <div className="bg-white border border-border rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Save Profile Prompt */}
        {showSavePrompt && chatState === 'match' && (
          <div className="mx-4 mb-2 p-3 rounded-lg bg-[#138808]/10 border border-[#138808]/30 flex items-center justify-between flex-wrap gap-2">
            <p style={{ fontSize: '0.85rem' }}>{t('save.prompt')}</p>
            <div className="flex gap-2">
              <button className="px-3 py-1.5 rounded-full bg-[#138808] text-white" style={{ fontSize: '0.8rem' }}>{t('save.google')}</button>
              <button onClick={() => setShowSavePrompt(false)} className="px-3 py-1.5 rounded-full border border-border" style={{ fontSize: '0.8rem' }}>{t('save.notnow')}</button>
            </div>
          </div>
        )}

        {/* Input Bar */}
        <div className="p-4 border-t border-border bg-white">
          <div className="flex items-center gap-2">
            <button
              onClick={handleVoice}
              className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 transition ${
                voiceState === 'listening' ? 'bg-red-500 animate-pulse' :
                voiceState === 'processing' ? 'bg-[#FF9933] animate-spin' :
                'bg-muted hover:bg-muted/80'
              }`}
              title={t('chat.hold')}
            >
              <Mic className={`w-5 h-5 ${voiceState !== 'default' ? 'text-white' : ''}`} />
            </button>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder={t('chat.placeholder')}
              className="flex-1 px-4 py-2.5 rounded-full border border-border bg-background focus:border-primary outline-none transition"
            />
            <button
              onClick={() => handleSend()}
              className="w-10 h-10 rounded-full bg-[#138808] text-white flex items-center justify-center shrink-0 hover:bg-[#0f6d06] transition"
              aria-label={t('chat.send')}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Mobile sidebar toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="md:hidden fixed bottom-24 right-4 z-40 px-4 py-2 rounded-full bg-[#000080] text-white shadow-lg"
        style={{ fontSize: '0.8rem' }}
      >
        {t('profile.header')}
      </button>

      {/* Profile Sidebar */}
      <div className={`${sidebarOpen ? 'fixed inset-0 z-50 bg-black/30 md:relative md:bg-transparent' : 'hidden md:block'} md:w-80`}>
        <div className={`${sidebarOpen ? 'absolute right-0 top-0 h-full w-80' : ''} bg-white border-l border-border p-4 overflow-y-auto h-full`}>
          {sidebarOpen && <button onClick={() => setSidebarOpen(false)} className="md:hidden mb-2 text-muted-foreground">✕</button>}
          <h3 className="text-[#000080] mb-4" style={{ fontWeight: 600 }}>{t('profile.header')}</h3>
          <div className="space-y-3">
            {profileFields.map(f => (
              <div key={f.key} className="flex items-center justify-between py-2 border-b border-border/50">
                <span className="text-muted-foreground" style={{ fontSize: '0.8rem' }}>{f.label}</span>
                <span className="flex items-center gap-1" style={{ fontSize: '0.85rem', fontWeight: 500 }}>
                  {f.value || '—'}
                  {f.value && <Check className="w-3.5 h-3.5 text-[#138808]" />}
                </span>
              </div>
            ))}
          </div>

          {/* Gap Card */}
          {chatState === 'match' && (
            <div className="mt-6 p-4 rounded-xl bg-gradient-to-br from-[#FF9933]/10 to-[#138808]/10 border-2 border-[#FF9933]">
              <p style={{ fontSize: '1.1rem', fontWeight: 700 }} className="text-[#000080]">
                {t('gap.claim', { gap_value: gapValue.toLocaleString('en-IN') })}
              </p>
              <p className="text-muted-foreground mt-1" style={{ fontSize: '0.8rem' }}>
                {t('gap.across', { scheme_count: mockSchemes.length })}
              </p>
              <button
                onClick={() => navigate('/schemes')}
                className="mt-3 w-full py-2.5 rounded-full bg-[#138808] text-white flex items-center justify-center gap-1 hover:bg-[#0f6d06] transition"
                style={{ fontWeight: 500, fontSize: '0.9rem' }}
              >
                {t('gap.cta')} <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
