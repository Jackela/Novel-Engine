/**
 * WeaverToolbar - Toolbar for weaver actions
 */
import { Users, Sparkles, MapPin, Zap, Save, Undo, Redo, Film } from 'lucide-react';
import { Button } from '@/shared/components/ui';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/shared/components/ui/tooltip';

interface WeaverToolbarProps {
  onAddCharacter?: (() => void) | undefined;
  onAddEvent?: (() => void) | undefined;
  onAddLocation?: (() => void) | undefined;
  onGenerateCharacter?: (() => void) | undefined;
  onGenerateScene?: (() => void) | undefined;
  onSave?: (() => void) | undefined;
  onUndo?: (() => void) | undefined;
  onRedo?: (() => void) | undefined;
  canUndo?: boolean;
  canRedo?: boolean;
  hasSelectedCharacter?: boolean;
}

export function WeaverToolbar({
  onAddCharacter,
  onAddEvent,
  onAddLocation,
  onGenerateCharacter,
  onGenerateScene,
  onSave,
  onUndo,
  onRedo,
  canUndo = false,
  canRedo = false,
  hasSelectedCharacter = false,
}: WeaverToolbarProps) {
  return (
    <header className="flex items-center justify-between border-b bg-background px-6 py-3">
      <div className="flex items-center gap-3">
        <Sparkles className="h-6 w-6 text-primary" />
        <h1 className="text-xl font-semibold">Story Weaver</h1>
      </div>

      <div className="flex items-center gap-2">
        <WeaverNodeControls
          onAddCharacter={onAddCharacter}
          onAddEvent={onAddEvent}
          onAddLocation={onAddLocation}
        />
        <TooltipButton
          label="Generate"
          tooltip="Generate a character node"
          onClick={onGenerateCharacter}
          icon={<Sparkles className="mr-2 h-4 w-4" />}
        />
        <TooltipButton
          label="Generate Scene"
          tooltip="Generate a scene from selected character"
          onClick={onGenerateScene}
          icon={<Film className="mr-2 h-4 w-4" />}
          disabled={!hasSelectedCharacter}
        />
        <Divider />
        <WeaverHistoryControls
          onUndo={onUndo}
          onRedo={onRedo}
          canUndo={canUndo}
          canRedo={canRedo}
        />
        <Divider />
        <Button size="sm" onClick={onSave}>
          <Save className="mr-2 h-4 w-4" />
          Save
        </Button>
      </div>
    </header>
  );
}

type TooltipButtonProps = {
  label: string;
  tooltip: string;
  onClick?: (() => void) | undefined;
  icon: JSX.Element;
  variant?: 'outline' | 'ghost';
  size?: 'sm' | 'icon';
  disabled?: boolean;
};

function TooltipButton({
  label,
  tooltip,
  onClick,
  icon,
  variant = 'outline',
  size = 'sm',
  disabled,
}: TooltipButtonProps) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={variant}
            size={size}
            onClick={onClick}
            disabled={disabled}
            aria-label={label || tooltip}
          >
            {icon}
            {label && size !== 'icon' ? label : null}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{tooltip}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function Divider() {
  return <div className="mx-2 h-6 w-px bg-border" />;
}

function WeaverNodeControls({
  onAddCharacter,
  onAddEvent,
  onAddLocation,
}: Pick<WeaverToolbarProps, 'onAddCharacter' | 'onAddEvent' | 'onAddLocation'>) {
  return (
    <>
      <TooltipButton
        label="Character"
        tooltip="Add a character node"
        onClick={onAddCharacter}
        icon={<Users className="mr-2 h-4 w-4" />}
      />
      <TooltipButton
        label="Event"
        tooltip="Add an event node"
        onClick={onAddEvent}
        icon={<Zap className="mr-2 h-4 w-4" />}
      />
      <TooltipButton
        label="Location"
        tooltip="Add a location node"
        onClick={onAddLocation}
        icon={<MapPin className="mr-2 h-4 w-4" />}
      />
    </>
  );
}

function WeaverHistoryControls({
  onUndo,
  onRedo,
  canUndo,
  canRedo,
}: Pick<WeaverToolbarProps, 'onUndo' | 'onRedo' | 'canUndo' | 'canRedo'>) {
  return (
    <>
      <TooltipButton
        label=""
        tooltip="Undo"
        onClick={onUndo}
        icon={<Undo className="h-4 w-4" />}
        variant="ghost"
        size="icon"
        disabled={!canUndo}
      />
      <TooltipButton
        label=""
        tooltip="Redo"
        onClick={onRedo}
        icon={<Redo className="h-4 w-4" />}
        variant="ghost"
        size="icon"
        disabled={!canRedo}
      />
    </>
  );
}
