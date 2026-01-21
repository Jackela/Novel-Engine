/**
 * WeaverPage - Main story weaver page
 */
import { useCallback } from 'react';
import { WeaverLayout } from '@/layouts/WeaverLayout';
import { WeaverCanvas } from './WeaverCanvas';
import { WeaverToolbar } from './components/WeaverToolbar';
import type { Node } from '@xyflow/react';
import { useWeaverAddNode, useWeaverStore } from './store/weaverStore';

export default function WeaverPage() {
  const addNode = useWeaverAddNode();

  const handleAddCharacter = useCallback(() => {
    const newNode: Node = {
      id: `char-${Date.now()}`,
      type: 'character',
      position: { x: Math.random() * 400 + 100, y: Math.random() * 300 + 100 },
      data: {
        name: 'New Character',
        role: 'Supporting',
        traits: [],
      },
    };
    addNode(newNode);
  }, [addNode]);

  const handleAddEvent = useCallback(() => {
    const newNode: Node = {
      id: `event-${Date.now()}`,
      type: 'event',
      position: { x: Math.random() * 400 + 100, y: Math.random() * 300 + 100 },
      data: {
        title: 'New Event',
        type: 'action',
        description: 'Describe what happens...',
      },
    };
    addNode(newNode);
  }, [addNode]);

  const handleAddLocation = useCallback(() => {
    const newNode: Node = {
      id: `loc-${Date.now()}`,
      type: 'location',
      position: { x: Math.random() * 400 + 100, y: Math.random() * 300 + 100 },
      data: {
        name: 'New Location',
        type: 'other',
        description: 'Describe the place...',
      },
    };
    addNode(newNode);
  }, [addNode]);

  const handleSave = useCallback(() => {
    const { nodes, edges } = useWeaverStore.getState();
    // TODO: Implement save to backend
    console.log('Saving story...', { nodes, edges });
  }, []);

  return (
    <WeaverLayout>
      <div className="flex min-h-screen flex-col">
        <WeaverToolbar
          onAddCharacter={handleAddCharacter}
          onAddEvent={handleAddEvent}
          onAddLocation={handleAddLocation}
          onSave={handleSave}
        />
        <div className="flex-1">
          <WeaverCanvas />
        </div>
      </div>
    </WeaverLayout>
  );
}
