'use client';
import { Card, Icon } from './ui';
import { UserData } from '@/lib/types';
import { useCountUp } from '@/lib/hooks';

const label = { fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-secondary)', fontWeight: 600 as const };

export function StatCards({ user }: { user: UserData }) {
  const hasSessions = user.sessionCount > 0;
  const counts = useCountUp(
    { score: user.score, reaction: user.medianReaction, accuracy: user.accuracy, streak: user.streak },
    user.id
  );

  const statCards = [
    { label: 'Yoda score', value: counts.score || 0, unit: '', icon: 'trophy', color: 'var(--text-primary)' },
    { label: 'Median reaction', value: counts.reaction || 0, unit: 'ms', icon: 'zap', color: 'var(--accent-right)' },
    { label: 'Accuracy', value: counts.accuracy || 0, unit: '%', icon: 'target', color: 'var(--text-primary)' },
    { label: 'Current streak', value: counts.streak || 0, unit: 'd', icon: 'flame', color: 'var(--accent-left)' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 20 }}>
      {statCards.map((stat) => (
        <Card key={stat.label}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={label}>{stat.label}</span>
              <Icon name={stat.icon} size={20} color="var(--text-tertiary)" />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 40, fontWeight: 700, color: hasSessions ? stat.color : 'var(--text-tertiary)' }}>{hasSessions ? stat.value : '–'}</span>
              {hasSessions && stat.unit && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 15, color: 'var(--text-tertiary)' }}>{stat.unit}</span>}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
