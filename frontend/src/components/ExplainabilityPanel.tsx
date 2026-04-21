'use client';

import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { explainPrediction } from '@/lib/api';

interface Props {
  modelId: number;
}

export default function ExplainabilityPanel({ modelId }: Props) {
  const [explanation, setExplanation] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [method, setMethod] = useState<'shap' | 'lime'>('shap');

  const sampleInstance = {
    age: 35.0,
    income: 55000.0,
    credit_score: 720.0,
    debt_ratio: 0.3,
    employment_years: 8.0,
  };

  const runExplanation = async () => {
    setLoading(true);
    try {
      const result = await explainPrediction({
        model_id: modelId,
        instance: sampleInstance,
        method,
      });
      setExplanation(result);
    } catch (error) {
      console.error('Explanation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const chartData = explanation
    ? Object.entries(explanation.feature_importances)
        .map(([name, value]: [string, any]) => ({
          name: name.length > 20 ? name.substring(0, 20) : name,
          value: parseFloat(value),
          positive: parseFloat(value) >= 0,
        }))
        .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
        .slice(0, 10)
    : [];

  return (
    <div style={{
      background: '#1e293b', borderRadius: '12px', padding: '24px',
      border: '1px solid #334155',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: 600 }}>🔍 Explainability</h3>
          <p style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>SHAP / LIME feature attributions</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {(['shap', 'lime'] as const).map(m => (
            <button
              key={m}
              onClick={() => setMethod(m)}
              style={{
                padding: '4px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 600,
                border: 'none', cursor: 'pointer',
                background: method === m ? '#06b6d4' : '#334155',
                color: method === m ? '#0f172a' : '#94a3b8',
              }}
            >
              {m.toUpperCase()}
            </button>
          ))}
          <button
            onClick={runExplanation}
            disabled={loading}
            style={{
              padding: '4px 16px', borderRadius: '6px', fontSize: '12px', fontWeight: 600,
              border: 'none', cursor: 'pointer',
              background: loading ? '#334155' : '#8b5cf6', color: '#fff',
            }}
          >
            {loading ? 'Running...' : 'Explain ▶'}
          </button>
        </div>
      </div>

      {explanation ? (
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
            <XAxis type="number" stroke="#64748b" fontSize={11} />
            <YAxis type="category" dataKey="name" width={120} stroke="#64748b" fontSize={10} />
            <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.positive ? '#10b981' : '#ef4444'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div style={{
          height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#64748b', fontSize: '14px', flexDirection: 'column', gap: '8px',
        }}>
          <span style={{ fontSize: '32px' }}>🔍</span>
          Click "Explain" to generate feature attributions
        </div>
      )}

      {/* Sample instance display */}
      <div style={{ marginTop: '12px', padding: '12px', background: '#0f172a', borderRadius: '8px' }}>
        <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '6px' }}>Sample Instance:</div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {Object.entries(sampleInstance).map(([k, v]) => (
            <span key={k} style={{
              padding: '2px 8px', borderRadius: '4px', fontSize: '11px',
              background: '#1e293b', color: '#94a3b8',
            }}>
              {k}: <strong style={{ color: '#f1f5f9' }}>{v}</strong>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}