/**
 * CharacterProfileForm - A form for editing detailed character profiles.
 *
 * Uses react-hook-form with zod validation to manage enhanced character
 * profile fields including aliases, archetype, traits, and appearance.
 * Includes an Auto-Generate button to fill the form using AI generation.
 */
import { useState, useCallback, useMemo, type KeyboardEvent } from 'react';
import { useForm, type UseFormReturn, type Resolver } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { X, Sparkles, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { generateCharacterProfile } from '@/lib/api/generationApi';

/**
 * Schema for character profile form validation.
 * Name is required; other fields are optional for flexibility.
 */
export const CharacterProfileFormSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .max(100, 'Name must be 100 characters or less'),
  aliases: z.array(z.string()).optional().default([]),
  archetype: z.string().max(50, 'Archetype must be 50 characters or less').optional(),
  traits: z.array(z.string()).optional().default([]),
  appearance: z
    .string()
    .max(1000, 'Appearance must be 1000 characters or less')
    .optional(),
  background_summary: z
    .string()
    .max(2000, 'Background must be 2000 characters or less')
    .optional(),
});

/**
 * Form values type with non-optional array fields for internal use.
 * This ensures the form always has arrays to work with.
 */
export type CharacterProfileFormValues = {
  name: string;
  aliases: string[];
  archetype: string;
  traits: string[];
  appearance: string;
  background_summary: string;
};

export interface CharacterProfileFormProps {
  /** Initial values to populate the form */
  defaultValues?: Partial<CharacterProfileFormValues>;
  /** Callback when form is submitted with valid data */
  onSubmit: (data: CharacterProfileFormValues) => void | Promise<void>;
  /** Callback when user cancels editing */
  onCancel?: () => void;
  /** Whether the form is in a loading/submitting state */
  isLoading?: boolean;
  /** Custom submit button text */
  submitLabel?: string;
}

const emptyDefaults: CharacterProfileFormValues = {
  name: '',
  aliases: [],
  archetype: '',
  traits: [],
  appearance: '',
  background_summary: '',
};

/**
 * CharacterProfileForm provides a detailed editing interface for character
 * profiles, including tag-based inputs for aliases and traits.
 */
export function CharacterProfileForm({
  defaultValues,
  onSubmit,
  onCancel,
  isLoading = false,
  submitLabel = 'Save Profile',
}: CharacterProfileFormProps) {
  const [isGenerating, setIsGenerating] = useState(false);

  const form = useForm<CharacterProfileFormValues>({
    resolver: zodResolver(
      CharacterProfileFormSchema
    ) as Resolver<CharacterProfileFormValues>,
    defaultValues: { ...emptyDefaults, ...defaultValues },
    mode: 'onBlur',
  });

  const handleSubmit = async (values: CharacterProfileFormValues) => {
    await onSubmit(values);
  };

  /**
   * Handle auto-generation of character profile using the AI generator.
   * Requires name and archetype to be filled in before generation.
   */
  const handleAutoGenerate = useCallback(async () => {
    const name = form.getValues('name');
    const archetype = form.getValues('archetype');

    if (!name.trim()) {
      toast.error('Please enter a character name first');
      return;
    }

    if (!archetype?.trim()) {
      toast.error('Please enter an archetype first (e.g., Hero, Villain, Mentor)');
      return;
    }

    setIsGenerating(true);

    try {
      const result = await generateCharacterProfile({
        name: name.trim(),
        archetype: archetype.trim(),
        context: form.getValues('background_summary') || undefined,
      });

      // Fill the form with generated values
      form.setValue('name', result.name, { shouldDirty: true });
      form.setValue('aliases', result.aliases, { shouldDirty: true });
      form.setValue('archetype', result.archetype, { shouldDirty: true });
      form.setValue('traits', result.traits, { shouldDirty: true });
      form.setValue('appearance', result.appearance, { shouldDirty: true });
      form.setValue('background_summary', result.backstory, { shouldDirty: true });

      toast.success('Character profile generated successfully');
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to generate profile';
      toast.error(message);
    } finally {
      setIsGenerating(false);
    }
  }, [form]);

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
        {/* Name Field - Required */}
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>
                Name <span className="text-destructive">*</span>
              </FormLabel>
              <FormControl>
                <Input placeholder="Enter character name" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Aliases Field - Tag Input */}
        <TagInputField
          form={form}
          name="aliases"
          label="Aliases"
          description="Alternative names or nicknames"
          placeholder="Type an alias and press Enter"
        />

        {/* Archetype Field */}
        <FormField
          control={form.control}
          name="archetype"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Archetype</FormLabel>
              <FormControl>
                <Input
                  placeholder="e.g., Hero, Mentor, Trickster"
                  {...field}
                  value={field.value ?? ''}
                />
              </FormControl>
              <FormDescription>
                The character's narrative role or archetypal pattern
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Auto-Generate Button */}
        <div className="flex items-center gap-2 rounded-lg border border-dashed border-muted-foreground/25 bg-muted/30 p-4">
          <div className="flex-1">
            <p className="text-sm font-medium">Auto-Generate Profile</p>
            <p className="text-xs text-muted-foreground">
              Fill in name and archetype above, then generate the rest automatically
            </p>
          </div>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={handleAutoGenerate}
            disabled={isGenerating || isLoading}
          >
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                Auto-Generate
              </>
            )}
          </Button>
        </div>

        {/* Traits Field - Tag Input */}
        <TagInputField
          form={form}
          name="traits"
          label="Traits"
          description="Key personality characteristics"
          placeholder="Type a trait and press Enter"
        />

        {/* Appearance Field */}
        <FormField
          control={form.control}
          name="appearance"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Appearance</FormLabel>
              <FormControl>
                <Textarea
                  rows={3}
                  placeholder="Describe the character's physical appearance..."
                  {...field}
                  value={field.value ?? ''}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Background Summary Field */}
        <FormField
          control={form.control}
          name="background_summary"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Background Summary</FormLabel>
              <FormControl>
                <Textarea
                  rows={4}
                  placeholder="Brief history and backstory..."
                  {...field}
                  value={field.value ?? ''}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Form Actions */}
        <div className="flex justify-end gap-3 pt-4">
          {onCancel && (
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={isLoading}
            >
              Cancel
            </Button>
          )}
          <Button type="submit" disabled={isLoading}>
            {isLoading ? 'Saving...' : submitLabel}
          </Button>
        </div>
      </form>
    </Form>
  );
}

/**
 * TagInputField - A reusable component for entering multiple tags.
 * Uses Badge components to display and manage tag values.
 */
interface TagInputFieldProps {
  form: UseFormReturn<CharacterProfileFormValues>;
  name: 'aliases' | 'traits';
  label: string;
  description?: string;
  placeholder?: string;
}

function TagInputField({
  form,
  name,
  label,
  description,
  placeholder,
}: TagInputFieldProps) {
  const [inputValue, setInputValue] = useState('');
  const watchedTags = form.watch(name);
  const currentTags = useMemo(() => watchedTags ?? [], [watchedTags]);

  const addTag = useCallback(
    (tag: string) => {
      const trimmed = tag.trim();
      if (trimmed && !currentTags.includes(trimmed)) {
        form.setValue(name, [...currentTags, trimmed], {
          shouldDirty: true,
          shouldValidate: true,
        });
      }
      setInputValue('');
    },
    [form, name, currentTags]
  );

  const removeTag = useCallback(
    (index: number) => {
      const newTags = currentTags.filter((_, i) => i !== index);
      form.setValue(name, newTags, { shouldDirty: true, shouldValidate: true });
    },
    [form, name, currentTags]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        addTag(inputValue);
      } else if (e.key === 'Backspace' && !inputValue && currentTags.length > 0) {
        removeTag(currentTags.length - 1);
      }
    },
    [addTag, removeTag, inputValue, currentTags.length]
  );

  return (
    <FormField
      control={form.control}
      name={name}
      render={() => (
        <FormItem>
          <FormLabel>{label}</FormLabel>
          <FormControl>
            <div className="space-y-2">
              {/* Tag Display */}
              {currentTags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {currentTags.map((tag, index) => (
                    <Badge
                      key={`${tag}-${index}`}
                      variant="secondary"
                      className="gap-1 pr-1"
                    >
                      {tag}
                      <button
                        type="button"
                        onClick={() => removeTag(index)}
                        className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20"
                        aria-label={`Remove ${tag}`}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
              {/* Tag Input */}
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
              />
            </div>
          </FormControl>
          {description && <FormDescription>{description}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

export default CharacterProfileForm;
