/**
 * WeaverToolbar - Toolbar for weaver actions
 */
import { Users, Sparkles, MapPin, Zap, Save, Undo, Redo } from 'lucide-react';
import { Button } from '@/shared/components/ui';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/shared/components/ui/tooltip';

interface WeaverToolbarProps {
  onAddCharacter?: () => void;
  onAddEvent?: () => void;
  onAddLocation?: () => void;
  onSave?: () => void;
  onUndo?: () => void;
  onRedo?: () => void;
  canUndo?: boolean;
  canRedo?: boolean;
}

export function WeaverToolbar({
  onAddCharacter,
  onAddEvent,
  onAddLocation,
  onSave,
  onUndo,
  onRedo,
  canUndo = false,
  canRedo = false,
}: WeaverToolbarProps) {
  return (
    <header className="flex items-center justify-between border-b bg-background px-6 py-3">
      <div className="flex items-center gap-3">
        <Sparkles className="h-6 w-6 text-primary" />
        <h1 className="text-xl font-semibold">Story Weaver</h1>
      </div>

      <div className="flex items-center gap-2">
        {/* Node Creation */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="outline" size="sm" onClick={onAddCharacter}>
                <Users className="mr-2 h-4 w-4" />
                Character
              </Button>
            </TooltipTrigger>
            <TooltipContent>Add a character node</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="outline" size="sm" onClick={onAddEvent}>
                <Zap className="mr-2 h-4 w-4" />
                Event
              </Button>
            </TooltipTrigger>
            <TooltipContent>Add an event node</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="outline" size="sm" onClick={onAddLocation}>
                <MapPin className="mr-2 h-4 w-4" />
                Location
              </Button>
            </TooltipTrigger>
            <TooltipContent>Add a location node</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <div className="w-px h-6 bg-border mx-2" />

        {/* History */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={onUndo}
                disabled={!canUndo}
              >
                <Undo className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Undo</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={onRedo}
                disabled={!canRedo}
              >
                <Redo className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Redo</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <div className="w-px h-6 bg-border mx-2" />

        {/* Save */}
        <Button size="sm" onClick={onSave}>
          <Save className="mr-2 h-4 w-4" />
          Save
        </Button>
      </div>
    </header>
  );
}
