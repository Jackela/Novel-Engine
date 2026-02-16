import { useState, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Sword,
  Shield,
  Beaker,
  Key,
  Package,
  Plus,
  Trash2,
  Loader2,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { ItemResponse, ItemType, ItemRarity } from '@/types/schemas';

type Props = {
  characterId: string;
};

const ITEM_TYPE_LABELS: Record<ItemType, string> = {
  weapon: 'Weapon',
  armor: 'Armor',
  consumable: 'Consumable',
  key_item: 'Key Item',
  misc: 'Misc',
};

const ITEM_TYPE_ICONS: Record<ItemType, typeof Sword> = {
  weapon: Sword,
  armor: Shield,
  consumable: Beaker,
  key_item: Key,
  misc: Package,
};

const RARITY_COLORS: Record<ItemRarity, string> = {
  common: 'bg-zinc-500/20 text-zinc-700 dark:text-zinc-300',
  uncommon: 'bg-green-500/20 text-green-700 dark:text-green-300',
  rare: 'bg-blue-500/20 text-blue-700 dark:text-blue-300',
  legendary: 'bg-amber-500/20 text-amber-700 dark:text-amber-300',
};

async function fetchInventory(characterId: string): Promise<ItemResponse[]> {
  const res = await fetch(`/api/characters/${characterId}/inventory`);
  if (!res.ok) throw new Error('Failed to fetch inventory');
  const data = await res.json();
  return data.items;
}

async function fetchAllItems(): Promise<ItemResponse[]> {
  const res = await fetch('/api/items');
  if (!res.ok) throw new Error('Failed to fetch items');
  const data = await res.json();
  return data.items;
}

async function giveItem(characterId: string, itemId: string): Promise<void> {
  const res = await fetch(`/api/characters/${characterId}/give-item`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_id: itemId }),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to give item');
  }
}

async function removeItem(characterId: string, itemId: string): Promise<void> {
  const res = await fetch(`/api/characters/${characterId}/remove-item/${itemId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to remove item');
}

function ItemIcon({ type }: { type: ItemType }) {
  const Icon = ITEM_TYPE_ICONS[type];
  return <Icon className="h-4 w-4 text-muted-foreground" />;
}

function RarityBadge({ rarity }: { rarity: ItemRarity }) {
  return (
    <Badge variant="outline" className={RARITY_COLORS[rarity]}>
      {rarity.charAt(0).toUpperCase() + rarity.slice(1)}
    </Badge>
  );
}

type ItemRowProps = {
  item: ItemResponse;
  onRemove: (itemId: string) => void;
  isRemoving: boolean;
};

function ItemRow({ item, onRemove, isRemoving }: ItemRowProps) {
  return (
    <li className="flex items-center justify-between rounded-lg border bg-card p-3">
      <div className="flex items-center gap-3">
        <ItemIcon type={item.item_type} />
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium">{item.name}</span>
            <RarityBadge rarity={item.rarity} />
          </div>
          {item.description && (
            <p className="line-clamp-1 text-sm text-muted-foreground">
              {item.description}
            </p>
          )}
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => onRemove(item.id)}
        disabled={isRemoving}
        className="text-destructive hover:bg-destructive/10 hover:text-destructive"
      >
        {isRemoving ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Trash2 className="h-4 w-4" />
        )}
      </Button>
    </li>
  );
}

type GiveItemDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  availableItems: ItemResponse[];
  isLoading: boolean;
  selectedItemId: string;
  onSelectItem: (itemId: string) => void;
  onConfirm: () => void;
  isPending: boolean;
  error: Error | null;
};

function GiveItemDialog({
  open,
  onOpenChange,
  availableItems,
  isLoading,
  selectedItemId,
  onSelectItem,
  onConfirm,
  isPending,
  error,
}: GiveItemDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Plus className="mr-2 h-4 w-4" />
          Give Item
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Give Item to Character</DialogTitle>
          <DialogDescription className="sr-only">
            Select an item to add to the character inventory.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 pt-4">
          <Select
            value={selectedItemId}
            onValueChange={onSelectItem}
            disabled={isLoading}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select an item..." />
            </SelectTrigger>
            <SelectContent>
              {availableItems.map((item) => (
                <SelectItem key={item.id} value={item.id}>
                  <div className="flex items-center gap-2">
                    <ItemIcon type={item.item_type} />
                    <span>{item.name}</span>
                    <RarityBadge rarity={item.rarity} />
                  </div>
                </SelectItem>
              ))}
              {availableItems.length === 0 && (
                <div className="p-2 text-sm text-muted-foreground">
                  No items available to give.
                </div>
              )}
            </SelectContent>
          </Select>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={onConfirm} disabled={!selectedItemId || isPending}>
              {isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Give Item
            </Button>
          </div>

          {error && (
            <p className="text-sm text-destructive">
              {error instanceof Error ? error.message : 'Failed to give item'}
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function InventoryTab({ characterId }: Props) {
  const queryClient = useQueryClient();
  const [typeFilter, setTypeFilter] = useState<ItemType | 'all'>('all');
  const [giveDialogOpen, setGiveDialogOpen] = useState(false);
  const [selectedItemId, setSelectedItemId] = useState<string>('');

  const {
    data: inventory = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['character-inventory', characterId],
    queryFn: () => fetchInventory(characterId),
    enabled: Boolean(characterId),
  });

  const { data: allItems = [], isLoading: allItemsLoading } = useQuery({
    queryKey: ['all-items'],
    queryFn: fetchAllItems,
  });

  const giveMutation = useMutation({
    mutationFn: (itemId: string) => giveItem(characterId, itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['character-inventory', characterId] });
      setGiveDialogOpen(false);
      setSelectedItemId('');
    },
  });

  const removeMutation = useMutation({
    mutationFn: (itemId: string) => removeItem(characterId, itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['character-inventory', characterId] });
    },
  });

  const handleGiveItem = useCallback(() => {
    if (selectedItemId) giveMutation.mutate(selectedItemId);
  }, [selectedItemId, giveMutation]);

  const handleRemoveItem = useCallback(
    (itemId: string) => removeMutation.mutate(itemId),
    [removeMutation]
  );

  const filteredInventory = useMemo(() => {
    if (typeFilter === 'all') return inventory;
    return inventory.filter((item) => item.item_type === typeFilter);
  }, [inventory, typeFilter]);

  const availableItems = useMemo(() => {
    const inventoryIds = new Set(inventory.map((item) => item.id));
    return allItems.filter((item) => !inventoryIds.has(item.id));
  }, [allItems, inventory]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-4 text-sm text-destructive">
        Failed to load inventory. Please try again.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <Select
          value={typeFilter}
          onValueChange={(value) => setTypeFilter(value as ItemType | 'all')}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="weapon">Weapons</SelectItem>
            <SelectItem value="armor">Armor</SelectItem>
            <SelectItem value="consumable">Consumables</SelectItem>
            <SelectItem value="key_item">Key Items</SelectItem>
            <SelectItem value="misc">Misc</SelectItem>
          </SelectContent>
        </Select>

        <GiveItemDialog
          open={giveDialogOpen}
          onOpenChange={setGiveDialogOpen}
          availableItems={availableItems}
          isLoading={allItemsLoading}
          selectedItemId={selectedItemId}
          onSelectItem={setSelectedItemId}
          onConfirm={handleGiveItem}
          isPending={giveMutation.isPending}
          error={giveMutation.error}
        />
      </div>

      {filteredInventory.length === 0 ? (
        <div className="py-4 text-center text-sm text-muted-foreground">
          {typeFilter === 'all'
            ? 'No items in inventory.'
            : `No ${ITEM_TYPE_LABELS[typeFilter].toLowerCase()} items.`}
        </div>
      ) : (
        <ul className="space-y-2">
          {filteredInventory.map((item) => (
            <ItemRow
              key={item.id}
              item={item}
              onRemove={handleRemoveItem}
              isRemoving={removeMutation.isPending}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
