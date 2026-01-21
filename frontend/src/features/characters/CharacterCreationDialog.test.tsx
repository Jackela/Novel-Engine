import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import CharacterCreationDialog from './CharacterCreationDialog';

const mockCreate = {
  mutateAsync: vi.fn().mockResolvedValue(undefined),
  isPending: false,
};

const mockUpdate = {
  mutateAsync: vi.fn().mockResolvedValue(undefined),
  isPending: false,
};

vi.mock('./api/characterApi', () => ({
  useCreateCharacter: () => mockCreate,
  useUpdateCharacter: () => mockUpdate,
}));

describe('CharacterCreationDialog', () => {
  const mockProps = {
    open: true,
    onClose: vi.fn(),
    onCharacterCreated: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the dialog when open', () => {
    render(<CharacterCreationDialog {...mockProps} />);

    expect(screen.getByText('Create New Character')).toBeInTheDocument();
    expect(screen.getByLabelText('Agent ID')).toBeInTheDocument();
    expect(screen.getByLabelText('Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Background Summary')).toBeInTheDocument();
  });

  it('validates required fields', async () => {
    render(<CharacterCreationDialog {...mockProps} />);

    const submitButton = screen.getByRole('button', { name: /create character/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Agent ID is required')).toBeInTheDocument();
      expect(screen.getByText('Name must be at least 2 characters')).toBeInTheDocument();
    });
  });

  it('submits valid form data', async () => {
    render(<CharacterCreationDialog {...mockProps} />);

    fireEvent.change(screen.getByLabelText('Agent ID'), { target: { value: 'agent-001' } });
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Test Agent' } });

    const submitButton = screen.getByRole('button', { name: /create character/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockCreate.mutateAsync).toHaveBeenCalled();
    });
  });

  it('closes dialog when cancel is clicked', () => {
    render(<CharacterCreationDialog {...mockProps} />);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    expect(mockProps.onClose).toHaveBeenCalledTimes(1);
  });
});
