'use client';

import React, { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';

interface Props {
  data: any[];
}

export default function DriftChart({ data }: Props) {
  const features = useMemo(() => {
    const featureSet = new Set(data.map(d => d.feature_name));
    return Array.from(featureSet).slice(0, 5);
  }, [data]);

  const colors = ['#06b6d4', '#8b5cf6', '#f59e0b', '#10b981', '#f97316'];

  // Build time series by feature (KS test only)
  const timeSeriesMap = useMemo(() => {
    const ksData = data.filter(d => d.statistic_name === 'kolmogorov_smirnov');
    const byTime: Record<string, any> = {};

    for (const d of ksData) {
      const time = new Date(d.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      if (!byTime[time]) byTime[time] = { time };
      byTime[time][d.feature_name] = d.statistic_value;
    }

    return Object.values(byTime).sort((a: any, b: any) =>
      new Date(a.time).getTime() - new Date(b.time).getTime()
    );
  }, [data]);

  const driftedCount = data.filter(d => d.is_drifted).length;
  const totalChecks = data.length;

  return (
    <div style={{
      background: '#1e293b', borderRadius: '12px', padding: '24px',
      border: '1px solid #334155',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: 600 }}>📈 Drift Detection</h3>
          <p style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>KS statistic by feature over time</p>
        </div>
        <span style={{
          padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 600,
          background: driftedCount === 0 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
          color: driftedCount === 0 ? '#10b981' : '#f59e0b',
        }}>
          {driftedCount}/{totalChecks} drifted
        </span>
      </div>

      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={timeSeriesMap} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
          <YAxis stroke="#64748b" fontSize={11} />
          <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }} />
          <ReferenceLine y={0.05} stroke="#ef4444" strokeDasharray="3 3" label={{ value: 'α=0.05', fill: '#ef4444', fontSize: 10 }} />
          {features.map((feat, i) => (
            <Line
              key={feat}
              type="monotone"
              dataKey={feat}
              stroke={colors[i % colors.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
              name={feat}
            />
          ))}
          <Legend wrapperStyle={{ fontSize: '11px' }} />
        </LineChart>
      </ResponsiveContainer>

      {/* Feature drift status */}
      <div style={{ display: 'flex', gap: '6px', marginTop: '12px', flexWrap: 'wrap' }}>
        {features.map((feat, i) => {
          const latestDrift = data
            .filter(d => d.feature_name === feat && d.statistic_name === 'kolmogorov_smirnov')
            .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0];

          const isDrifted = latestDrift?.is_drifted;
          return (
            <span key={feat} style={{
              padding: '4px 10px', borderRadius: '6px', fontSize: '11px',
              background: isDrifted ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
              color: isDrifted ? '#ef4444' : '#10b981',
              border: `1px solid ${isDrifted ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)'}`,
            }}>
              {isDrifted ? '⚠' : '✓'} {feat}
            </span>
          );
        })}
      </div>
    </div>
  );
}