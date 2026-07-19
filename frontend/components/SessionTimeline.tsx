'use client';
import { Card, Badge, Icon } from './ui';
import { SessionData } from '@/lib/types';

const sectionTitle = { fontFamily: 'var(--font-display)', fontWeight: 800 as const, fontSize: 22, color: 'var(--text-primary)' };

export function SessionTimeline({ session }: { session: SessionData }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <span style={sectionTitle}>Punch timeline</span>
      <Card padding={0}>
        <div style={{ display: 'flex', flexDirection: 'column', maxHeight: 520, overflowY: 'auto' }}>
          {session.timeline.map((row, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '14px 24px', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-tertiary)', width: 24 }}>{i + 1}</span>
              <Badge tone={row.hand === 'LEFT' ? 'left' : 'right'}>{row.hand}</Badge>
              <span style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: 15 }}>{row.success ? `${row.time} ms` : 'Wrong hand'}</span>
              <Icon name={row.success ? 'check-circle' : 'x-circle'} size={18} color={row.success ? 'var(--accent-right)' : 'var(--accent-left)'} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
