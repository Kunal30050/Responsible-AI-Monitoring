'use client';

import React from 'react';

interface Props {
  summary: any;
  loading: boolean;
}

export default function MetricsOverview({ summary, loading }: Props) {
  const metrics = [
    {
      label: 'Monitored Models',
      value: summary?.total_models ?? '—',
      icon: '🤖',
      color: '#06b6d4',
      bg: 'rgba(6, 182, 212, 0.1)',
    },
    {
      label: 'Predictions (24h)',
      value: summary?.total_predictions_24h?.toLocaleString() ?? '—',
      icon: '📊',
      color: '#8b5cf6',
      bg: 'rgba(139, 92, 246, 0.1)',
    },
    {
      label: 'Active Alerts',
      value: summary?.active_alerts ?? '—',
      icon: '🚨',
      color: summary?.active_alerts > 0 ? '#ef4444' : '#10b981',
      bg: summary?.active_alerts > 0 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
    },
    {
      label: 'Avg Risk Score',
      value: summary?.avg_risk_score?.toFixed(2) ?? '—',
      icon: '⚠️',
      color: (summary?.avg_risk_score ?? 0) > 0.5 ? '#f59e0b' : '#10b981',
      bg: (summary?.avg_risk_score ?? 0) > 0.5 ? 'rgba(245, 158, 11, 0.1)' : 'rgba(16, 185, 129, 0.1)',
    },
    {
      label: 'Bias Issues',
      value: summary?.bias_issues ?? '—',
      icon: '⚖️',
      color: (summary?.bias_issues ?? 0) > 0 ? '#f97316' : '#10b981',
      bg: (summary?.bias_issues ?? 0) > 0 ? 'rgba(249, 115, 22, 0.1)' : 'rgba(16, 185, 129, 0.1)',
    },
    {
      label: 'Drift Detected',
      value: summary?.drift_detected ?? '—',
      icon: '📈',
      color: (summary?.drift_detected ?? 0) > 0 ? '#f59e0b' : '#10b981',
      bg: (summary?.drift_detected ?? 0) > 0 ? 'rgba(245, 158, 11, 0.1)' : 'rgba(16, 185, 129, 0.1)',
    },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '16px' }}>
      {metrics.map((m, i) => (
        <div key={i} style={{
          background: '#1e293b', borderRadius: '12px', padding: '20px',
          border: '1px solid #334155',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{
              fontSize: '24px', width: '44px', height: '44px', borderRadius: '10px',
              background: m.bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>{m.icon}</span>
          </div>
          <div style={{ marginTop: '16px' }}>
            <div style={{ fontSize: '24px', fontWeight: 700, color: m.color }}>
              {loading ? '...' : m.value}
            </div>
            <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
              {m.label}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}