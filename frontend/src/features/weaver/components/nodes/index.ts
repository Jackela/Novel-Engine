/**
 * Weaver node types
 */
export {
  CharacterNode,
  type CharacterNodeData,
  type CharacterNodeType,
} from './CharacterNode';
export { EventNode, type EventNodeData, type EventNodeType } from './EventNode';
export {
  LocationNode,
  type LocationNodeData,
  type LocationNodeType,
} from './LocationNode';

import { CharacterNode } from './CharacterNode';
import { EventNode } from './EventNode';
import { LocationNode } from './LocationNode';

export const nodeTypes = {
  character: CharacterNode,
  event: EventNode,
  location: LocationNode,
};
