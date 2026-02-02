/**
 * WeaverPage - Main story weaver page
 */
import { useCallback, useState } from 'react';
import { WeaverLayout } from '@/layouts/WeaverLayout';
import { WeaverCanvas } from './WeaverCanvas';
import { CharacterGenerationDialog } from './components/CharacterGenerationDialog';
import { SceneGenerationDialog } from './components/SceneGenerationDialog';
import { WeaverToolbar } from './components/WeaverToolbar';
import {
  useWeaverAddNode,
  useWeaverStore,
  useSelectedCharacterNode,
  type WeaverNode,
} from './store/weaverStore';
import type { CharacterNodeData } from './components/nodes/CharacterNode';

export default function WeaverPage() {
  const addNode = useWeaverAddNode();
  const [generationOpen, setGenerationOpen] = useState(false);
  const [sceneGenerationOpen, setSceneGenerationOpen] = useState(false);
  const selectedCharacterNode = useSelectedCharacterNode();

  const selectedCharacterName = selectedCharacterNode
    ? (selectedCharacterNode.data as CharacterNodeData).name
    : undefined;

  const getNextNodePosition = useCallback(() => {
    const { nodes } = useWeaverStore.getState();
    const index = nodes.length;
    const columns = 3;
    const col = index % columns;
    const row = Math.floor(index / columns);
    return { x: 160 + col * 320, y: 120 + row * 240 };
  }, []);

  const handleAddCharacter = useCallback(() => {
    const newNode: WeaverNode = {
      id: `char-${Date.now()}`,
      type: 'character',
      position: getNextNodePosition(),
      data: {
        name: 'New Character',
        role: 'Supporting',
        traits: [],
        status: 'idle',
      },
    };
    addNode(newNode);
  }, [addNode, getNextNodePosition]);

  const handleAddEvent = useCallback(() => {
    const newNode: WeaverNode = {
      id: `event-${Date.now()}`,
      type: 'event',
      position: getNextNodePosition(),
      data: {
        title: 'New Event',
        type: 'action',
        description: 'Describe what happens...',
        status: 'idle',
      },
    };
    addNode(newNode);
  }, [addNode, getNextNodePosition]);

  const handleAddLocation = useCallback(() => {
    const newNode: WeaverNode = {
      id: `loc-${Date.now()}`,
      type: 'location',
      position: getNextNodePosition(),
      data: {
        name: 'New Location',
        type: 'other',
        description: 'Describe the place...',
        status: 'idle',
      },
    };
    addNode(newNode);
  }, [addNode, getNextNodePosition]);

  const handleSave = useCallback(() => {
    const { nodes, edges } = useWeaverStore.getState();
    const payload = { nodes, edges };
    void payload;
  }, []);

  return (
    <WeaverLayout>
      <div className="flex h-screen flex-col">
        <WeaverToolbar
          onAddCharacter={handleAddCharacter}
          onAddEvent={handleAddEvent}
          onAddLocation={handleAddLocation}
          onGenerateCharacter={() => setGenerationOpen(true)}
          onGenerateScene={() => setSceneGenerationOpen(true)}
          onSave={handleSave}
          hasSelectedCharacter={selectedCharacterNode !== null}
        />
        <div className="relative flex-1">
          <div className="absolute inset-0">
            <WeaverCanvas />
          </div>
        </div>
      </div>
      <CharacterGenerationDialog
        open={generationOpen}
        onOpenChange={setGenerationOpen}
      />
      <SceneGenerationDialog
        open={sceneGenerationOpen}
        onOpenChange={setSceneGenerationOpen}
        selectedCharacterNodeId={selectedCharacterNode?.id ?? null}
        selectedCharacterName={selectedCharacterName}
      />
    </WeaverLayout>
  );
}
