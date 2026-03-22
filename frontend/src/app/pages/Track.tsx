import React, { useState } from 'react';
import { useLang } from '../context/LanguageContext';
import { useApp } from '../context/AppContext';
import { Search, Check, Clock, AlertCircle } from 'lucide-react';

export function Track() {
  const { t } = useLang();
  const { applications } = useApp();
  const [refInput, setRefInput] = useState('');
  const [result, setResult] = useState<any>(null);
  const [searched, setSearched] = useState(false);

  const handleTrack = () => {
    setSearched(true);
    if (applications[refInput]) {
      setResult({ ref: refInput, ...applications[refInput] });
    } else {
      // Mock: always return a sample result for demo
      setResult({
        ref: refInput || 'JAN-2026-00341',
        schemeName: 'PM-KISAN Samman Nidhi',
        status: 'review',
        date: '20 Mar 2026',
        expected: '4 Apr 2026',
      });
    }
  };

  const stages = [
    { key: 'submitted', label: t('track.s1'), icon: Check },
    { key: 'review', label: t('track.s2'), icon: Clock },
    { key: 'approved', label: t('track.s3'), icon: Check },
  ];

  const stageIndex = result ? (result.status === 'submitted' ? 0 : result.status === 'review' ? 1 : 2) : -1;

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      <div className="text-center mb-8">
        <h1 className="text-[#000080] mb-2" style={{ fontWeight: 700, fontSize: '1.75rem' }}>{t('track.header')}</h1>
        <p className="text-muted-foreground">{t('track.sub')}</p>
      </div>

      <div className="flex rounded-full border-2 border-border bg-white shadow-sm overflow-hidden focus-within:border-primary transition mb-8">
        <input
          value={refInput}
          onChange={e => setRefInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleTrack()}
          placeholder={t('track.placeholder')}
          className="flex-1 px-5 py-3 bg-transparent outline-none"
        />
        <button onClick={handleTrack} className="px-6 py-3 bg-[#FF9933] text-white hover:bg-[#e8882d] transition flex items-center gap-2" style={{ fontWeight: 500 }}>
          <Search className="w-4 h-4" /> {t('track.btn')}
        </button>
      </div>

      {searched && !result && (
        <div className="text-center p-6 rounded-xl bg-white border border-border">
          <AlertCircle className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground">{t('track.notfound')}</p>
        </div>
      )}

      {result && (
        <div className="bg-white rounded-xl border border-border p-6">
          <h3 className="text-center mb-1" style={{ fontWeight: 600 }}>{result.schemeName}</h3>
          <p className="text-center text-muted-foreground mb-8" style={{ fontSize: '0.85rem' }}>Ref: {result.ref}</p>

          {/* Timeline */}
          <div className="flex items-center justify-between relative mb-6">
            <div className="absolute top-5 left-[10%] right-[10%] h-1 bg-muted rounded-full">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${stageIndex * 50}%`, backgroundColor: result.status === 'rejected' ? '#dc2626' : '#138808' }}
              />
            </div>
            {stages.map((stage, i) => {
              const active = i <= stageIndex;
              const isRejected = i === 2 && result.status === 'rejected';
              return (
                <div key={stage.key} className="relative z-10 flex flex-col items-center w-1/3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 ${
                    isRejected ? 'bg-red-100 border-red-500 text-red-500' :
                    active ? 'bg-[#138808] border-[#138808] text-white' : 'bg-white border-border text-muted-foreground'
                  }`}>
                    <stage.icon className="w-5 h-5" />
                  </div>
                  <span className={`mt-2 text-center ${active ? 'text-foreground' : 'text-muted-foreground'}`} style={{ fontSize: '0.8rem', fontWeight: active ? 600 : 400 }}>
                    {isRejected ? t('track.rejected') : stage.label}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="text-center space-y-1 text-muted-foreground" style={{ fontSize: '0.85rem' }}>
            <p>{t('track.s1')}: {result.date}</p>
            <p>{t('track.expected', { date: result.expected })}</p>
          </div>
        </div>
      )}
    </div>
  );
}
