/**
 * TimelinePanel - Narrative timeline
 * Shows the sequence of events in the story
 */
import { Clock, ChevronRight } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/components/ui/Card';

const events = [
  { id: 1, time: '09:00', title: 'Meeting at the tavern', status: 'completed' },
  { id: 2, time: '12:00', title: 'Journey begins', status: 'completed' },
  { id: 3, time: '15:00', title: 'Ambush in the forest', status: 'active' },
  { id: 4, time: '18:00', title: 'Arrival at the castle', status: 'pending' },
];

export default function TimelinePanel() {
  return (
    <Card className="h-full" data-testid="timeline-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-primary" />
          Narrative Timeline
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute bottom-0 left-4 top-0 w-px bg-border" />

          {/* Events */}
          <div className="space-y-4">
            {events.map((event) => (
              <div key={event.id} className="relative flex items-start gap-4 pl-8">
                {/* Dot */}
                <div
                  className={`absolute left-3 mt-2 h-2 w-2 -translate-x-1/2 rounded-full ${
                    event.status === 'completed'
                      ? 'bg-primary'
                      : event.status === 'active'
                        ? 'animate-pulse bg-warning'
                        : 'bg-muted-foreground/30'
                  }`}
                />

                {/* Content */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">{event.time}</span>
                    {event.status === 'active' && (
                      <span className="rounded-full bg-warning/20 px-2 py-0.5 text-xs text-warning">
                        Active
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-medium">{event.title}</p>
                </div>

                {/* Arrow */}
                <ChevronRight className="h-4 w-4 text-muted-foreground/50" />
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
