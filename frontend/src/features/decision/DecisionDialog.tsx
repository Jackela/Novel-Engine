/**
 * DecisionDialog - Decision point modal for narrative choices
 */
import { useEffect, useMemo } from 'react';
import { AlertTriangle, CheckCircle2, Timer } from 'lucide-react';
import { Button } from '@/shared/components/ui/Button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/Dialog';
import { useDecisionStore } from './decisionStore';
import { cn } from '@/lib/utils';

const MIN_FREE_TEXT_LENGTH = 5;
const MAX_FREE_TEXT_LENGTH = 500;

const formatCountdown = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.max(seconds % 60, 0);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export function DecisionDialog() {
  const {
    currentDecision,
    selectedOptionId,
    freeTextInput,
    remainingSeconds,
    inputMode,
    submitting,
    errorMessage,
    negotiationResult,
    setInputMode,
    setFreeText,
    setRemainingSeconds,
    selectOption,
    clearDecisionPoint,
    setNegotiationResult,
  } = useDecisionStore();

  const open = Boolean(currentDecision);

  const countdownTarget = useMemo(() => {
    if (!currentDecision) {
      return null;
    }
    if (currentDecision.expiresAt) {
      return new Date(currentDecision.expiresAt).getTime();
    }
    const start = currentDecision.createdAt
      ? new Date(currentDecision.createdAt).getTime()
      : Date.now();
    return start + currentDecision.timeoutSeconds * 1000;
  }, [currentDecision]);

  useEffect(() => {
    if (!currentDecision || !countdownTarget) {
      return;
    }
    const tick = () => {
      const secondsLeft = Math.ceil((countdownTarget - Date.now()) / 1000);
      setRemainingSeconds(secondsLeft);
    };
    tick();
    const interval = window.setInterval(tick, 1000);
    return () => window.clearInterval(interval);
  }, [currentDecision, countdownTarget, setRemainingSeconds]);

  useEffect(() => {
    if (!open) {
      setNegotiationResult(null);
    }
  }, [open, setNegotiationResult]);

  if (!currentDecision) {
    return null;
  }

  const confirmEnabled =
    !submitting &&
    ((inputMode === 'options' && selectedOptionId !== null) ||
      (inputMode === 'freeText' &&
        freeTextInput.trim().length >= MIN_FREE_TEXT_LENGTH));

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          clearDecisionPoint();
        }
      }}
    >
      <DialogContent data-testid="decision-dialog">
        <DialogHeader className="space-y-2">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <DialogTitle>{currentDecision.title}</DialogTitle>
              <DialogDescription>{currentDecision.description}</DialogDescription>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={clearDecisionPoint}
              aria-label="Skip decision"
              data-testid="decision-skip-header"
            >
              Skip decision
            </Button>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span
              className="rounded-full bg-muted px-2 py-1"
              data-testid="decision-turn-chip"
            >
              Turn {currentDecision.turnNumber}
            </span>
            <span
              className="rounded-full bg-muted px-2 py-1"
              data-testid="decision-type-chip"
            >
              {currentDecision.decisionType}
            </span>
            <span
              className="ml-auto flex items-center gap-1 rounded-full bg-muted px-2 py-1"
              data-testid="decision-countdown"
            >
              <Timer className="h-3 w-3" />
              {formatCountdown(remainingSeconds)}
            </span>
          </div>
        </DialogHeader>

        {currentDecision.narrativeContext && (
          <div
            className="rounded-md border border-border bg-muted/30 p-3 text-sm"
            data-testid="decision-narrative-context"
          >
            {currentDecision.narrativeContext}
          </div>
        )}

        {errorMessage && (
          <div
            className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
            data-testid="decision-error"
            role="alert"
          >
            <AlertTriangle className="h-4 w-4" />
            <span>{errorMessage}</span>
          </div>
        )}

        {negotiationResult && (
          <div
            className="rounded-md border border-border bg-muted/30 p-3 text-sm"
            data-testid="decision-negotiation"
            role="alert"
          >
            <div className="flex items-center gap-2 font-medium">
              <CheckCircle2 className="h-4 w-4 text-primary" />
              Adjustment Suggested
            </div>
            <p className="mt-1 text-muted-foreground">
              {negotiationResult.explanation}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button type="button" size="sm" data-testid="decision-accept-suggestion">
                Accept suggestion
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                data-testid="decision-keep-original"
              >
                Keep original
              </Button>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant={inputMode === 'options' ? 'default' : 'outline'}
            onClick={() => setInputMode('options')}
            data-testid="decision-mode-options"
          >
            Choose option
          </Button>
          <Button
            type="button"
            size="sm"
            variant={inputMode === 'freeText' ? 'default' : 'outline'}
            onClick={() => setInputMode('freeText')}
            data-testid="decision-mode-free-text"
          >
            Custom action
          </Button>
        </div>

        {inputMode === 'options' ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {currentDecision.options.map((option) => (
              <button
                key={option.optionId}
                type="button"
                className={cn(
                  'rounded-md border border-border bg-background p-3 text-left transition',
                  'hover:border-primary/50 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                  selectedOptionId === option.optionId &&
                    'border-primary/60 bg-primary/10'
                )}
                onClick={() => selectOption(option.optionId)}
                aria-pressed={selectedOptionId === option.optionId}
                data-testid="decision-option-card"
              >
                <div className="flex items-center gap-2 text-sm font-medium">
                  <span>{option.icon}</span>
                  <span data-testid="decision-option-label">{option.label}</span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {option.description}
                </p>
                {option.impactPreview && (
                  <p className="mt-2 text-xs text-primary/70">{option.impactPreview}</p>
                )}
              </button>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            <textarea
              className="min-h-[120px] w-full rounded-md border border-border bg-background p-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              placeholder="Describe what you want the characters to do..."
              value={freeTextInput}
              onChange={(event) => setFreeText(event.target.value)}
              data-testid="decision-free-text"
            />
            <div
              className="text-right text-xs text-muted-foreground"
              data-testid="decision-character-count"
            >
              {freeTextInput.length}/{MAX_FREE_TEXT_LENGTH}
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={clearDecisionPoint}
            data-testid="decision-skip-footer"
          >
            Skip (default)
          </Button>

          <Button
            type="button"
            size="sm"
            onClick={clearDecisionPoint}
            disabled={!confirmEnabled}
            data-testid="decision-confirm"
          >
            {submitting ? 'Submitting...' : 'Confirm'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
