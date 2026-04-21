'use client';

import React from 'react';

interface Props {
  children: React.ReactNode;
  models: any[];
  selectedModel: number;
  onModelSelect: (id: number) => void;
}

export default function DashboardLayout({ children, models, selectedModel, onModelSelect }: Props) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <aside style={{
        width: '280px', background: '#1e293b', padding: '24px 16px',
        borderRight: '1px solid #334155', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '32px' }}>
          <div style={{
            width: '40px', height: '40px', borderRadius: '10px',
            background: 'linear-gradient(135deg, #06b6d4, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '20px',
          }}>🛡️</div>
          <div>
            <h1 style={{ fontSize: '16px', fontWeight: 700, color: '#f1f5f9' }}>RAI Monitor</h1>
            <p style={{ fontSize: '11px', color: '#64748b' }}>Responsible AI Platform</p>
          </div>
        </div>

        <nav>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#64748b', marginBottom: '12px', letterSpacing: '1px' }}>
            Monitored Models
          </div>
          {models.map((m: any) => (
            <button
              key={m.id}
              onClick={() => onModelSelect(m.id)}
              style={{
                display: 'block', width: '100%', padding: '12px', marginBottom: '4px',
                borderRadius: '8px', border: 'none', cursor: 'pointer', textAlign: 'left',
                background: selectedModel === m.id ? 'rgba(6, 182, 212, 0.15)' : 'transparent',
                color: selectedModel === m.id ? '#06b6d4' : '#94a3b8',
                fontSize: '13px', transition: 'all 0.2s',
              }}
            >
              <div style={{ fontWeight: 600 }}>{m.name}</div>
              <div style={{ fontSize: '11px', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{
                  width: '8px', height: '8px', borderRadius: '50%',
                  background: m.risk_level === 'low' ? '#10b981' : m.risk_level === 'medium' ? '#f59e0b' : m.risk_level === 'high' ? '#f97316' : '#ef4444',
                  display: 'inline-block',
                }} />
                {m.risk_level || 'unknown'} risk
              </div>
            </button>
          ))}
        </nav>

        <div style={{ marginTop: '32px' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#64748b', marginBottom: '12px', letterSpacing: '1px' }}>
            Navigation
          </div>
          {['Dashboard', 'Bias Analysis', 'Drift Detection', 'Explainability', 'Risk Scores', 'Alerts', 'Settings'].map(item => (
            <button key={item} style={{
              display: 'block', width: '100%', padding: '10px 12px', marginBottom: '2px',
              borderRadius: '8px', border: 'none', cursor: 'pointer', textAlign: 'left',
              background: item === 'Dashboard' ? 'rgba(6, 182, 212, 0.1)' : 'transparent',
              color: item === 'Dashboard' ? '#06b6d4' : '#94a3b8',
              fontSize: '13px',
            }}>
              {item}
            </button>
          ))}
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, padding: '24px 32px', overflowY: 'auto', background: '#0f172a' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <h2 style={{ fontSize: '24px', fontWeight: 700 }}>AI Monitoring Dashboard</h2>
            <p style={{ color: '#64748b', fontSize: '13px', marginTop: '4px' }}>
              Real-time monitoring for fairness, drift, explainability & risk
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <span style={{
              padding: '6px 12px', borderRadius: '20px', fontSize: '12px',
              background: 'rgba(16, 185, 129, 0.15)', color: '#10b981',
            }}>
              ● System Healthy
            </span>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}