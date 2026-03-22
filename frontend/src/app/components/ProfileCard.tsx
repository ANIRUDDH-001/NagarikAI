import React from 'react';
import { Check, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useLang } from '../context/LanguageContext';

interface ProfileCardProps {
  fields: Array<{
    key: string;
    label: string;
    value: string;
  }>;
  isExtracting?: boolean;
}

export function ProfileCard({ fields, isExtracting }: ProfileCardProps) {
  const { t } = useLang();

  return (
    <div 
      className="bg-white/40 backdrop-blur-md border border-white/60 rounded-2xl p-5 shadow-xl"
      style={{ backdropFilter: 'blur(16px)' }}
    >
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-5 h-5 text-[#FF9933]" />
        <h3 
          className="text-[#000080]" 
          style={{ fontWeight: 700, fontSize: '1rem', fontFamily: 'Lora, serif' }}
        >
          {t('profile.header')}
        </h3>
      </div>

      <div className="space-y-3">
        <AnimatePresence>
          {fields.map((f, index) => (
            <motion.div
              key={f.key}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="relative"
            >
              <div className="flex items-center justify-between py-2.5 px-3 rounded-lg bg-white/50 border border-white/60">
                <span 
                  className="text-muted-foreground" 
                  style={{ fontSize: '0.85rem', fontWeight: 500 }}
                >
                  {f.label}
                </span>
                <div className="flex items-center gap-2">
                  {f.value ? (
                    <>
                      <span 
                        style={{ fontSize: '0.9rem', fontWeight: 600 }}
                        className="text-foreground"
                      >
                        {f.value}
                      </span>
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: 'spring', stiffness: 500 }}
                      >
                        <div className="w-6 h-6 rounded-full bg-[#138808] flex items-center justify-center">
                          <Check className="w-4 h-4 text-white" />
                        </div>
                      </motion.div>
                    </>
                  ) : (
                    <div className="flex gap-1">
                      <div className="w-2 h-2 rounded-full bg-muted-foreground/30 animate-pulse" />
                      <div className="w-2 h-2 rounded-full bg-muted-foreground/30 animate-pulse" style={{ animationDelay: '0.2s' }} />
                      <div className="w-2 h-2 rounded-full bg-muted-foreground/30 animate-pulse" style={{ animationDelay: '0.4s' }} />
                    </div>
                  )}
                </div>
              </div>
              {f.value && (
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: '100%' }}
                  transition={{ duration: 0.5 }}
                  className="absolute bottom-0 left-0 h-0.5 bg-gradient-to-r from-[#FF9933] to-[#138808] rounded-full"
                />
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
