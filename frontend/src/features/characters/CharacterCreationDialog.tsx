import { useEffect } from 'react';
import { useForm, type Resolver, type UseFormReturn } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

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
import {
  WorkspaceCharacterCreateSchema,
  WorkspaceCharacterUpdateSchema,
} from '@/types/schemas';
import { useCreateCharacter, useUpdateCharacter } from './api/characterApi';

type CharacterFormValues = {
  agent_id: string;
  name: string;
  background_summary: string;
  personality_traits: string;
  skills: Record<string, number>;
  relationships: Record<string, number>;
  current_location: string;
  inventory: string[];
  metadata: Record<string, unknown>;
  structured_data: Record<string, unknown>;
};

type Props = {
  open: boolean;
  onClose: () => void;
  onCharacterCreated: () => void;
  mode?: 'create' | 'edit';
  characterId?: string;
  initialData?: CharacterFormValues;
};

const defaultValues: CharacterFormValues = {
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

  const form = useForm<CharacterFormValues>({
    resolver: zodResolver(
      WorkspaceCharacterCreateSchema
    ) as Resolver<CharacterFormValues>,
    defaultValues: initialData ?? defaultValues,
    mode: 'onBlur',
  });

  const inventoryItems = form.watch('inventory') ?? [];
  const handleAddInventoryItem = () => {
    form.setValue('inventory', [...inventoryItems, ''], { shouldDirty: true });
  };

  useEffect(() => {
    if (!open) return;
    form.reset(initialData ?? defaultValues);
  }, [open, form, initialData]);

  const onSubmit = async (values: CharacterFormValues) => {
    const parsed = WorkspaceCharacterCreateSchema.parse(values);
    if (isEdit) {
      if (!characterId) return;
      const { agent_id: _agentId, ...payload } = parsed;
      const updatePayload = WorkspaceCharacterUpdateSchema.parse(payload);
      await updateCharacter.mutateAsync({ id: characterId, ...updatePayload });
    } else {
      await createCharacter.mutateAsync(parsed);
    }
    onCharacterCreated();
    onClose();
  };

  const isLoading = createCharacter.isPending || updateCharacter.isPending;

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? 'Edit Character' : 'Create New Character'}
          </DialogTitle>
          <DialogDescription className="sr-only">
            {isEdit
              ? 'Update the character profile fields.'
              : 'Fill out the form to create a new character.'}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <CharacterFormFields form={form} isEdit={isEdit} />
            <InventoryFieldList
              form={form}
              items={inventoryItems}
              onAddItem={handleAddInventoryItem}
            />

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Character'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

type CharacterFormFieldsProps = {
  form: UseFormReturn<CharacterFormValues>;
  isEdit: boolean;
};

function CharacterFormFields({ form, isEdit }: CharacterFormFieldsProps) {
  return (
    <>
      <FormField
        control={form.control}
        name="agent_id"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Agent ID</FormLabel>
            <FormControl>
              <Input placeholder="unique-agent-id" disabled={isEdit} {...field} />
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
    </>
  );
}

type InventoryFieldListProps = {
  form: UseFormReturn<CharacterFormValues>;
  items: string[];
  onAddItem: () => void;
};

function InventoryFieldList({ form, items, onAddItem }: InventoryFieldListProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <FormLabel>Inventory</FormLabel>
        <Button type="button" variant="outline" size="sm" onClick={onAddItem}>
          Add Item
        </Button>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No inventory items yet.</p>
      ) : (
        <div className="space-y-2">
          {items.map((_, index) => (
            <FormField
              key={index}
              control={form.control}
              name={`inventory.${index}` as const}
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
  );
}
