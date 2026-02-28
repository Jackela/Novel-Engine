/**
 * TokenAnalyticsPanel - Token usage and cost analytics
 *
 * BRAIN-035A: Token Usage Analytics Dashboard
 * BRAIN-035B-01: Model Pricing Comparison
 * BRAIN-035B-02: Date Range Filter
 * BRAIN-035B-03: CSV Export
 *
 * Displays usage analytics, charts, and model pricing comparison.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  brainSettingsApi,
  type DailyStatsResponse,
  type ModelPricingResponse,
  type ModelUsageResponse,
} from '@/features/routing/api/brainSettingsApi';
import { DollarSign, Download, Loader2, TrendingUp } from 'lucide-react';
import { RealtimeUsagePanel } from './RealtimeUsagePanel';

export function TokenAnalyticsPanel() {
  // Date range filter state
  const [dateRangeMode, setDateRangeMode] = useState<'preset' | 'custom'>('preset');
  const [usageDays, setUsageDays] = useState(30);
  const [customStartDate, setCustomStartDate] = useState<string>('');
  const [customEndDate, setCustomEndDate] = useState<string>('');

  // Calculate effective date range for queries
  const getDaysFromDateRange = (): number => {
    if (dateRangeMode === 'custom' && customStartDate && customEndDate) {
      const start = new Date(customStartDate);
      const end = new Date(customEndDate);
      const diffTime = Math.abs(end.getTime() - start.getTime());
      return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
    }
    return usageDays;
  };

  const effectiveDays = getDaysFromDateRange();

  // Fetch usage analytics data
  const { data: usageSummary, isLoading: usageSummaryLoading } = useQuery({
    queryKey: ['usage-summary', effectiveDays],
    queryFn: () => brainSettingsApi.getUsageSummary(effectiveDays),
  });

  const { data: dailyUsage, isLoading: dailyUsageLoading } = useQuery({
    queryKey: ['daily-usage', effectiveDays],
    queryFn: () => brainSettingsApi.getDailyUsage(effectiveDays),
  });

  const { data: usageByModel, isLoading: usageByModelLoading } = useQuery({
    queryKey: ['usage-by-model'],
    queryFn: () => brainSettingsApi.getUsageByModel(),
  });

  const { data: modelPricing, isLoading: modelPricingLoading } = useQuery({
    queryKey: ['model-pricing'],
    queryFn: () => brainSettingsApi.getModelPricing(),
  });

  return (
    <div className="space-y-6">
      {/* Real-time Usage Counter */}
      <RealtimeUsagePanel />

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Tokens</CardDescription>
            <CardTitle className="flex items-center gap-2 text-2xl">
              {usageSummaryLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <TrendingUp className="h-5 w-5 text-primary" />
                  {(usageSummary?.total_tokens ?? 0).toLocaleString()}
                </>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-2">
            <p className="text-xs text-muted-foreground">
              {usageSummary?.period_end ? `Last ${usageDays} days` : '-'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Cost</CardDescription>
            <CardTitle className="flex items-center gap-2 text-2xl">
              {usageSummaryLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <DollarSign className="h-5 w-5 text-green-500" />$
                  {(usageSummary?.total_cost ?? 0).toFixed(4)}
                </>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-2">
            <p className="text-xs text-muted-foreground">
              {usageSummary?.period_end ? `Last ${usageDays} days` : '-'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Requests</CardDescription>
            <CardTitle className="text-2xl">
              {usageSummaryLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                (usageSummary?.total_requests ?? 0).toLocaleString()
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-2">
            <p className="text-xs text-muted-foreground">
              {usageSummary?.period_end
                ? `Avg ${((usageSummary?.total_tokens ?? 0) / (usageSummary?.total_requests || 1) || 0).toFixed(0)} tokens/request`
                : '-'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Avg Latency</CardDescription>
            <CardTitle className="text-2xl">
              {usageSummaryLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                `${(usageSummary?.avg_latency_ms ?? 0).toFixed(0)}ms`
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-2">
            <p className="text-xs text-muted-foreground">
              {usageSummary?.period_end ? 'Across all requests' : '-'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tokens Over Time Chart */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Tokens Over Time</CardTitle>
              <CardDescription>Daily token usage trend</CardDescription>
            </div>
            <div className="flex items-center gap-4">
              {/* Date range filter */}
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant={dateRangeMode === 'preset' ? 'default' : 'outline'}
                  onClick={() => setDateRangeMode('preset')}
                >
                  Preset
                </Button>
                <Button
                  size="sm"
                  variant={dateRangeMode === 'custom' ? 'default' : 'outline'}
                  onClick={() => setDateRangeMode('custom')}
                >
                  Custom
                </Button>
              </div>

              {dateRangeMode === 'preset' ? (
                <div className="flex gap-2">
                  {[7, 30, 90].map((days) => (
                    <Button
                      key={days}
                      size="sm"
                      variant={usageDays === days ? 'default' : 'outline'}
                      onClick={() => setUsageDays(days)}
                    >
                      {days}d
                    </Button>
                  ))}
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Input
                    type="date"
                    value={customStartDate}
                    onChange={(e) => setCustomStartDate(e.target.value)}
                    className="w-auto"
                  />
                  <span className="text-muted-foreground">to</span>
                  <Input
                    type="date"
                    value={customEndDate}
                    onChange={(e) => setCustomEndDate(e.target.value)}
                    className="w-auto"
                  />
                  <Button
                    size="sm"
                    disabled={!customStartDate || !customEndDate}
                    onClick={() => {
                      if (customStartDate && customEndDate) {
                        const start = new Date(customStartDate);
                        const end = new Date(customEndDate);
                        const diffTime = Math.abs(end.getTime() - start.getTime());
                        const days = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
                        setUsageDays(days);
                      }
                    }}
                  >
                    Apply
                  </Button>
                </div>
              )}

              {/* CSV Export button */}
              <Button
                size="sm"
                variant="outline"
                onClick={() => brainSettingsApi.exportUsageCsv(effectiveDays)}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                Export CSV
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {dailyUsageLoading ? (
            <div className="flex h-64 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : dailyUsage && dailyUsage.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={dailyUsage}>
                  <defs>
                    <linearGradient id="tokensGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="5%"
                        stopColor="hsl(var(--primary))"
                        stopOpacity={0.3}
                      />
                      <stop
                        offset="95%"
                        stopColor="hsl(var(--primary))"
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="hsl(var(--border))"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(value) => {
                      const date = new Date(value);
                      return date.toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                      });
                    }}
                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                    tickLine={{ stroke: 'hsl(var(--border))' }}
                    axisLine={{ stroke: 'hsl(var(--border))' }}
                  />
                  <YAxis
                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                    tickLine={{ stroke: 'hsl(var(--border))' }}
                    axisLine={{ stroke: 'hsl(var(--border))' }}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.[0]) return null;
                      const data = payload[0].payload as DailyStatsResponse;
                      return (
                        <div className="rounded-md border bg-popover px-3 py-2 shadow-md">
                          <p className="mb-1 font-medium">
                            {new Date(data.date).toLocaleDateString('en-US', {
                              month: 'short',
                              day: 'numeric',
                            })}
                          </p>
                          <p className="text-sm">
                            Tokens:{' '}
                            <span className="font-medium">
                              {data.total_tokens.toLocaleString()}
                            </span>
                          </p>
                          <p className="text-sm">
                            Cost:{' '}
                            <span className="font-medium">
                              ${data.total_cost.toFixed(4)}
                            </span>
                          </p>
                          <p className="text-sm">
                            Requests:{' '}
                            <span className="font-medium">{data.total_requests}</span>
                          </p>
                        </div>
                      );
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="total_tokens"
                    stroke="hsl(var(--primary))"
                    fill="url(#tokensGradient)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-64 items-center justify-center text-muted-foreground">
              No usage data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Cost by Model Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Cost by Model</CardTitle>
          <CardDescription>Total cost breakdown per model</CardDescription>
        </CardHeader>
        <CardContent>
          {usageByModelLoading ? (
            <div className="flex h-64 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : usageByModel && usageByModel.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={usageByModel}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="hsl(var(--border))"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="model_identifier"
                    angle={-45}
                    textAnchor="end"
                    height={80}
                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                    tickLine={{ stroke: 'hsl(var(--border))' }}
                    axisLine={{ stroke: 'hsl(var(--border))' }}
                  />
                  <YAxis
                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                    tickLine={{ stroke: 'hsl(var(--border))' }}
                    axisLine={{ stroke: 'hsl(var(--border))' }}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.[0]) return null;
                      const data = payload[0].payload as ModelUsageResponse;
                      return (
                        <div className="rounded-md border bg-popover px-3 py-2 shadow-md">
                          <p className="mb-1 font-medium">{data.model_identifier}</p>
                          <p className="text-sm">
                            Cost:{' '}
                            <span className="font-medium">
                              ${data.total_cost.toFixed(4)}
                            </span>
                          </p>
                          <p className="text-sm">
                            Tokens:{' '}
                            <span className="font-medium">
                              {data.total_tokens.toLocaleString()}
                            </span>
                          </p>
                          <p className="text-sm">
                            Requests:{' '}
                            <span className="font-medium">{data.total_requests}</span>
                          </p>
                        </div>
                      );
                    }}
                  />
                  <Bar
                    dataKey="total_cost"
                    fill="hsl(var(--primary))"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-64 items-center justify-center text-muted-foreground">
              No usage data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Provider Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Provider Distribution</CardTitle>
          <CardDescription>Usage breakdown by LLM provider</CardDescription>
        </CardHeader>
        <CardContent>
          {usageByModelLoading ? (
            <div className="flex h-48 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : usageByModel && usageByModel.length > 0 ? (
            <div className="space-y-3">
              {Object.entries(
                usageByModel.reduce(
                  (acc, item) => {
                    const provider = item.provider;
                    if (!acc[provider]) {
                      acc[provider] = { cost: 0, tokens: 0, requests: 0 };
                    }
                    acc[provider].cost += item.total_cost;
                    acc[provider].tokens += item.total_tokens;
                    acc[provider].requests += item.total_requests;
                    return acc;
                  },
                  {} as Record<
                    string,
                    { cost: number; tokens: number; requests: number }
                  >
                )
              ).map(([provider, stats]) => {
                const totalCost = usageByModel.reduce(
                  (sum, item) => sum + item.total_cost,
                  0
                );
                const percentage = totalCost > 0 ? (stats.cost / totalCost) * 100 : 0;
                return (
                  <div key={provider} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium capitalize">{provider}</span>
                      <span className="text-muted-foreground">
                        ${stats.cost.toFixed(4)} ({percentage.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex h-48 items-center justify-center text-muted-foreground">
              No usage data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Model Pricing Comparison */}
      <Card>
        <CardHeader>
          <CardTitle>Model Pricing Comparison</CardTitle>
          <CardDescription>Cost per 1M tokens for each available model</CardDescription>
        </CardHeader>
        <CardContent>
          {modelPricingLoading ? (
            <div className="flex h-48 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : modelPricing && modelPricing.length > 0 ? (
            <div className="space-y-6">
              {(() => {
                // Group models by provider
                const grouped = modelPricing.reduce(
                  (acc, model) => {
                    const provider = model.provider ?? 'unknown';
                    if (!acc[provider]) {
                      acc[provider] = [];
                    }
                    acc[provider].push(model);
                    return acc;
                  },
                  {} as Record<string, ModelPricingResponse[]>
                );

                const providerLabels: Record<string, string> = {
                  openai: 'OpenAI',
                  anthropic: 'Anthropic',
                  gemini: 'Google Gemini',
                  ollama: 'Ollama (Local)',
                  mock: 'Mock',
                };

                return Object.entries(grouped).map(([provider, models]) => (
                  <div key={provider} className="space-y-3">
                    <h3 className="flex items-center gap-2 text-lg font-semibold capitalize">
                      {providerLabels[provider] || provider}
                    </h3>
                    <div className="overflow-x-auto rounded-lg border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Model</TableHead>
                            <TableHead className="text-right">Input / 1M</TableHead>
                            <TableHead className="text-right">Output / 1M</TableHead>
                            <TableHead className="text-right">Context</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {models.map((model) => (
                            <TableRow key={`${model.provider}-${model.model_name}`}>
                              <TableCell>
                                <div>
                                  <div className="font-medium">{model.display_name}</div>
                                  <div className="text-xs text-muted-foreground">
                                    {model.model_name}
                                  </div>
                                </div>
                              </TableCell>
                              <TableCell className="text-right">
                                ${model.cost_per_1m_input_tokens.toFixed(2)}
                              </TableCell>
                              <TableCell className="text-right">
                                ${model.cost_per_1m_output_tokens.toFixed(2)}
                              </TableCell>
                              <TableCell className="text-right">
                                {model.max_context_tokens.toLocaleString()}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                ));
              })()}
            </div>
          ) : (
            <div className="flex h-48 items-center justify-center text-muted-foreground">
              No model pricing data available
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
