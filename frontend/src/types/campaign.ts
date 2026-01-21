import { z } from 'zod';
import { CampaignSchema } from '@/types/schemas';

export type Campaign = z.infer<typeof CampaignSchema>;
