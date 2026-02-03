/**
 * FactionMembers - Display faction roster with member roles
 *
 * Shows a scrollable list of characters belonging to a faction,
 * highlighting the faction leader with a crown icon.
 */
import { Crown, User, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import type { FactionMember } from '@/types/schemas';

type Props = {
  members: FactionMember[];
  factionName?: string;
};

/**
 * Format character ID to display name.
 * Converts `aria-shadowbane` to `Aria Shadowbane`.
 */
function formatDisplayName(member: FactionMember): string {
  if (member.name && member.name.trim()) {
    return member.name;
  }
  // Fallback: format ID as display name
  return member.character_id
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Single member item in the roster.
 */
function MemberItem({ member }: { member: FactionMember }) {
  const displayName = formatDisplayName(member);

  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-muted/50',
        member.is_leader && 'border-amber-500/50 bg-amber-500/10'
      )}
    >
      <div
        className={cn(
          'flex h-8 w-8 items-center justify-center rounded-full',
          member.is_leader ? 'bg-amber-500/20' : 'bg-muted'
        )}
      >
        {member.is_leader ? (
          <Crown className="h-4 w-4 text-amber-500" />
        ) : (
          <User className="h-4 w-4 text-muted-foreground" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{displayName}</p>
        {member.is_leader && (
          <Badge
            variant="outline"
            className="mt-1 border-amber-500/50 text-xs text-amber-500"
          >
            Leader
          </Badge>
        )}
      </div>
    </div>
  );
}

/**
 * FactionMembers displays a roster of faction members.
 *
 * Features:
 * - Scrollable list of members
 * - Leader highlighted with crown icon and amber styling
 * - Character names formatted from IDs when display name unavailable
 * - Member count header
 */
export default function FactionMembers({ members, factionName }: Props) {
  if (!members || members.length === 0) {
    return (
      <div className="flex h-48 flex-col items-center justify-center text-muted-foreground">
        <Users className="mb-2 h-8 w-8" />
        <p className="text-sm">No members in this faction.</p>
      </div>
    );
  }

  // Sort: leader first, then alphabetically by name
  const sortedMembers = [...members].sort((a, b) => {
    // Leader always first
    if (a.is_leader && !b.is_leader) return -1;
    if (!a.is_leader && b.is_leader) return 1;

    // Alphabetical by display name
    const nameA = formatDisplayName(a).toLowerCase();
    const nameB = formatDisplayName(b).toLowerCase();
    return nameA.localeCompare(nameB);
  });

  const leader = sortedMembers.find((m) => m.is_leader);

  return (
    <div className="space-y-4">
      {/* Header with member count */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-muted-foreground">
          {factionName ? `${factionName} Roster` : 'Faction Roster'}
        </h4>
        <Badge variant="secondary" className="text-xs">
          {members.length} {members.length === 1 ? 'member' : 'members'}
        </Badge>
      </div>

      {/* Leader summary if exists */}
      {leader && (
        <div className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400">
          <Crown className="h-4 w-4" />
          <span>Led by {formatDisplayName(leader)}</span>
        </div>
      )}

      {/* Scrollable member list */}
      <ScrollArea className="h-64">
        <div className="space-y-2 pr-4">
          {sortedMembers.map((member) => (
            <MemberItem key={member.character_id} member={member} />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
