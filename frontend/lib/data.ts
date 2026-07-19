import { SessionData, UserData, Insight } from './types';

const AVATAR_COUNT = 10;

export function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 31 + str.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

export function avatarIndex(username: string): number {
  return (hashString(username) % AVATAR_COUNT) + 1;
}

export function avatarUrl(username: string): string {
  return `/avatars/${avatarIndex(username)}.svg`;
}

export function genInsights(session: SessionData, user: UserData): Insight[] {
  const insights: Insight[] = [];
  const avg = (arr: number[]) => (arr.length ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length) : null);
  const left = avg(session.timeline.filter((t) => t.hand === 'LEFT' && t.success).map((t) => t.time));
  const right = avg(session.timeline.filter((t) => t.hand === 'RIGHT' && t.success).map((t) => t.time));
  if (left != null && right != null) {
    if (Math.abs(left - right) > 25) {
      const slower = left > right ? 'left' : 'right';
      const faster = slower === 'left' ? 'right' : 'left';
      const diff = Math.abs(left - right);
      insights.push({ icon: 'activity', bg: `var(--accent-${slower}-tint)`, color: `var(--accent-${slower})`, text: `Your ${slower} hand is running ${diff}ms slower than your ${faster} hand tonight.` });
    } else {
      insights.push({ icon: 'scale', bg: 'var(--ink-700)', color: 'var(--text-secondary)', text: 'Balanced hands today — nearly identical left and right reaction times.' });
    }
  }
  const best = Math.max(...user.sessions.map((s) => s.score));
  if (session.score >= best) {
    insights.push({ icon: 'trophy', bg: 'var(--accent-right-tint)', color: 'var(--accent-right)', text: 'New personal best session score.' });
  } else if (session.accuracy >= 95) {
    insights.push({ icon: 'check-circle', bg: 'var(--accent-right-tint)', color: 'var(--accent-right)', text: 'Excellent consistency today — accuracy held above 95%.' });
  }
  if (session.longestStreak >= 8) {
    insights.push({ icon: 'flame', bg: 'var(--accent-left-tint)', color: 'var(--accent-left)', text: `Longest streak of the session: ${session.longestStreak} correct reactions in a row.` });
  }
  if (insights.length < 3) {
    insights.push({ icon: 'trending-up', bg: 'var(--ink-700)', color: 'var(--text-secondary)', text: 'Keep training daily to build a longer streak.' });
  }
  return insights.slice(0, 3);
}

export interface ChartPoint { x: number; y: number; value: number; label: string; }
export function buildChart(data: { dateLabel: string;[k: string]: any }[], key: string) {
  if (data.length === 0) return { points: [] as ChartPoint[], path: '' };
  const w = 600, h = 180, pad = 20;
  const values = data.map((d) => d[key]);
  const min = Math.min(...values), max = Math.max(...values);
  const range = max - min || 1;
  const n = data.length;
  const points: ChartPoint[] = data.map((d, i) => ({
    x: pad + (n > 1 ? i / (n - 1) : 0) * (w - 2 * pad),
    y: h - pad - ((d[key] - min) / range) * (h - 2 * pad),
    value: d[key],
    label: d.dateLabel,
  }));
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  return { points, path };
}
