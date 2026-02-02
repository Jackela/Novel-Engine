/**
 * CharacterForm - Form for creating/editing characters
 */
import { useForm, type Resolver, type UseFormReturn } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Label } from '@/components/ui/label';
import type { CharacterDetail, CreateCharacterInput } from '@/shared/types/character';
import { WorkspaceCharacterCreateSchema } from '@/types/schemas';

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

interface CharacterFormProps {
  character?: CharacterDetail;
  onSubmit: (data: CreateCharacterInput) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const emptyDefaults: CharacterFormValues = {
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

export function CharacterForm({
  character,
  onSubmit,
  onCancel,
  isLoading = false,
}: CharacterFormProps) {
  const form = useForm<CharacterFormValues>({
    resolver: zodResolver(
      WorkspaceCharacterCreateSchema
    ) as Resolver<CharacterFormValues>,
    defaultValues: character
      ? {
          ...emptyDefaults,
          agent_id: character.agent_id,
          name: character.name,
          background_summary: character.background_summary,
          personality_traits: character.personality_traits,
          current_location: character.current_location,
          inventory: character.inventory,
          skills: character.skills,
          relationships: character.relationships,
          metadata: character.metadata,
          structured_data: character.structured_data,
        }
      : emptyDefaults,
    mode: 'onBlur',
  });

  const inventoryItems = form.watch('inventory') ?? [];

  const handleAddInventory = () => {
    form.setValue('inventory', [...inventoryItems, ''], { shouldDirty: true });
  };

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((values) => {
          const parsed = WorkspaceCharacterCreateSchema.parse(values);
          onSubmit(parsed);
        })}
        className="space-y-6"
      >
        <CharacterDetailsFields form={form} />
        <InventoryFieldList
          form={form}
          items={inventoryItems}
          onAddItem={handleAddInventory}
        />

        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? 'Saving...' : character ? 'Update' : 'Create'} Character
          </Button>
        </div>
      </form>
    </Form>
  );
}

type CharacterDetailsFieldsProps = {
  form: UseFormReturn<CharacterFormValues>;
};

function CharacterDetailsFields({ form }: CharacterDetailsFieldsProps) {
  return (
    <>
      <FormField
        control={form.control}
        name="agent_id"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Agent ID</FormLabel>
            <FormControl>
              <Input placeholder="unique-agent-id" {...field} />
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
            <FormLabel>Character Description</FormLabel>
            <FormControl>
              <Textarea rows={4} placeholder="Character description" {...field} />
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

      <FormField
        control={form.control}
        name={'metadata.role' as const}
        render={({ field }) => (
          <FormItem>
            <FormLabel>Role</FormLabel>
            <FormControl>
              <Input
                placeholder="Role"
                value={typeof field.value === 'string' ? field.value : ''}
                onChange={field.onChange}
                onBlur={field.onBlur}
                name={field.name}
                ref={field.ref}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={form.control}
        name={'metadata.faction_id' as const}
        render={({ field }) => (
          <FormItem>
            <FormLabel>Faction</FormLabel>
            <Select
              value={typeof field.value === 'string' ? field.value : ''}
              onValueChange={field.onChange}
            >
              <FormControl>
                <SelectTrigger data-testid="faction-select">
                  <SelectValue placeholder="Select faction" />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                <SelectItem value="alliance-network">Alliance Network</SelectItem>
                <SelectItem value="shadowbane-order">Shadowbane Order</SelectItem>
                <SelectItem value="merchants-alliance">Merchants Alliance</SelectItem>
              </SelectContent>
            </Select>
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
        <Label>Inventory</Label>
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
              render={({ field: itemField }) => (
                <FormItem>
                  <FormControl>
                    <Input placeholder="Item name" {...itemField} />
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
