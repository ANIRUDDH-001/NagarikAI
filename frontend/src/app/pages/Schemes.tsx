import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router';
import { useLang } from '../context/LanguageContext';
import { useApp } from '../context/AppContext';
import { ChevronDown, ChevronUp, ArrowLeft, FileText, ExternalLink } from 'lucide-react';

const domainColors: Record<string, string> = {
  Agriculture: '#138808', Health: '#FF9933', Education: '#000080', Employment: '#8B5CF6', 'Social welfare': '#dc2626',
};

export function Schemes() {
  const { lang, t } = useLang();
  const { schemes, gapValue, profile } = useApp();
  const navigate = useNavigate();
  const [activeDomain, setActiveDomain] = useState('All');
  const [sort, setSort] = useState('highest');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const domains = ['All', 'Agriculture', 'Health', 'Education', 'Employment', 'Social welfare'];
  const domainKeys = ['filter.all', 'filter.agriculture', 'filter.health', 'filter.education', 'filter.employment', 'filter.social'];

  const filtered = schemes
    .filter(s => activeDomain === 'All' || s.domain === activeDomain)
    .sort((a, b) => sort === 'highest' ? b.benefit - a.benefit : sort === 'best' ? b.matchConfidence - a.matchConfidence : a.steps.length - b.steps.length);

  if (schemes.length === 0) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 text-center">
        <p className="text-muted-foreground mb-4">{t('scheme.empty')}</p>
        <button onClick={() => navigate('/chat')} className="px-6 py-2 rounded-full bg-primary text-primary-foreground">{t('scheme.update')}</button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      {/* Gap Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-[#FF9933] to-[#138808] text-white mb-6">
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>
          {t('schemes.gap_banner', { gap_value: `₹${gapValue.toLocaleString('en-IN')}`, count: schemes.length })}
        </h1>
        <p className="text-white/80 mt-1" style={{ fontSize: '0.85rem' }}>
          {t('schemes.gap_sub', { state: profile.state, occupation: profile.occupation, age: profile.age, income: profile.income })}
        </p>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-2 mb-6">
        <div className="flex flex-wrap gap-1.5">
          {domains.map((d, i) => (
            <button
              key={d}
              onClick={() => setActiveDomain(d)}
              className={`px-3 py-1.5 rounded-full border transition ${activeDomain === d ? 'bg-[#000080] text-white border-[#000080]' : 'border-border hover:bg-muted'}`}
              style={{ fontSize: '0.8rem' }}
            >
              {t(domainKeys[i])}
            </button>
          ))}
        </div>
        <select
          value={sort}
          onChange={e => setSort(e.target.value)}
          className="ml-auto px-3 py-1.5 rounded-lg border border-border bg-white"
          style={{ fontSize: '0.8rem' }}
        >
          <option value="highest">{t('sort.highest')}</option>
          <option value="easiest">{t('sort.easiest')}</option>
          <option value="best">{t('sort.best')}</option>
        </select>
      </div>

      {/* Scheme Cards */}
      <div className="space-y-4">
        {filtered.map(scheme => {
          const expanded = expandedId === scheme.id;
          return (
            <div key={scheme.id} className="bg-white rounded-xl border border-border shadow-sm overflow-hidden">
              <div className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <h3 style={{ fontWeight: 600, fontSize: '1.05rem' }}>{lang === 'hi' ? scheme.nameHi : scheme.name}</h3>
                    <p className="text-muted-foreground" style={{ fontSize: '0.8rem' }}>{lang === 'hi' ? scheme.ministryHi : scheme.ministry}</p>
                  </div>
                  <span className="px-2.5 py-1 rounded-full text-white shrink-0" style={{ backgroundColor: domainColors[scheme.domain] || '#666', fontSize: '0.7rem', fontWeight: 500 }}>
                    {scheme.domain}
                  </span>
                </div>
                <div className="flex items-center gap-4 mt-3">
                  <span className="text-[#138808]" style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                    {t('scheme.per_year', { value: scheme.benefit.toLocaleString('en-IN') })}
                  </span>
                  <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                    <div className="h-full rounded-full bg-[#FF9933]" style={{ width: `${scheme.matchConfidence * 100}%` }} />
                  </div>
                </div>
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => setExpandedId(expanded ? null : scheme.id)}
                    className="px-4 py-2 rounded-full bg-[#000080] text-white flex items-center gap-1"
                    style={{ fontSize: '0.8rem' }}
                  >
                    {t('scheme.how_apply')}
                    {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => navigate('/chat')}
                    className="px-4 py-2 rounded-full border border-[#FF9933] text-[#FF9933]"
                    style={{ fontSize: '0.8rem' }}
                  >
                    {t('scheme.ask')}
                  </button>
                </div>
              </div>

              {expanded && (
                <div className="border-t border-border p-4 bg-background/50 space-y-4">
                  <p style={{ fontSize: '0.9rem' }}>{lang === 'hi' ? scheme.descriptionHi : scheme.description}</p>

                  <div>
                    <h4 className="text-[#000080] mb-2" style={{ fontWeight: 600 }}>{t('detail.need')}</h4>
                    <ol className="list-decimal list-inside space-y-1">
                      {scheme.documents.map((d, i) => (
                        <li key={i} style={{ fontSize: '0.85rem' }}>
                          <span style={{ fontWeight: 500 }}>{lang === 'hi' ? d.nameHi : d.name}</span>
                          <span className="text-muted-foreground"> — {lang === 'hi' ? d.sourceHi : d.source}</span>
                        </li>
                      ))}
                    </ol>
                  </div>

                  <div>
                    <h4 className="text-[#000080] mb-2" style={{ fontWeight: 600 }}>{t('detail.steps')}</h4>
                    <ol className="list-decimal list-inside space-y-1">
                      {scheme.steps.map((s, i) => (
                        <li key={i} style={{ fontSize: '0.85rem' }}>{lang === 'hi' ? s.stepHi : s.step}</li>
                      ))}
                    </ol>
                  </div>

                  <div className="flex flex-wrap gap-2 pt-2">
                    <Link to={`/schemes/${scheme.slug}`} className="px-4 py-2 rounded-full bg-[#138808] text-white flex items-center gap-1" style={{ fontSize: '0.8rem' }}>
                      <FileText className="w-4 h-4" /> {t('scheme.start')}
                    </Link>
                    {scheme.applyUrl && (
                      <a href={scheme.applyUrl} target="_blank" rel="noopener noreferrer" className="px-4 py-2 rounded-full border border-border flex items-center gap-1" style={{ fontSize: '0.8rem' }}>
                        <ExternalLink className="w-4 h-4" /> {t('scheme.apply_online')}
                      </a>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <button onClick={() => navigate('/chat')} className="mt-6 px-5 py-2 rounded-full border border-border flex items-center gap-1 hover:bg-muted transition" style={{ fontSize: '0.9rem' }}>
        <ArrowLeft className="w-4 h-4" /> {t('scheme.back')}
      </button>
    </div>
  );
}
