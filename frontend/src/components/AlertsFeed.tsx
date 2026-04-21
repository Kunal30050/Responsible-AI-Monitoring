'use client';

import React from 'react';

interface Props {
  alerts: any[];
}

export default function AlertsFeed({ alerts }: Props) {
  const severityConfig: Record<string, { icon: string; color: string; bg: string }> = {
    low: { icon: 'ℹ️', color: '#06b6d4', bg: 'rgba(6, 182, 212, 0.1)' },
    medium: { icon: '⚠️', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)' },
    high: { icon: '🔴', color: '#f97316', bg: 'rgba(249, 115, 22, 0.1)' },
    critical: { icon: '🚨', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)' },
  };

  return (
    <div style={{
      background: '#1e293b', borderRadius: '12px', padding: '24px',
      border: '1px solid #334155',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: 600 }}>🔔 Alert Feed</h3>
          <p style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>Recent alerts and notifications</p>
        </div>
        <span style={{ fontSize: '12px', color: '#64748b' }}>
          {alerts.filter(a => !a.acknowledged).length} unacknowledged
        </span>
      </div>

      <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
        {alerts.length === 0 ? (
          <div style={{
            textAlign: 'center', padding: '40px', color: '#64748b',
          }}>
            <span style={{ fontSize: '32px' }}>✅</span>
            <p style={{ marginTop: '8px' }}>No active alerts</p>
          </div>
        ) : (
          alerts.slice(0, 20).map((alert, i) => {
            const config = severityConfig[alert.severity] || severityConfig.low;
            return (
              <div key={alert.id || i} style={{
                display: 'flex', gap: '12px', padding: '12px',
                borderRadius: '8px', marginBottom: '4px',
                background: alert.acknowledged ? 'transparent' : config.bg,
                border: `1px solid ${alert.acknowledged ? '#334155' : config.color}20`,
                opacity: alert.acknowledged ? 0.6 : 1,
              }}>
                <span style={{ fontSize: '18px', flexShrink: 0 }}>{config.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{
                      fontSize: '12px', fontWeight: 600, color: config.color,
                      textTransform: 'uppercase',
                    }}>
                      {alert.severity}
                    </span>
                    <span style={{ fontSize: '11px', color: '#64748b' }}>
                      {new Date(alert.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p style={{
                    fontSize: '13px', color: '#e2e8f0', marginTop: '4px',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    Model {alert.model_id} — metric value: {alert.metric_value?.toFixed(4)}
                  </p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}