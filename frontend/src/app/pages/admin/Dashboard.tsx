import React from 'react';
import { useLang } from '../../context/LanguageContext';
import { mockAdminStats, mockTopSchemes, mockRecentSessions, mockGapData } from '../../utils/mockData';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Users, IndianRupee, Database, Clock } from 'lucide-react';

export function Dashboard() {
  const { t } = useLang();
  const stats = [
    { label: t('admin.sessions_today'), value: mockAdminStats.sessionsToday.toLocaleString(), icon: Users, color: '#FF9933' },
    { label: t('admin.total_gap'), value: `₹${(mockAdminStats.totalGap / 100000).toFixed(1)}L`, icon: IndianRupee, color: '#138808' },
    { label: t('admin.schemes_db'), value: mockAdminStats.schemesInDb, icon: Database, color: '#000080' },
    { label: t('admin.pending'), value: mockAdminStats.pendingReview, icon: Clock, color: '#dc2626' },
  ];

  return (
    <div>
      <h1 className="text-[#000080] mb-6" style={{ fontWeight: 700 }}>{t('admin.dashboard')}</h1>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map(s => (
          <div key={s.label} className="bg-white rounded-xl border border-border p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${s.color}15` }}>
                <s.icon className="w-5 h-5" style={{ color: s.color }} />
              </div>
              <div>
                <p className="text-muted-foreground" style={{ fontSize: '0.75rem' }}>{s.label}</p>
                <p style={{ fontSize: '1.25rem', fontWeight: 700 }}>{s.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Gap Chart */}
      <div className="bg-white rounded-xl border border-border p-5 mb-8">
        <h3 className="mb-4" style={{ fontWeight: 600 }}>{t('admin.gap_chart')}</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={mockGapData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
            <XAxis dataKey="day" style={{ fontSize: '0.75rem' }} />
            <YAxis tickFormatter={v => `₹${(v / 100000).toFixed(0)}L`} style={{ fontSize: '0.75rem' }} />
            <Tooltip formatter={(v: number) => `₹${v.toLocaleString('en-IN')}`} />
            <Line 
              type="monotone" 
              dataKey="value" 
              stroke="#FF9933" 
              strokeWidth={2} 
              dot={{ fill: '#FF9933', r: 3 }} 
              activeDot={{ r: 6 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Schemes */}
        <div className="bg-white rounded-xl border border-border p-5">
          <h3 className="mb-4" style={{ fontWeight: 600 }}>{t('admin.top_schemes')}</h3>
          <div className="overflow-x-auto">
            <table className="w-full" style={{ fontSize: '0.8rem' }}>
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="py-2 pr-2">#</th><th className="py-2 pr-2">Scheme</th><th className="py-2 pr-2">Ministry</th><th className="py-2 pr-2">Matches</th><th className="py-2">Avg ₹</th>
                </tr>
              </thead>
              <tbody>
                {mockTopSchemes.map(s => (
                  <tr key={s.rank} className="border-b border-border/50">
                    <td className="py-2 pr-2" style={{ fontWeight: 600 }}>{s.rank}</td>
                    <td className="py-2 pr-2">{s.name}</td>
                    <td className="py-2 pr-2 text-muted-foreground">{s.ministry}</td>
                    <td className="py-2 pr-2">{s.matchCount}</td>
                    <td className="py-2">₹{s.avgBenefit.toLocaleString('en-IN')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Sessions */}
        <div className="bg-white rounded-xl border border-border p-5">
          <h3 className="mb-4" style={{ fontWeight: 600 }}>{t('admin.recent')}</h3>
          <div className="overflow-x-auto">
            <table className="w-full" style={{ fontSize: '0.8rem' }}>
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="py-2 pr-2">ID</th><th className="py-2 pr-2">State</th><th className="py-2 pr-2">Fields</th><th className="py-2 pr-2">Matched</th><th className="py-2">Time</th>
                </tr>
              </thead>
              <tbody>
                {mockRecentSessions.map(s => (
                  <tr key={s.id} className="border-b border-border/50 hover:bg-muted/50 cursor-pointer">
                    <td className="py-2 pr-2 text-muted-foreground">{s.id}</td>
                    <td className="py-2 pr-2">{s.state}</td>
                    <td className="py-2 pr-2">{s.fieldsCount}/7</td>
                    <td className="py-2 pr-2">{s.schemesMatched}</td>
                    <td className="py-2 text-muted-foreground">{s.timestamp}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}