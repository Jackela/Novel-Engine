import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ThemeProvider } from '@mui/material/styles';
import theme from '@/styles/theme';

describe('US3: Providers smoke test', () => {
  it('ThemeProvider + QueryClientProvider render without runtime errors', async () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <ThemeProvider theme={theme}>
          <div>providers-ok</div>
        </ThemeProvider>
      </QueryClientProvider>
    );
    expect(await screen.findByText('providers-ok')).toBeTruthy();
  });
});
