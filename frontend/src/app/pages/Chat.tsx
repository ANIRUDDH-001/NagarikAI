import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { useLang } from '../context/LanguageContext';
import { useApp } from '../context/AppContext';
import { mockSchemes, botResponses } from '../utils/mockData';
import { Mic, Send, Volume2 } from 'lucide-react';
import { v4Fallback } from '../utils/uuid';
import { ProfileCard } from '../components/ProfileCard';
import { GapCard } from '../components/GapCard';
import { motion, AnimatePresence } from 'motion/react';

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

  useEffect(() => {
    if (messages.length === 0) {
      addMessage({ id: v4Fallback(), role: 'bot', text: t('chat.first') });
    }
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
      <div className="flex-1 flex flex-col min-w-0">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
          <AnimatePresence>
            {messages.map((msg, index) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[85%] md:max-w-[70%] rounded-2xl px-5 py-3.5 ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-br from-[#FF9933] to-[#e8882d] text-white rounded-br-md shadow-lg'
                    : 'bg-white/80 backdrop-blur-sm border border-border rounded-bl-md shadow-md'
                }`}>
                  {msg.role === 'bot' && (
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#000080] to-[#000060] flex items-center justify-center shadow-md">
                        <span className="text-white" style={{ fontSize: '0.6rem', fontWeight: 700 }}>JS</span>
                      </div>
                      <button 
                        className="text-muted-foreground hover:text-[#FF9933] transition-colors"
                        title={t('chat.speak')}
                      >
                        <Volume2 className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                  <p style={{ fontSize: '0.95rem', lineHeight: 1.7 }}>{msg.text}</p>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {typing && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-white/80 backdrop-blur-sm border border-border rounded-2xl rounded-bl-md px-5 py-4 shadow-md">
                <div className="flex gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#FF9933] animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2.5 h-2.5 rounded-full bg-[#FF9933] animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2.5 h-2.5 rounded-full bg-[#FF9933] animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </motion.div>
          )}
        </div>

        <AnimatePresence>
          {showSavePrompt && chatState === 'match' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="mx-4 mb-2 p-4 rounded-xl bg-gradient-to-r from-[#138808]/10 to-[#138808]/5 border border-[#138808]/30 backdrop-blur-sm flex items-center justify-between flex-wrap gap-3"
            >
              <p style={{ fontSize: '0.9rem', fontWeight: 500 }}>{t('save.prompt')}</p>
              <div className="flex gap-2">
                <button 
                  className="px-4 py-2 rounded-full bg-gradient-to-r from-[#138808] to-[#0f6d06] text-white shadow-md hover:shadow-lg transition-all" 
                  style={{ fontSize: '0.85rem', fontWeight: 600 }}
                >
                  {t('save.google')}
                </button>
                <button 
                  onClick={() => setShowSavePrompt(false)} 
                  className="px-4 py-2 rounded-full border border-border bg-white hover:bg-muted transition-all" 
                  style={{ fontSize: '0.85rem' }}
                >
                  {t('save.notnow')}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="p-4 border-t border-border bg-white/80 backdrop-blur-sm">
          <div className="flex items-center gap-2">
            <button
              onClick={handleVoice}
              className={`w-11 h-11 rounded-full flex items-center justify-center shrink-0 transition-all shadow-md ${
                voiceState === 'listening' 
                  ? 'bg-gradient-to-br from-red-500 to-red-600 animate-pulse shadow-red-500/50' 
                  : voiceState === 'processing' 
                  ? 'bg-gradient-to-br from-[#FF9933] to-[#e8882d] animate-spin' 
                  : 'bg-muted hover:bg-muted/80 hover:scale-105'
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
              className="flex-1 px-5 py-3 rounded-full border border-border bg-white focus:border-[#FF9933] outline-none transition-all"
              style={{ fontSize: '0.95rem' }}
            />
            <button
              onClick={() => handleSend()}
              className="w-11 h-11 rounded-full bg-gradient-to-br from-[#138808] to-[#0f6d06] text-white flex items-center justify-center shrink-0 hover:scale-105 transition-all shadow-md hover:shadow-lg"
              aria-label={t('chat.send')}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="md:hidden fixed bottom-24 right-4 z-40 px-5 py-3 rounded-full bg-gradient-to-br from-[#000080] to-[#000060] text-white shadow-xl"
        style={{ fontSize: '0.85rem', fontWeight: 600 }}
      >
        {t('profile.header')}
      </button>

      <div className={`${sidebarOpen ? 'fixed inset-0 z-50 bg-black/40 md:relative md:bg-transparent' : 'hidden md:block'} md:w-80 lg:w-96`}>
        <div 
          className={`${sidebarOpen ? 'absolute right-0 top-0 h-full w-80 lg:w-96' : ''} bg-gradient-to-b from-background to-white border-l border-border p-5 overflow-y-auto h-full`}
          style={{ backdropFilter: 'blur(10px)' }}
        >
          {sidebarOpen && (
            <button 
              onClick={() => setSidebarOpen(false)} 
              className="md:hidden mb-3 text-muted-foreground hover:text-foreground text-2xl"
            >
              ✕
            </button>
          )}

          <div className="space-y-5">
            <ProfileCard fields={profileFields} />

            {chatState === 'match' && (
              <GapCard
                gapValue={gapValue}
                schemeCount={mockSchemes.length}
                onViewSchemes={() => navigate('/schemes')}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
