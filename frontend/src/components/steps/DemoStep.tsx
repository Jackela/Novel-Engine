import React, { useState } from 'react';
import './DemoStep.css';
import { SAMPLE_STORIES } from '../../data/sampleStories';

type Preview = { narrator: string; characters: Record<string, { dialogue: string; action: string }> };
type SampleStory = {
  id: string;
  title: string;
  description: string;
  genre: string;
  estimatedLength: string;
  complexity: string;
  opening: { setting: string };
  characters: Array<{ name: string; profession: string }>;
  sampleTurns: Preview[];
};

export type GeneratedStory = SampleStory & { generatedAt: string; mode: 'ai_enhanced' | 'algorithmic'; preview: Preview };

interface DemoStepProps {
  apiUrl?: () => string;
  hasApiKey: boolean;
  onStoryGenerated: (story: GeneratedStory) => void;
  className?: string;
}

export default function DemoStep({ apiUrl: _apiUrl, hasApiKey, onStoryGenerated, className = '' }: DemoStepProps) {
  const [selectedStory, setSelectedStory] = useState<SampleStory | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedStory, setGeneratedStory] = useState<GeneratedStory | null>(null);

  const sampleStories = Object.values(SAMPLE_STORIES) as SampleStory[];

  const handleStorySelection = (story: SampleStory) => {
    setSelectedStory(story);
  };

  const handleGenerateStory = async () => {
    if (!selectedStory) return;
    setIsGenerating(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      const story: GeneratedStory = {
        ...selectedStory,
        generatedAt: new Date().toISOString(),
        mode: hasApiKey ? 'ai_enhanced' : 'algorithmic',
        preview: selectedStory.sampleTurns[0] as Preview,
      };
      setGeneratedStory(story);
      onStoryGenerated(story);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className={`demo-step ${className}`}>
      {!selectedStory && (
        <div className="story-selection">
          <h3>Choose a Story to Experience</h3>
          <p>Select one of our sample stories to see StoryForge AI in action:</p>
          <div className="story-grid">
            {sampleStories.map((story) => (
              <div key={story.id} className="story-card" onClick={() => handleStorySelection(story)}>
                <div className="story-header">
                  <h4>{story.title}</h4>
                  <span className="story-genre">{story.genre}</span>
                </div>
                <p className="story-description">{story.description}</p>
                <div className="story-meta">
                  <span className="story-length">{story.estimatedLength}</span>
                  <span className="story-complexity">{story.complexity}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedStory && !generatedStory && (
        <div className="story-generation">
          <div className="selected-story">
            <h3>{selectedStory.title}</h3>
            <p>{selectedStory.description}</p>
            <div className="story-preview">
              <h4>Story Setting</h4>
              <p>{selectedStory.opening.setting}</p>
              <h4>Characters</h4>
              <div className="character-list">
                {selectedStory.characters.map((character, index) => (
                  <div key={index} className="character-card">
                    <strong>{character.name}</strong>
                    <span>{character.profession}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="generation-controls">
              <button onClick={handleGenerateStory} className="btn-primary" disabled={isGenerating}>
                {isGenerating ? (
                  <>
                    <span className="spinner" />
                    Generating Story...
                  </>
                ) : (
                  'Generate Interactive Story'
                )}
              </button>
              <button onClick={() => setSelectedStory(null)} className="btn-secondary" disabled={isGenerating}>
                Back to Stories
              </button>
            </div>
          </div>
        </div>
      )}

      {generatedStory && (
        <div className="story-preview-section">
          <div className="preview-card">
            <h3>Preview</h3>
            <div className="dialogue-block">
              <p>
                <strong>Narrator:</strong> {generatedStory.preview.narrator}
              </p>
              {Object.entries(generatedStory.preview.characters).map(([name, character]) => (
                <div key={name} className="character-turn">
                  <p>
                    <strong>{name}:</strong> "{character.dialogue}"
                  </p>
                  <p>
                    <em>{character.action}</em>
                  </p>
                </div>
              ))}
            </div>
          </div>
          <div className="demo-actions">
            <button
              onClick={() => {
                setSelectedStory(null);
                setGeneratedStory(null);
              }}
              className="btn-secondary"
            >
              Try Another Story
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
