// Data shapes returned by the backend API. Keep in sync with the server contract
// documented in .env.example.

export interface PunchEvent { 
  hand: 'LEFT' | 'RIGHT'; 
  time: number; 
  success: boolean; 
}

export interface SessionData {
  id: string; 
  date: string; 
  dateLabel: string; 
  fullDateLabel: string; 
  punches: number;
  timeline: PunchEvent[]; 
  longestStreak: number; 
  accuracy: number; 
  median: number; 
  fastest: number; 
  score: number;
}

export interface HeatCell { 
  date: string; 
  label: string; 
  count: number; 
}

export interface UserData {
  id: string;
  username: string;
  sessions: SessionData[];
  score: number;
  accuracy: number;
  medianReaction: number;
  sessionCount: number;
  heatmap: HeatCell[];
  streak: number;
}

export interface Insight { 
  icon: string; 
  bg: string; 
  color: string;
  text: string; 
}
