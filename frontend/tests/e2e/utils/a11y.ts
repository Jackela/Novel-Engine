import type { Page } from '@playwright/test';
import { expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const DEFAULT_IGNORED_RULES = ['color-contrast', 'list', 'scrollable-region-focusable'];
const DEFAULT_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

export const checkA11y = async (page: Page) => {
  const results = await new AxeBuilder({ page })
    .disableRules(DEFAULT_IGNORED_RULES)
    .withTags(DEFAULT_TAGS)
    .analyze();

  expect(results.violations).toEqual([]);
};
