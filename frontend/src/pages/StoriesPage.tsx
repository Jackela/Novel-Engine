import React from 'react';
import { Container } from '@mui/material';
import StoryLibrary from '@/features/stories/StoryLibrary';

const StoriesPage: React.FC = () => {
  return (
    <Container maxWidth="xl" sx={{ py: { xs: 3, md: 4 } }}>
      <StoryLibrary />
    </Container>
  );
};

export default StoriesPage;
