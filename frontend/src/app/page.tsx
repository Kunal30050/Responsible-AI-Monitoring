'use client';

import React, { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import MetricsOverview from '@/components/MetricsOverview';
import BiasCard from '@/components/BiasCard';
import DriftChart from '@/components/DriftChart';
import RiskGauge from '@/components/RiskGauge';
import ExplainabilityPanel from '@/components/ExplainabilityPanel';
import AlertsFeed from '@/components/AlertsFeed';
import { fetchDashboardSummary, fetchBiasHistory, fetchDriftHistory, fetchRiskHistory, fetchAlertHistory } from '@/lib/api';

export default function Dashboard() {
  const [summary, setSummary] = useState<any>(null);
  const [biasData, setBiasData] = useState<any[]>([]);
  const [driftData, setDriftData] = useState<any[]>([]);
  const [riskData, setRiskData] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<number>(1);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [summaryRes, biasRes, driftRes, riskRes, alertsRes] = await Promise.allSettled([
        fetchDashboardSummary(),
        fetchBiasHistory(selectedModel),
        fetchDriftHistory(selectedModel),
        fetchRiskHistory(selectedModel),
        fetchAlertHistory(),
      ]);

      if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value);
      if (biasRes.status === 'fulfilled') setBiasData(biasRes.value);
      if (driftRes.status === 'fulfilled') setDriftData(driftRes.value);
      if (riskRes.status === 'fulfilled') setRiskData(riskRes.value);
      if (alertsRes.status === 'fulfilled') setAlerts(alertsRes.value);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [selectedModel]);

  return (
    <DashboardLayout
      models={summary?.models || []}
      selectedModel={selectedModel}
      onModelSelect={setSelectedModel}
    >
      <MetricsOverview summary={summary} loading={loading} />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginTop: '24px' }}>
        <BiasCard data={biasData} />
        <DriftChart data={driftData} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginTop: '24px' }}>
        <RiskGauge data={riskData} />
        <ExplainabilityPanel modelId={selectedModel} />
      </div>

      <div style={{ marginTop: '24px' }}>
        <AlertsFeed alerts={alerts} />
      </div>
    </DashboardLayout>
  );
}