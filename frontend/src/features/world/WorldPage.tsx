/**
 * WorldPage - World management and visualization
 * Full-page view for world state management
 */
import { Suspense } from 'react';
import { Globe, MapPin, Clock, Users, Layers, Settings } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from '@/shared/components/ui/Card';
import { Button } from '@/shared/components/ui';
import { LoadingSpinner } from '@/shared/components/feedback';

function WorldMap() {
  return (
    <Card className="h-full" data-testid="world-map-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Globe className="h-5 w-5 text-primary" />
          World Map
        </CardTitle>
        <CardDescription>Interactive visualization of your narrative world</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex aspect-[16/9] items-center justify-center rounded-lg border border-dashed border-muted-foreground/30 bg-muted/30">
          <div className="text-center">
            <Globe className="mx-auto h-12 w-12 text-muted-foreground/50" />
            <p className="mt-2 text-sm text-muted-foreground">
              World map visualization coming soon
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function LocationsList() {
  const locations = [
    { name: "Dragon's Keep", type: 'Fortress', active: true },
    { name: 'Merchant Quarter', type: 'District', active: true },
    { name: 'Forest Path', type: 'Road', active: false },
    { name: 'Crystal Caverns', type: 'Dungeon', active: false },
  ];

  return (
    <Card data-testid="locations-list">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MapPin className="h-5 w-5 text-primary" />
          Locations
        </CardTitle>
        <CardDescription>All defined locations in your world</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {locations.map((location) => (
            <div
              key={location.name}
              className="flex cursor-pointer items-center justify-between rounded-lg p-3 transition-colors hover:bg-muted/50"
            >
              <div className="flex items-center gap-3">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">{location.name}</p>
                  <p className="text-xs text-muted-foreground">{location.type}</p>
                </div>
              </div>
              {location.active && (
                <span className="rounded-full bg-green-500/10 px-2 py-1 text-xs text-green-600">
                  Active
                </span>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function WorldClock() {
  return (
    <Card data-testid="world-clock">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-primary" />
          World Time
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="text-center">
            <p className="text-3xl font-bold">Day 15</p>
            <p className="text-lg text-muted-foreground">Year 1042</p>
          </div>
          <div className="flex justify-center gap-2">
            <Button variant="outline" size="sm">
              Advance Day
            </Button>
            <Button variant="outline" size="sm">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function WorldStats() {
  const stats = [
    { label: 'Characters', value: 12, icon: Users },
    { label: 'Locations', value: 8, icon: MapPin },
    { label: 'Factions', value: 3, icon: Layers },
  ];

  return (
    <Card data-testid="world-stats">
      <CardHeader>
        <CardTitle>World Statistics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <stat.icon className="mx-auto h-6 w-6 text-muted-foreground" />
              <p className="mt-2 text-2xl font-bold">{stat.value}</p>
              <p className="text-xs text-muted-foreground">{stat.label}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function WorldPage() {
  return (
    <Suspense fallback={<LoadingSpinner fullScreen text="Loading world..." />}>
      <div className="space-y-6" data-testid="world-page">
        {/* Page header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">World Management</h1>
            <p className="text-muted-foreground">
              Build and manage your narrative world
            </p>
          </div>
          <Button>
            <Globe className="mr-2 h-4 w-4" />
            Generate World
          </Button>
        </div>

        {/* Main content grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Map takes 2 columns */}
          <div className="lg:col-span-2">
            <WorldMap />
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <WorldClock />
            <WorldStats />
          </div>
        </div>

        {/* Locations list */}
        <LocationsList />
      </div>
    </Suspense>
  );
}
