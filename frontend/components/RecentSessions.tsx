'use client';
import Link from 'next/link';
import { Card, Icon } from './ui';
import { UserData } from '@/lib/types';

const sectionTitle = { fontFamily: 'var(--font-display)', fontWeight: 800 as const, fontSize: 22, color: 'var(--text-primary)' };

export function RecentSessions({ user }: { user: UserData }) {
  const hasSessions = user.sessionCount > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <span style={sectionTitle}>Recent sessions</span>
      {!hasSessions && (
        <Card>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '24px 0', textAlign: 'center' }}>
            <Icon name="zap" size={24} color="var(--text-tertiary)" />
            <span style={{ fontFamily: 'var(--font-body)', fontSize: 14, color: 'var(--text-secondary)', fontWeight: 600 }}>No sessions logged yet</span>
            <span style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-tertiary)' }}>Complete a training session to see it here.</span>
          </div>
        </Card>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {user.sessions.map((s) => (
          <Link key={s.id} href={`/session/${s.id}`}
            className="session-card"
            style={{ display: 'grid', gridTemplateColumns: '96px 1fr auto', alignItems: 'center', gap: 20, background: 'var(--surface-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', padding: '20px 24px', cursor: 'pointer', textDecoration: 'none', color: 'inherit', transition: 'background var(--dur-md) var(--ease-out), transform var(--dur-fast) var(--ease-out)' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-secondary)' }}>{s.dateLabel}</span>
            <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span style={{ fontFamily: 'var(--font-body)', fontSize: 11, color: 'var(--text-tertiary)' }}>Score</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 16, fontWeight: 600 }}>{s.score}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span style={{ fontFamily: 'var(--font-body)', fontSize: 11, color: 'var(--text-tertiary)' }}>Median</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 16, fontWeight: 600, color: 'var(--accent-right)' }}>{s.median}<span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>ms</span></span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span style={{ fontFamily: 'var(--font-body)', fontSize: 11, color: 'var(--text-tertiary)' }}>Accuracy</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 16, fontWeight: 600 }}>{s.accuracy}%</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span style={{ fontFamily: 'var(--font-body)', fontSize: 11, color: 'var(--text-tertiary)' }}>Punches</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 16, fontWeight: 600 }}>{s.punches}</span>
              </div>
            </div>
            <Icon name="chevron-right" size={20} color="var(--text-tertiary)" />
          </Link>
        ))}
      </div>
    </div>
  );
}
