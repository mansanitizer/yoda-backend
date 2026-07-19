'use client';
import { Card, Icon } from './ui';
import { Insight } from '@/lib/types';

const sectionTitle = { fontFamily: 'var(--font-display)', fontWeight: 800 as const, fontSize: 22, color: 'var(--text-primary)' };

export function Insights({ insights }: { insights: Insight[] }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <span style={sectionTitle}>Coach insights</span>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 20 }}>
        {insights.map((ins, i) => (
          <Card key={i}>
            <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
              <div style={{ width: 40, height: 40, borderRadius: 999, background: ins.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon name={ins.icon} size={20} color={ins.color} />
              </div>
              <span style={{ fontFamily: 'var(--font-body)', fontSize: 15, lineHeight: 1.5 }}>{ins.text}</span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
