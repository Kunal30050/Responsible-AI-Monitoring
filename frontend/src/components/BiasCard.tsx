'use client';

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';

interface Props {
  data: any[];
}

export default function BiasCard({ data }: Props) {
  // Group by metric_name, take latest
  const latestByMetric: Record<string, any> = {};
  for (const item of data) {
    if (!latestByMetric[item.metric_name] || new Date(item.timestamp) > new Date(latestByMetric[item.metric_name].timestamp)) {
      latestByMetric[item.metric_name] = item;
    }
  }

  const chartData = Object.values(latestByMetric).map((m: any) => ({
    name: m.metric_name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()).substring(0, 20),
    value: Math.abs(m.metric_value),
    isFair: m.is_fair,
    raw: m.metric_value,
  }));

  // Time series for trend
  const trendData = data
    .filter(d => d.metric_name === 'demographic_parity_difference')
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .slice(-14)
    .map(d => ({
      time: new Date(d.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: Math.abs(d.metric_value),
    }));

  return (
    <div style={{
      background: '#1e293b', borderRadius: '12px', padding: '24px',
      border: '1px solid #334155',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: 600 }}>⚖️ Bias & Fairness</h3>
          <p style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>Latest fairness metrics</p>
        </div>
        <span style={{
          padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 600,
          background: chartData.every(d => d.isFair) ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
          color: chartData.every(d => d.isFair) ? '#10b981' : '#ef4444',
        }}>
          {chartData.every(d => d.isFair) ? '✓ Fair' : '⚠ Issues Detected'}
        </span>
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
          <XAxis type="number" stroke="#64748b" fontSize={11} />
          <YAxis type="category" dataKey="name" width={140} stroke="#64748b" fontSize={10} />
          <Tooltip
            contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }}
          />
          <ReferenceLine x={0.1} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: 'Threshold', fill: '#f59e0b', fontSize: 10 }} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.isFair ? '#10b981' : '#ef4444'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Metric cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', marginTop: '16px' }}>
        {chartData.slice(0, 4).map((m, i) => (
          <div key={i} style={{
            padding: '10px', borderRadius: '8px',
            background: m.isFair ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
            border: `1px solid ${m.isFair ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`,
          }}>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>{m.name}</div>
            <div style={{
              fontSize: '18px', fontWeight: 700, marginTop: '2px',
              color: m.isFair ? '#10b981' : '#ef4444',
            }}>
              {m.raw.toFixed(4)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}