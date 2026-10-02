import { type ReactNode, useRef } from "react";

import type { Volume } from "@/app/types/studio";

import {
  type NavigatorVolumeCommands,
  StudioNavigatorVolumeHeader,
} from "./StudioNavigatorVolumeHeader";

interface StudioNavigatorVolumeListProps {
  volumes: Volume[];
  /** Absent renders titles without management controls. */
  commands: NavigatorVolumeCommands | null;
  isMutationBusy: boolean;
  /** The chapter rows of one volume, rendered under its header. */
  renderRows: (volume: Volume) => ReactNode;
}

/**
 * The chapter group's volume reading order: one header per volume over its
 * rows. The map keeps a focus fallback so a deleted volume hands focus to its
 * surviving neighbor's first control instead of dropping it to the body.
 */
export function StudioNavigatorVolumeList({
  volumes,
  commands,
  isMutationBusy,
  renderRows,
}: StudioNavigatorVolumeListProps) {
  const roots = useRef(new Map<string, HTMLDivElement>());

  /** The surviving neighbor of a removed volume, mirroring row deletion. */
  const neighborFallback = (volumeId: string): HTMLElement | null => {
    const index = volumes.findIndex((volume) => volume.id === volumeId);
    if (index === -1) return null;
    const remaining = volumes.filter((volume) => volume.id !== volumeId);
    const neighbor = remaining[index] ?? remaining[index - 1] ?? null;
    if (neighbor === null) return null;
    return (
      roots.current.get(neighbor.id)?.querySelector<HTMLElement>("button:not([disabled])") ?? null
    );
  };

  return volumes.map((volume, index) => (
    <div
      className="volume-group"
      key={volume.id}
      ref={(node) => {
        if (node) roots.current.set(volume.id, node);
        else roots.current.delete(volume.id);
      }}
    >
      <StudioNavigatorVolumeHeader
        commands={commands}
        focusFallback={() => neighborFallback(volume.id)}
        index={index}
        isMutationBusy={isMutationBusy}
        volume={volume}
        volumeCount={volumes.length}
      />
      {renderRows(volume)}
    </div>
  ));
}
