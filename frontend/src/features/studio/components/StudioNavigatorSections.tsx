import { useTranslation } from "@/app/i18n/useTranslation";

import { SECTIONS } from "../studioConstants";

interface StudioNavigatorSectionsProps {
  readonly section: string;
  readonly onNavigateSection: (section: string) => void;
}

/**
 * The URL-owned section switcher: one button per studio section,
 * with `aria-current="page"` on the active one. The first SECTIONS
 * tuple element stays the route segment; the second resolves
 * through the dictionaries so the navigator follows the active
 * UI language.
 */
export function StudioNavigatorSections({
  onNavigateSection,
  section,
}: StudioNavigatorSectionsProps) {
  const { t } = useTranslation();
  return (
    <nav className="studio-nav__sections" aria-label={t("navigator.sections.label")}>
      {SECTIONS.map(([path, labelKey]) => (
        <button
          aria-current={section === path ? "page" : undefined}
          className={
            section === path
              ? "studio-nav__section studio-nav__section--active"
              : "studio-nav__section"
          }
          key={path}
          onClick={() => onNavigateSection(path)}
          type="button"
        >
          {t(labelKey)}
        </button>
      ))}
    </nav>
  );
}
