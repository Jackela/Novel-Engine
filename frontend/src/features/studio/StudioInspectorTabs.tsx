import type { Dispatch, KeyboardEvent, ReactNode, SetStateAction } from 'react';
import { Bot, Briefcase, Download, History, ShieldCheck } from 'lucide-react';

import { INSPECTOR_TABS, type InspectorTab } from './studioConstants';

interface StudioInspectorTabsProps {
  inspector: InspectorTab;
  tabId: (tab: Exclude<InspectorTab, 'settings'>) => string;
  panelId: (tab: Exclude<InspectorTab, 'settings'>) => string;
  setInspector: Dispatch<SetStateAction<InspectorTab>>;
}

export function StudioInspectorTabs({
  inspector,
  tabId,
  panelId,
  setInspector,
}: StudioInspectorTabsProps) {
  const onTabKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    currentTab: Exclude<InspectorTab, 'settings'>,
  ) => {
    const currentIndex = INSPECTOR_TABS.indexOf(currentTab);
    let nextIndex = currentIndex;
    if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
    if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % INSPECTOR_TABS.length;
    if (event.key === 'ArrowLeft') {
      nextIndex = (currentIndex - 1 + INSPECTOR_TABS.length) % INSPECTOR_TABS.length;
    }
    if (event.key === 'Home') nextIndex = 0;
    if (event.key === 'End') nextIndex = INSPECTOR_TABS.length - 1;
    event.preventDefault();
    if (nextIndex === currentIndex) return;
    const nextTab = INSPECTOR_TABS[nextIndex];
    setInspector(nextTab);
    event.currentTarget.parentElement
      ?.querySelector<HTMLButtonElement>(`[data-inspector-index="${nextIndex}"]`)
      ?.focus();
  };

  const tabButton = (tab: Exclude<InspectorTab, 'settings'>, label: string, icon: ReactNode) => (
    <button
      aria-controls={panelId(tab)}
      aria-selected={inspector === tab}
      className={inspector === tab ? 'active' : ''}
      data-inspector-index={INSPECTOR_TABS.indexOf(tab)}
      id={tabId(tab)}
      onClick={() => setInspector(tab)}
      onKeyDown={(event) => onTabKeyDown(event, tab)}
      role="tab"
      tabIndex={inspector === tab ? 0 : -1}
      type="button"
    >
      {icon} {label}
    </button>
  );

  return (
    <div
      aria-label="Inspector panels"
      aria-orientation="horizontal"
      className="inspector-tabs"
      role="tablist"
    >
      {tabButton('copilot', 'Copilot', <Bot aria-hidden="true" />)}
      {tabButton('review', 'Review', <ShieldCheck aria-hidden="true" />)}
      {tabButton('history', 'History', <History aria-hidden="true" />)}
      {tabButton('export', 'Export', <Download aria-hidden="true" />)}
      {tabButton('jobs', 'Jobs', <Briefcase aria-hidden="true" />)}
    </div>
  );
}
