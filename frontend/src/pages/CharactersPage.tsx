import React from 'react';
import { Container } from '@mui/material';
import CharacterStudio from '../features/characters';

const CharactersPage: React.FC = () => {
  return (
    <Container maxWidth="xl" sx={{ py: { xs: 3, md: 4 } }}>
      <CharacterStudio />
    </Container>
  );
};

export default CharactersPage;
