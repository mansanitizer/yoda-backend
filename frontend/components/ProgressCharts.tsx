'use client';
import { useState } from 'react';
import { Card } from './ui';
import { buildChart, ChartPoint } from '@/lib/data';
import { UserData } from '@/lib/types';

const sectionTitle = { fontFamily: 'var(--font-display)', fontWeight: 800 as const, fontSize: 22, color: 'var(--text-primary)' };

function EmptyChart() {
  return (
    <div style={{ height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: 13, fontFamily: 'var(--font-body)' }}>
      No sessions yet
    </div>
  );
}

function LineChart({ chart, chartKey, onHover }: { chart: { path: string; points: ChartPoint[] }; chartKey: string; onHover: (idx: number | null) => void }) {
  return (
    <svg viewBox="0 0 600 180" style={{ width: '100%', height: 160, overflow: 'visible' }}>
      <path d={chart.path} fill="none" stroke="var(--ink-300)" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
      {chart.points.map((p, i) => {
        const isLast = i === chart.points.length - 1;
        return (
          <circle key={i} cx={p.x} cy={p.y} r={isLast ? 6 : 4}
            fill={isLast ? 'var(--accent-right)' : 'var(--surface-card)'} stroke={isLast ? 'var(--accent-right)' : 'var(--ink-300)'} strokeWidth={2}
            style={{ cursor: 'pointer' }}
            onMouseEnter={() => onHover(i)}
            onMouseLeave={() => onHover(null)} />
        );
      })}
    </svg>
  );
}

export function ProgressCharts({ user }: { user: UserData }) {
  const hasSessions = user.sessionCount > 0;
  const [reactionHover, setReactionHover] = useState<number | null>(null);
  const [accuracyHover, setAccuracyHover] = useState<number | null>(null);

  const trendSlice = user.sessions.slice(0, 14).slice().reverse();
  const reactionChart = buildChart(trendSlice, 'median');
  const accuracyChart = buildChart(trendSlice, 'accuracy');
  const reactionTooltip = reactionHover != null ? reactionChart.points[reactionHover] : null;
  const accuracyTooltip = accuracyHover != null ? accuracyChart.points[accuracyHover] : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <span style={sectionTitle}>Progress</span>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(360px,1fr))', gap: 24 }}>
        <Card>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', minHeight: 20 }}>
              <span style={{ fontFamily: 'var(--font-body)', fontWeight: 700, fontSize: 15 }}>Reaction time</span>
              {reactionTooltip && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--accent-right)' }}>{reactionTooltip.value} ms · {reactionTooltip.label}</span>}
            </div>
            {hasSessions ? <LineChart chart={reactionChart} chartKey="reaction" onHover={setReactionHover} /> : <EmptyChart />}
          </div>
        </Card>
        <Card>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', minHeight: 20 }}>
              <span style={{ fontFamily: 'var(--font-body)', fontWeight: 700, fontSize: 15 }}>Accuracy</span>
              {accuracyTooltip && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--accent-right)' }}>{accuracyTooltip.value}% · {accuracyTooltip.label}</span>}
            </div>
            {hasSessions ? <LineChart chart={accuracyChart} chartKey="accuracy" onHover={setAccuracyHover} /> : <EmptyChart />}
          </div>
        </Card>
      </div>
    </div>
  );
}
