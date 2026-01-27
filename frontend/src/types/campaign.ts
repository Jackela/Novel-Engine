import type { z } from 'zod';
import type { CampaignSchema } from '@/types/schemas';

export type Campaign = z.infer<typeof CampaignSchema>;
