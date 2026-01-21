import { useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import type { CreateCharacterInput } from '@/shared/types/character';
import { WorkspaceCharacterCreateSchema } from '@/types/schemas';
import { useCreateCharacter, useUpdateCharacter } from './api/characterApi';

type Props = {
  open: boolean;
  onClose: () => void;
  onCharacterCreated: () => void;
  mode?: 'create' | 'edit';
  characterId?: string;
  initialData?: CreateCharacterInput;
};

const defaultValues: CreateCharacterInput = {
  agent_id: '',
  name: '',
  background_summary: '',
  personality_traits: '',
  skills: {},
  relationships: {},
  current_location: '',
  inventory: [],
  metadata: {},
  structured_data: {},
};

export default function CharacterCreationDialog({
  open,
  onClose,
  onCharacterCreated,
  mode = 'create',
  characterId,
  initialData,
}: Props) {
  const createCharacter = useCreateCharacter();
  const updateCharacter = useUpdateCharacter();
  const isEdit = mode === 'edit';

  const form = useForm<CreateCharacterInput>({
    resolver: zodResolver(WorkspaceCharacterCreateSchema),
    defaultValues: initialData ?? defaultValues,
    mode: 'onBlur',
  });

  const inventoryFieldArray = useFieldArray({
    control: form.control,
    name: 'inventory',
  });

  useEffect(() => {
    if (!open) return;
    form.reset(initialData ?? defaultValues);
  }, [open, form, initialData]);

  const onSubmit = async (values: CreateCharacterInput) => {
    if (isEdit) {
      if (!characterId) return;
      const { agent_id: _agentId, ...payload } = values;
      await updateCharacter.mutateAsync({ id: characterId, ...payload });
    } else {
      await createCharacter.mutateAsync(values);
    }
    onCharacterCreated();
    onClose();
  };

  const isLoading = createCharacter.isPending || updateCharacter.isPending;

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Character' : 'Create New Character'}</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="agent_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Agent ID</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="unique-agent-id"
                      disabled={isEdit}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input placeholder="Character name" {...field} />
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
                  <FormLabel>Background Summary</FormLabel>
                  <FormControl>
                    <Textarea rows={4} placeholder="Short background summary" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="personality_traits"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Personality Traits</FormLabel>
                  <FormControl>
                    <Textarea rows={3} placeholder="Traits and temperament" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="current_location"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Current Location</FormLabel>
                  <FormControl>
                    <Input placeholder="Current location" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <FormLabel>Inventory</FormLabel>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => inventoryFieldArray.append('')}
                >
                  Add Item
                </Button>
              </div>
              {inventoryFieldArray.fields.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No inventory items yet.
                </p>
              ) : (
                <div className="space-y-2">
                  {inventoryFieldArray.fields.map((fieldItem, index) => (
                    <FormField
                      key={fieldItem.id}
                      control={form.control}
                      name={`inventory.${index}`}
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Input placeholder="Item name" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  ))}
                </div>
              )}
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
                Cancel
              </Button>
              <Button type="submit" loading={isLoading}>
                {isEdit ? 'Save Changes' : 'Create Character'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
