'use client';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Card, Icon } from '@/components/ui';
import { SessionTimeline } from '@/components/SessionTimeline';
import { Insights } from '@/components/Insights';
import { useApp } from '@/lib/store';
import { useQuery } from '@/lib/hooks';
import { api } from '@/lib/api';
import { genInsights } from '@/lib/data';
import { UserData } from '@/lib/types';

const label = { fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-secondary)', fontWeight: 600 as const };

export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const { getCachedUser, cacheUser } = useApp();

  const { data: session, loading: sessionLoading, error: sessionError } = useQuery(
    () => api.sessions.get(id),
    [id]
  );

  const cachedOwner = session ? getCachedUser(session.userId) : undefined;
  const { data: fetchedOwner, loading: ownerLoading, error: ownerError } = useQuery<UserData>(async () => {
    const owner = await api.users.get(session!.userId);
    cacheUser(owner);
    return owner;
  }, [session?.userId], !!session && !cachedOwner);

  const owner = cachedOwner ?? fetchedOwner;
  const loading = sessionLoading || (!!session && !owner && ownerLoading);
  const error = sessionError || ownerError;

  if (loading) {
    return (
      <div style={{ maxWidth: 'var(--container-desktop)', margin: '0 auto', padding: '96px 24px', textAlign: 'center', color: 'var(--text-tertiary)', fontFamily: 'var(--font-body)' }}>
        Loading session…
      </div>
    );
  }

  if (error || !session || !owner) {
    return (
      <div style={{ maxWidth: 'var(--container-desktop)', margin: '0 auto', padding: '96px 24px', textAlign: 'center', color: 'var(--text-tertiary)', fontFamily: 'var(--font-body)' }}>
        Session not found{error ? `: ${error.message}` : '.'}
      </div>
    );
  }

  const insights = genInsights(session, owner);

  return (
    <div style={{ maxWidth: 'var(--container-desktop)', margin: '0 auto', padding: '40px 24px 96px', display: 'flex', flexDirection: 'column', gap: 48, animation: 'fadeUp 0.4s var(--ease-out)' }}>
      <Link href="/dashboard" style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', color: 'var(--text-secondary)', width: 'fit-content', textDecoration: 'none' }}>
        <Icon name="arrow-left" size={18} color="var(--text-secondary)" />
        <span style={{ fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)' }}>Back to profile</span>
      </Link>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <span style={{ fontFamily: 'var(--font-body)', fontSize: 14, color: 'var(--text-secondary)' }}>{session.fullDateLabel}</span>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 900, fontSize: 72, letterSpacing: '-0.02em' }}>{session.score}</span>
          <span style={{ fontFamily: 'var(--font-body)', fontSize: 16, color: 'var(--text-secondary)' }}>session score</span>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 20 }}>
        {[
          { label: 'Accuracy', value: session.accuracy, unit: '%', color: 'var(--text-primary)' },
          { label: 'Median reaction', value: session.median, unit: 'ms', color: 'var(--accent-right)' },
          { label: 'Fastest reaction', value: session.fastest, unit: 'ms', color: 'var(--accent-right)' },
          { label: 'Longest streak', value: session.longestStreak, unit: '', color: 'var(--accent-left)' },
        ].map((stat) => (
          <Card key={stat.label}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <span style={label}>{stat.label}</span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 32, fontWeight: 700, color: stat.color }}>{stat.value}</span>
                {stat.unit && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14, color: 'var(--text-tertiary)' }}>{stat.unit}</span>}
              </div>
            </div>
          </Card>
        ))}
      </div>

      <SessionTimeline session={session} />
      <Insights insights={insights} />
    </div>
  );
}
