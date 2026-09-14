import { BarChart3, Bot, Briefcase, Download, History, LineChart, ShieldCheck } from "lucide-react";
import {
  type Dispatch,
  type KeyboardEvent,
  type ReactNode,
  type SetStateAction,
  useRef,
} from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import { INSPECTOR_TABS, type InspectorTab } from "./studioConstants";

interface StudioInspectorTabsProps {
  inspector: InspectorTab;
  tabId: (tab: Exclude<InspectorTab, "settings">) => string;
  panelId: (tab: Exclude<InspectorTab, "settings">) => string;
  setInspector: Dispatch<SetStateAction<InspectorTab>>;
}

export function StudioInspectorTabs({
  inspector,
  tabId,
  panelId,
  setInspector,
}: StudioInspectorTabsProps) {
  const { t } = useTranslation();
  // #411: focus via refs instead of DOM queries.
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const onTabKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    currentTab: Exclude<InspectorTab, "settings">,
  ) => {
    const currentIndex = INSPECTOR_TABS.indexOf(currentTab);
    let nextIndex = currentIndex;
    if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
    if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % INSPECTOR_TABS.length;
    if (event.key === "ArrowLeft") {
      nextIndex = (currentIndex - 1 + INSPECTOR_TABS.length) % INSPECTOR_TABS.length;
    }
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = INSPECTOR_TABS.length - 1;
    event.preventDefault();
    if (nextIndex === currentIndex) return;
    const nextTab = INSPECTOR_TABS[nextIndex];
    setInspector(nextTab);
    tabRefs.current[nextIndex]?.focus();
  };

  const tabButton = (tab: Exclude<InspectorTab, "settings">, label: string, icon: ReactNode) => (
    <button
      aria-controls={panelId(tab)}
      aria-selected={inspector === tab}
      className={
        inspector === tab
          ? "studio-inspector__tab studio-inspector__tab--active"
          : "studio-inspector__tab"
      }
      id={tabId(tab)}
      onClick={() => setInspector(tab)}
      onKeyDown={(event) => onTabKeyDown(event, tab)}
      ref={(node) => {
        tabRefs.current[INSPECTOR_TABS.indexOf(tab)] = node;
      }}
      role="tab"
      tabIndex={inspector === tab ? 0 : -1}
      type="button"
    >
      {icon} {label}
    </button>
  );

  return (
    <div
      aria-label={t("inspector.tablist")}
      aria-orientation="horizontal"
      className="studio-inspector__tabs"
      role="tablist"
    >
      {tabButton("copilot", t("inspector.tab.copilot"), <Bot aria-hidden="true" />)}
      {tabButton("review", t("inspector.tab.review"), <ShieldCheck aria-hidden="true" />)}
      {tabButton("history", t("inspector.tab.history"), <History aria-hidden="true" />)}
      {tabButton("export", t("inspector.tab.export"), <Download aria-hidden="true" />)}
      {tabButton("jobs", t("inspector.tab.jobs"), <Briefcase aria-hidden="true" />)}
      {tabButton("usage", t("inspector.tab.usage"), <BarChart3 aria-hidden="true" />)}
      {tabButton("stats", t("inspector.tab.stats"), <LineChart aria-hidden="true" />)}
    </div>
  );
}
