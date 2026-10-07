import { Loader2, Plus } from "lucide-react";
import type { FormEvent, RefObject } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";

import type { LibraryOperation } from "../hooks/useProjectLibraryActions";

interface ProjectLibraryCreateFormProps {
  readonly createButtonRef: RefObject<HTMLButtonElement | null>;
  readonly description: string;
  readonly onDescriptionChange: (value: string) => void;
  readonly onSubmit: (event: FormEvent) => void;
  readonly onTitleChange: (value: string) => void;
  readonly operation: LibraryOperation | null;
  readonly title: string;
}

/**
 * The create-project form: title and premise fields feeding the page's
 * create command. Every control locks while any operation holds the
 * page's command slot; the submit button reports the creating
 * operation specifically.
 */
export function ProjectLibraryCreateForm({
  createButtonRef,
  description,
  onDescriptionChange,
  onSubmit,
  onTitleChange,
  operation,
  title,
}: ProjectLibraryCreateFormProps) {
  const { t } = useTranslation();
  return (
    <form className="library-create" onSubmit={onSubmit}>
      <div className="library-create__icon">
        <Plus aria-hidden="true" />
      </div>
      <h2>{t("library.create.newProject")}</h2>
      <label>
        <span>{t("common.field.title")}</span>
        <input
          disabled={operation !== null}
          value={title}
          onChange={(event) => onTitleChange(event.target.value)}
          required
        />
      </label>
      <label>
        <span>{t("library.create.premise")}</span>
        <textarea
          value={description}
          disabled={operation !== null}
          onChange={(event) => onDescriptionChange(event.target.value)}
          rows={4}
        />
      </label>
      <button
        aria-busy={operation === "create" || undefined}
        className="ui-command ui-command--primary"
        disabled={operation !== null}
        ref={createButtonRef}
        type="submit"
      >
        {operation === "create" ? <Loader2 aria-hidden="true" className="ui-spin" /> : null}
        {operation === "create" ? t("library.action.creating") : t("library.action.create")}
      </button>
    </form>
  );
}
