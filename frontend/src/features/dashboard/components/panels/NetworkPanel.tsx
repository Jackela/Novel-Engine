/**
 * NetworkPanel - Character relationship network
 * Visualizes connections between characters
 */
import { Users, Link2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/components/ui/Card';

export default function NetworkPanel() {
  return (
    <Card className="h-full" data-testid="network-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          Character Network
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Network stats */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-muted/50 text-center">
              <p className="text-2xl font-bold">12</p>
              <p className="text-xs text-muted-foreground">Characters</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50 text-center">
              <p className="text-2xl font-bold">28</p>
              <p className="text-xs text-muted-foreground">Relationships</p>
            </div>
          </div>

          {/* Recent interactions */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Recent Interactions</h4>
            <div className="space-y-1">
              {[
                { a: 'Aldric', b: 'Elena', type: 'Alliance' },
                { a: 'Marcus', b: 'Shadow', type: 'Conflict' },
              ].map((interaction, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 p-2 rounded-md bg-muted/30"
                >
                  <span className="text-sm">{interaction.a}</span>
                  <Link2 className="h-3 w-3 text-muted-foreground" />
                  <span className="text-sm">{interaction.b}</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {interaction.type}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Network visualization placeholder */}
          <div className="aspect-square rounded-lg bg-muted/30 flex items-center justify-center border border-dashed border-muted-foreground/30">
            <p className="text-sm text-muted-foreground">Network Graph</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
