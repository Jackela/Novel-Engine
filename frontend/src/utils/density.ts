export type DensityMode = 'relaxed' | 'compact';

interface DensityOptions {
  count: number;
  relaxedThreshold: number;
}

export const getDensityMode = ({ count, relaxedThreshold }: DensityOptions): DensityMode => {
  if (count > relaxedThreshold) {
    return 'compact';
  }
  return 'relaxed';
};
