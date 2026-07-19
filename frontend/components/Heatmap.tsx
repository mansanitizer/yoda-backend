'use client';
import { useState } from 'react';
import { Card } from './ui';
import { UserData } from '@/lib/types';

const sectionTitle = { fontFamily: 'var(--font-display)', fontWeight: 800 as const, fontSize: 22, color: 'var(--text-primary)' };
const heatColors = ['var(--ink-800)', 'var(--accent-right-tint)', 'rgba(214,255,63,.35)', 'rgba(214,255,63,.65)', 'var(--accent-right)'];

export function Heatmap({ user }: { user: UserData }) {
  const [heatHover, setHeatHover] = useState<number | null>(null);
  const hasSessions = user.sessionCount > 0;

  const heatmapCaption = heatHover != null
    ? `${user.heatmap[heatHover].label} · ${user.heatmap[heatHover].count} session${user.heatmap[heatHover].count === 1 ? '' : 's'}`
    : hasSessions ? 'Hover a day to see details' : 'No activity yet';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
        <span style={sectionTitle}>Activity</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-tertiary)' }}>{heatmapCaption}</span>
      </div>
      <Card>
        <div style={{ display: 'grid', gridTemplateRows: 'repeat(7,12px)', gridAutoFlow: 'column', gridAutoColumns: 12, gap: 4, overflowX: 'auto', paddingBottom: 4 }}>
          {user.heatmap.map((cell, i) => (
            <div key={cell.date} onMouseEnter={() => setHeatHover(i)} onMouseLeave={() => setHeatHover(null)}
              style={{ width: 12, height: 12, borderRadius: 3, background: heatColors[cell.count], cursor: 'pointer', transition: 'transform var(--dur-fast) var(--ease-out)', transform: heatHover === i ? 'scale(1.35)' : 'scale(1)' }} />
          ))}
        </div>
      </Card>
    </div>
  );
}
