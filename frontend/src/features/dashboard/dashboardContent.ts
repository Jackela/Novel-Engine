import type { CharacterCardData, WorldBeat } from '@/app/types';

export const characterRoster: CharacterCardData[] = [
  {
    id: 'c1',
    name: 'Mara Voss',
    role: 'Navigator',
    drive: 'Protect the archive',
    region: 'Salt Reach',
  },
  {
    id: 'c2',
    name: 'Ilan Rook',
    role: 'Broker',
    drive: 'Own the rumor market',
    region: 'Night Market',
  },
  {
    id: 'c3',
    name: 'Sera Flint',
    role: 'Scout',
    drive: 'Map the blackout zone',
    region: 'Ash Meridian',
  },
];

export const worldBeats: WorldBeat[] = [
  { id: 'w1', label: 'Pressure', value: 'High / 78%', tone: 'warm' },
  { id: 'w2', label: 'Signal drift', value: 'Stable / 12ms', tone: 'cool' },
  { id: 'w3', label: 'Active fronts', value: '3 zones', tone: 'neutral' },
];
