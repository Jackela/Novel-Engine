/**
 * DecisionDialog - Modal for user decision input
 */
import { useState } from 'react';
import { AlertCircle, Clock, CheckCircle2, ArrowRight } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/shared/components/ui/dialog';
import { Button, Badge, Card, CardContent } from '@/shared/components/ui';
import { cn } from '@/shared/lib/utils';
import type { DecisionPoint, DecisionOption } from '@/shared/types/orchestration';

interface DecisionDialogProps {
  decision: DecisionPoint | null;
  open: boolean;
  onClose: () => void;
  onDecide: (optionId: string) => void;
  isLoading?: boolean;
}

const urgencyColors = {
  low: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  high: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
};

const typeLabels: Record<DecisionPoint['type'], string> = {
  narrative_branch: 'Narrative Branch',
  conflict_resolution: 'Conflict Resolution',
  character_action: 'Character Action',
  world_event: 'World Event',
};

export function DecisionDialog({
  decision,
  open,
  onClose,
  onDecide,
  isLoading = false,
}: DecisionDialogProps) {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);

  if (!decision) return null;

  const handleConfirm = () => {
    if (selectedOption) {
      onDecide(selectedOption);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="h-5 w-5 text-primary" />
            <Badge variant="outline">{typeLabels[decision.type]}</Badge>
            <Badge className={cn('text-xs', urgencyColors[decision.urgency])}>
              {decision.urgency} urgency
            </Badge>
            {decision.expiresAt && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground ml-auto">
                <Clock className="h-3 w-3" />
                Expires soon
              </span>
            )}
          </div>
          <DialogTitle>{decision.prompt}</DialogTitle>
          <DialogDescription className="mt-2">{decision.context}</DialogDescription>
        </DialogHeader>

        {/* Options */}
        <div className="space-y-3 my-4">
          {decision.options.map((option) => (
            <Card
              key={option.id}
              className={cn(
                'cursor-pointer transition-all',
                selectedOption === option.id
                  ? 'border-primary ring-2 ring-primary/20'
                  : 'hover:border-muted-foreground/50'
              )}
              onClick={() => setSelectedOption(option.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      'w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5',
                      selectedOption === option.id
                        ? 'border-primary bg-primary'
                        : 'border-muted-foreground'
                    )}
                  >
                    {selectedOption === option.id && (
                      <CheckCircle2 className="h-3 w-3 text-primary-foreground" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium">{option.label}</h4>
                      {option.recommended && (
                        <Badge variant="secondary" className="text-xs">
                          Recommended
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">{option.description}</p>
                    {option.consequences && (
                      <div className="flex items-center gap-1 mt-2 text-xs text-muted-foreground">
                        <ArrowRight className="h-3 w-3" />
                        <span>{option.consequences}</span>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={!selectedOption || isLoading}>
            {isLoading ? 'Processing...' : 'Confirm Decision'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
