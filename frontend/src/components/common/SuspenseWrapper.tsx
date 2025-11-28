import React, { Suspense } from 'react';
import { Box, Skeleton, Stack } from '@mui/material';

type FallbackVariant = 'spinner' | 'skeleton' | 'card' | 'list';

interface SuspenseWrapperProps {
  children: React.ReactNode;
  /** Minimum height for the loading container. Default: 200 */
  minHeight?: number | string;
  /** Fallback variant: 'spinner' (legacy), 'skeleton' (default), 'card', or 'list' */
  variant?: FallbackVariant;
  /** Number of skeleton items for list variant. Default: 3 */
  skeletonCount?: number;
}

/**
 * Skeleton fallback for card-style content
 */
const CardSkeleton: React.FC<{ minHeight: number | string }> = ({ minHeight }) => (
  <Box sx={{ width: '100%', minHeight, p: 2 }}>
    <Skeleton
      variant="rectangular"
      width="100%"
      height={120}
      sx={{
        bgcolor: 'var(--color-bg-interactive)',
        borderRadius: 1,
        mb: 2,
      }}
    />
    <Skeleton
      variant="text"
      width="60%"
      sx={{ bgcolor: 'var(--color-bg-interactive)', mb: 1 }}
    />
    <Skeleton
      variant="text"
      width="80%"
      sx={{ bgcolor: 'var(--color-bg-interactive)' }}
    />
  </Box>
);

/**
 * Skeleton fallback for list-style content
 */
const ListSkeleton: React.FC<{ count: number }> = ({ count }) => (
  <Stack spacing={1.5} sx={{ width: '100%', p: 1 }}>
    {Array.from({ length: count }).map((_, index) => (
      <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Skeleton
          variant="circular"
          width={32}
          height={32}
          sx={{ bgcolor: 'var(--color-bg-interactive)', flexShrink: 0 }}
        />
        <Box sx={{ flex: 1 }}>
          <Skeleton
            variant="text"
            width={`${70 + Math.random() * 20}%`}
            sx={{ bgcolor: 'var(--color-bg-interactive)' }}
          />
          <Skeleton
            variant="text"
            width={`${40 + Math.random() * 30}%`}
            height={12}
            sx={{ bgcolor: 'var(--color-bg-interactive)' }}
          />
        </Box>
      </Box>
    ))}
  </Stack>
);

/**
 * Default skeleton fallback (simple rectangular placeholder)
 */
const DefaultSkeleton: React.FC<{ minHeight: number | string }> = ({ minHeight }) => (
  <Box sx={{ width: '100%', minHeight, p: 1 }}>
    <Skeleton
      variant="rectangular"
      width="100%"
      height="100%"
      sx={{
        bgcolor: 'var(--color-bg-interactive)',
        borderRadius: 1,
        minHeight: typeof minHeight === 'number' ? minHeight - 16 : minHeight,
      }}
      animation="wave"
    />
  </Box>
);

/**
 * Legacy spinner fallback (CircularProgress)
 */
const SpinnerFallback: React.FC<{ minHeight: number | string }> = ({ minHeight }) => (
  <Box
    display="flex"
    justifyContent="center"
    alignItems="center"
    minHeight={minHeight}
  >
    <Box
      sx={{
        width: 24,
        height: 24,
        borderRadius: '50%',
        border: '2px solid var(--color-bg-interactive)',
        borderTopColor: 'var(--color-accent-primary)',
        animation: 'spin 1s linear infinite',
        '@keyframes spin': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      }}
    />
  </Box>
);

/**
 * SuspenseWrapper Component
 *
 * A reusable Suspense wrapper with skeleton loading states for better UX.
 * Use this to wrap lazy-loaded components for a uniform loading experience.
 *
 * @example Basic usage (skeleton fallback)
 * <SuspenseWrapper>
 *   <LazyComponent />
 * </SuspenseWrapper>
 *
 * @example Card-style skeleton
 * <SuspenseWrapper variant="card" minHeight={200}>
 *   <LazyCardComponent />
 * </SuspenseWrapper>
 *
 * @example List-style skeleton
 * <SuspenseWrapper variant="list" skeletonCount={5}>
 *   <LazyListComponent />
 * </SuspenseWrapper>
 *
 * @example Legacy spinner fallback
 * <SuspenseWrapper variant="spinner" minHeight={100}>
 *   <SmallLazyComponent />
 * </SuspenseWrapper>
 */
const SuspenseWrapper: React.FC<SuspenseWrapperProps> = ({
  children,
  minHeight = 200,
  variant = 'skeleton',
  skeletonCount = 3,
}) => {
  const getFallback = () => {
    switch (variant) {
      case 'spinner':
        return <SpinnerFallback minHeight={minHeight} />;
      case 'card':
        return <CardSkeleton minHeight={minHeight} />;
      case 'list':
        return <ListSkeleton count={skeletonCount} />;
      case 'skeleton':
      default:
        return <DefaultSkeleton minHeight={minHeight} />;
    }
  };

  return <Suspense fallback={getFallback()}>{children}</Suspense>;
};

export default SuspenseWrapper;
