// React import not required for JSX with new transform
import { Box } from '@mui/material';
import { useCharactersQuery } from '@/services/queries';
import AsyncStates from '@/components/common/AsyncStates';
import CharacterSelection from './CharacterSelection';

interface Props {
  selectedCharacters: string[];
  onSelectionChange: (characters: string[]) => void;
}

export default function CharacterSelectionContainer({ selectedCharacters, onSelectionChange }: Props) {
  const { data: characters, isLoading, error } = useCharactersQuery();

  return (
    <AsyncStates isLoading={isLoading} error={error} height={240}>
      <Box>
        <CharacterSelection
          characters={characters || []}
          selectedCharacters={selectedCharacters}
          onSelectionChange={onSelectionChange}
          isLoading={false}
        />
      </Box>
    </AsyncStates>
  );
}
