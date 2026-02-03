/**
 * Weaver node types
 */
export {
  CharacterNode,
  type CharacterNodeData,
  type CharacterNodeType,
} from './CharacterNode';
export { EventNode, type EventNodeData, type EventNodeType } from './EventNode';
export { FactionNode, type FactionNodeData, type FactionNodeType } from './FactionNode';
export {
  LocationNode,
  type LocationNodeData,
  type LocationNodeType,
} from './LocationNode';
export { SceneNode, type SceneNodeType } from './SceneNode';
export { WorldNode, type WorldNodeData, type WorldNodeType } from './WorldNode';

import { CharacterNode } from './CharacterNode';
import { EventNode } from './EventNode';
import { FactionNode } from './FactionNode';
import { LocationNode } from './LocationNode';
import { SceneNode } from './SceneNode';
import { WorldNode } from './WorldNode';

export const nodeTypes = {
  character: CharacterNode,
  event: EventNode,
  faction: FactionNode,
  location: LocationNode,
  scene: SceneNode,
  world: WorldNode,
};
