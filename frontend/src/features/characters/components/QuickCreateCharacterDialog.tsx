/**
 * QuickCreateCharacterDialog - Minimal dialog for quick character creation from editor.
 *
 * Why: When writers are in creative flow, they don't want to leave the editor
 * to create a new character. This dialog provides only essential fields (name,
 * background) to minimize interruption. Triggered by typing @NewName in the editor.
 */
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { UserPlus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useCreateCharacter } from '../api/characterApi';

/**
 * Schema for quick character creation - minimal fields only.
 * Note: background_summary is required in the form but can be empty string.
 */
const QuickCreateSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters').max(100),
  background_summary: z.string().max(500),
});

type QuickCreateFormValues = z.infer<typeof QuickCreateSchema>;

interface QuickCreateCharacterDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Called when the dialog should close */
  onClose: () => void;
  /** Initial name extracted from @mention (e.g., "NewName" from "@NewName") */
  initialName?: string;
  /**
   * Called when character is created with the new character's ID and name.
   * The parent can use this to insert a mention of the newly created character.
   */
  onCharacterCreated: (characterId: string, characterName: string) => void;
}

/**
 * Convert a name to a valid agent ID format (lowercase, hyphenated).
 */
function nameToAgentId(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/**
 * A minimal character creation dialog for use in the editor.
 *
 * Why: Provides a low-friction way to create characters without leaving
 * the writing context. Only asks for name and optional background,
 * generating sensible defaults for other fields.
 */
export function QuickCreateCharacterDialog({
  open,
  onClose,
  initialName = '',
  onCharacterCreated,
}: QuickCreateCharacterDialogProps) {
  const createCharacter = useCreateCharacter();

  const form = useForm<QuickCreateFormValues>({
    resolver: zodResolver(QuickCreateSchema),
    defaultValues: {
      name: initialName,
      background_summary: '',
    },
    mode: 'onBlur',
  });

  // Reset form when dialog opens with new initial name
  useEffect(() => {
    if (open) {
      form.reset({
        name: initialName,
        background_summary: '',
      });
    }
  }, [open, initialName, form]);

  const onSubmit = async (values: QuickCreateFormValues) => {
    const agentId = nameToAgentId(values.name);

    // Create with minimal required fields, using sensible defaults
    const createPayload = {
      agent_id: agentId,
      name: values.name,
      background_summary: values.background_summary,
      personality_traits: '',
      skills: {},
      relationships: {},
      current_location: '',
      inventory: [],
      metadata: {},
      structured_data: {},
    };

    try {
      await createCharacter.mutateAsync(createPayload);
      onCharacterCreated(agentId, values.name);
      onClose();
    } catch (error) {
      // Error handling is done via react-query's error state
      console.error('Failed to create character:', error);
    }
  };

  const isLoading = createCharacter.isPending;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="h-5 w-5 text-primary" />
            Quick Create Character
          </DialogTitle>
          <DialogDescription>
            Create a new character without leaving the editor. You can add more details later.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Character name"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="background_summary"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Background{' '}
                    <span className="text-muted-foreground">(optional)</span>
                  </FormLabel>
                  <FormControl>
                    <Textarea
                      rows={3}
                      placeholder="Brief description or backstory..."
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter className="gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Creating...' : 'Create & Insert'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

export default QuickCreateCharacterDialog;
