'use client';

import React, { useMemo } from 'react';
import { RadialBarChart, RadialBar, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer as RC2 } from 'recharts';

interface Props {
  data: any[];
}

export default function RiskGauge({ data }: Props) {
  const latest = data[0];

  const riskColor = (level: string) => {
    switch (level) {
      case 'low': return '#10b981';
      case 'medium': return '#f59e0b';
      case 'high': return '#f97316';
      case 'critical': return '#ef4444';
      default: return '#64748b';
    }
  };

  const gaugeData = latest ? [
    { name: 'Bias', value: latest.bias_score * 100, fill: '#8b5cf6' },
    { name: 'Drift', value: latest.drift_score * 100, fill: '#06b6d4' },
    { name: 'Performance', value: latest.performance_score * 100, fill: '#f59e0b' },
    { name: 'Explainability', value: latest.explainability_score * 100, fill: '#10b981' },
  ] : [];

  const trend = useMemo(() => {
    return [...data]
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .slice(-14)
      .map(d => ({
        time: new Date(d.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        score: d.overall_score,
      }));
  }, [data]);

  return (
    <div style={{
      background: '#1e293b', borderRadius: '12px', padding: '24px',
      border: '1px solid #334155',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: 600 }}>⚠️ Risk Score</h3>
          <p style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>Composite risk assessment</p>
        </div>
        {latest && (
          <span style={{
            padding: '6px 14px', borderRadius: '20px', fontSize: '13px', fontWeight: 700,
            background: `${riskColor(latest.risk_level)}20`,
            color: riskColor(latest.risk_level),
            border: `1px solid ${riskColor(latest.risk_level)}40`,
          }}>
            {latest.overall_score.toFixed(2)} — {latest.risk_level.toUpperCase()}
          </span>
        )}
      </div>

      {/* Component scores */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '16px' }}>
        {gaugeData.map((g, i) => (
          <div key={i} style={{
            textAlign: 'center', padding: '12px 8px', borderRadius: '8px',
            background: `${g.fill}10`, border: `1px solid ${g.fill}20`,
          }}>
            <div style={{ fontSize: '20px', fontWeight: 700, color: g.fill }}>
              {g.value.toFixed(0)}%
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>{g.name}</div>
            <div style={{
              height: '4px', borderRadius: '2px', background: '#334155', marginTop: '8px',
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%', borderRadius: '2px', background: g.fill,
                width: `${g.value}%`, transition: 'width 0.5s ease',
              }} />
            </div>
          </div>
        ))}
      </div>

      {/* Trend line */}
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={trend} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
          <YAxis domain={[0, 1]} stroke="#64748b" fontSize={10} />
          <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }} />
          <Line type="monotone" dataKey="score" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}