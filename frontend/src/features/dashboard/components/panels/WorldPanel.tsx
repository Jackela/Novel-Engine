/**
 * WorldPanel - World state visualization
 * Shows the current state of the narrative world
 */
import { Globe, MapPin, Clock } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/components/ui/Card';

export default function WorldPanel() {
  return (
    <Card className="h-full" data-testid="world-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Globe className="h-5 w-5 text-primary" />
          World State
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Time indicator */}
          <div className="flex items-center gap-3 rounded-lg bg-muted/50 p-3">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">Current Time</p>
              <p className="text-xs text-muted-foreground">Day 15, Year 1042</p>
            </div>
          </div>

          {/* Active locations */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Active Locations</h4>
            <div className="space-y-1">
              {["Dragon's Keep", 'Merchant Quarter', 'Forest Path'].map((location) => (
                <div
                  key={location}
                  className="flex cursor-pointer items-center gap-2 rounded-md p-2 transition-colors hover:bg-muted/50"
                >
                  <MapPin className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">{location}</span>
                </div>
              ))}
            </div>
          </div>

          {/* World map placeholder */}
          <div className="flex aspect-video items-center justify-center rounded-lg border border-dashed border-muted-foreground/30 bg-muted/30">
            <p className="text-sm text-muted-foreground">World Map</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
