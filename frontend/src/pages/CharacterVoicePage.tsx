/**
 * CharacterVoicePage - Dialogue Testing Playground
 *
 * Route: /world/characters/:characterId/voice
 *
 * A dedicated page for testing a character's voice and dialogue patterns.
 * Uses the AI-powered dialogue generation to let users interact with
 * characters and hear how they would naturally speak.
 */
import { useParams, Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/Card';
import { Button } from '@/shared/components/ui/Button';
import { Skeleton } from '@/shared/components/ui/Skeleton';
import { api } from '@/lib/api';
import DialogueTester from '@/features/characters/components/DialogueTester';
import type { CharacterDetail } from '@/types/schemas';
import { CharacterDetailSchema } from '@/types/schemas';

/**
 * Fetch character details from the API.
 */
async function fetchCharacter(characterId: string): Promise<CharacterDetail> {
  const data = await api.get<unknown>(`/characters/${characterId}`);
  return CharacterDetailSchema.parse(data);
}

export default function CharacterVoicePage() {
  const { characterId } = useParams({ from: '/protected/world/characters/$characterId/voice' });

  const {
    data: character,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['character', characterId],
    queryFn: () => fetchCharacter(characterId),
    staleTime: 30000,
  });

  if (isLoading) {
    return (
      <div className="container mx-auto p-6 max-w-4xl">
        <div className="mb-4">
          <Skeleton className="h-8 w-48" />
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-64" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-[400px] w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !character) {
    return (
      <div className="container mx-auto p-6 max-w-4xl">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">Character Not Found</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              Could not load character with ID: {characterId}
            </p>
            <Link to="/characters">
              <Button variant="outline">Back to Characters</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      {/* Breadcrumb navigation */}
      <nav className="mb-4 text-sm text-muted-foreground">
        <ol className="flex items-center gap-2">
          <li>
            <Link to="/characters" className="hover:text-foreground transition-colors">
              Characters
            </Link>
          </li>
          <li>/</li>
          <li className="font-medium text-foreground">{character.character_name}</li>
          <li>/</li>
          <li className="font-medium text-foreground">Voice</li>
        </ol>
      </nav>

      {/* Main content card */}
      <Card className="overflow-hidden">
        <DialogueTester
          characterId={characterId}
          characterName={character.character_name}
          characterData={character}
        />
      </Card>

      {/* Character psychology summary if available */}
      {character.psychology && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle className="text-sm">Psychology Influences Speech</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-5 gap-2 text-xs">
              <div className="text-center">
                <div className="font-medium">Openness</div>
                <div className="text-muted-foreground">{character.psychology.openness}</div>
              </div>
              <div className="text-center">
                <div className="font-medium">Conscientiousness</div>
                <div className="text-muted-foreground">{character.psychology.conscientiousness}</div>
              </div>
              <div className="text-center">
                <div className="font-medium">Extraversion</div>
                <div className="text-muted-foreground">{character.psychology.extraversion}</div>
              </div>
              <div className="text-center">
                <div className="font-medium">Agreeableness</div>
                <div className="text-muted-foreground">{character.psychology.agreeableness}</div>
              </div>
              <div className="text-center">
                <div className="font-medium">Neuroticism</div>
                <div className="text-muted-foreground">{character.psychology.neuroticism}</div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              The character&apos;s Big Five personality traits influence how they speak. High extraversion leads
              to more enthusiastic speech, while high neuroticism may add hedging language.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
