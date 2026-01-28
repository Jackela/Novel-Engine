/**
 * WeaverPage - Main story weaver page
 */
import { useCallback, useState } from 'react';
import { WeaverLayout } from '@/layouts/WeaverLayout';
import { WeaverCanvas } from './WeaverCanvas';
import { CharacterGenerationDialog } from './components/CharacterGenerationDialog';
import { WeaverToolbar } from './components/WeaverToolbar';
import { useWeaverAddNode, useWeaverStore, type WeaverNode } from './store/weaverStore';

export default function WeaverPage() {
  const addNode = useWeaverAddNode();
  const [generationOpen, setGenerationOpen] = useState(false);

  const handleAddCharacter = useCallback(() => {
    const newNode: WeaverNode = {
      id: `char-${Date.now()}`,
      type: 'character',
      position: { x: Math.random() * 400 + 100, y: Math.random() * 300 + 100 },
      data: {
        name: 'New Character',
        role: 'Supporting',
        traits: [],
        status: 'idle',
      },
    };
    addNode(newNode);
  }, [addNode]);

  const handleAddEvent = useCallback(() => {
    const newNode: WeaverNode = {
      id: `event-${Date.now()}`,
      type: 'event',
      position: { x: Math.random() * 400 + 100, y: Math.random() * 300 + 100 },
      data: {
        title: 'New Event',
        type: 'action',
        description: 'Describe what happens...',
        status: 'idle',
      },
    };
    addNode(newNode);
  }, [addNode]);

  const handleAddLocation = useCallback(() => {
    const newNode: WeaverNode = {
      id: `loc-${Date.now()}`,
      type: 'location',
      position: { x: Math.random() * 400 + 100, y: Math.random() * 300 + 100 },
      data: {
        name: 'New Location',
        type: 'other',
        description: 'Describe the place...',
        status: 'idle',
      },
    };
    addNode(newNode);
  }, [addNode]);

  const handleSave = useCallback(() => {
    const { nodes, edges } = useWeaverStore.getState();
    const payload = { nodes, edges };
    void payload;
  }, []);

  return (
    <WeaverLayout>
      <div className="flex min-h-screen flex-col">
        <WeaverToolbar
          onAddCharacter={handleAddCharacter}
          onAddEvent={handleAddEvent}
          onAddLocation={handleAddLocation}
          onGenerateCharacter={() => setGenerationOpen(true)}
          onSave={handleSave}
        />
        <div className="flex-1">
          <WeaverCanvas />
        </div>
      </div>
      <CharacterGenerationDialog
        open={generationOpen}
        onOpenChange={setGenerationOpen}
      />
    </WeaverLayout>
  );
}
