import type { Dispatch, SetStateAction } from "react";
import { act, useState } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { createMountHarness } from "@/test/harness";

import { combineErrorMessages, useOwnerKeyedErrors } from "./useOwnerKeyedErrors";

const harness = createMountHarness();
const sources = ["draft", "proposal", "revision", "restore"] as const;

afterEach(() => harness.cleanup());

function renderErrors(initialOwnerKey: string) {
  let ownerKey = initialOwnerKey;
  let current:
    | {
        readonly error: string | null;
        readonly publishers: Record<
          (typeof sources)[number],
          Dispatch<SetStateAction<string | null>>
        >;
      }
    | undefined;

  function Wrapper(): null {
    current = useOwnerKeyedErrors(ownerKey, sources);
    return null;
  }

  const { root } = harness.mount(<Wrapper />);
  return {
    result: () => {
      if (!current) throw new Error("Expected owner-keyed errors after render.");
      return current;
    },
    rerender: (nextOwnerKey: string) => {
      ownerKey = nextOwnerKey;
      act(() => root.render(<Wrapper />));
    },
  };
}

describe("useOwnerKeyedErrors", () => {
  it("restores each document's errors when its owner becomes active again", () => {
    const view = renderErrors("project-1\u0000document-a");

    act(() => view.result().publishers.proposal("A proposal failed."));
    expect(view.result().error).toBe("A proposal failed.");

    view.rerender("project-1\u0000document-b");
    expect(view.result().error).toBeNull();
    act(() => view.result().publishers.draft("B save failed."));
    expect(view.result().error).toBe("B save failed.");

    view.rerender("project-1\u0000document-a");
    expect(view.result().error).toBe("A proposal failed.");
  });

  it("keeps a late publisher bound to its initiating owner", () => {
    const view = renderErrors("project-1\u0000document-a");
    const publishA = view.result().publishers.proposal;

    view.rerender("project-1\u0000document-b");
    act(() => publishA("Late A failure."));
    expect(view.result().error).toBeNull();

    view.rerender("project-1\u0000document-a");
    expect(view.result().error).toBe("Late A failure.");
  });

  it("clears only the publishing source and keeps concurrent errors readable", () => {
    const view = renderErrors("project-1\u0000document-a");

    act(() => {
      view.result().publishers.draft("Autosave failed.");
      view.result().publishers.revision("Revision history failed.");
    });
    expect(view.result().error).toContain("Autosave failed.");
    expect(view.result().error).toContain("Revision history failed.");

    act(() => view.result().publishers.revision(null));
    expect(view.result().error).toBe("Autosave failed.");
  });

  it("keeps a document error when an independent project operation succeeds", () => {
    let current:
      | {
          readonly document: ReturnType<typeof useOwnerKeyedErrors<(typeof sources)[number]>>;
          readonly error: string | null;
          readonly setProjectError: Dispatch<SetStateAction<string | null>>;
        }
      | undefined;

    function Wrapper(): null {
      const [projectError, setProjectError] = useState<string | null>(null);
      const document = useOwnerKeyedErrors("project-1\u0000document-a", sources);
      current = {
        document,
        error: combineErrorMessages(document.error, projectError),
        setProjectError,
      };
      return null;
    }

    harness.mount(<Wrapper />);
    if (!current) throw new Error("Expected separated errors after render.");
    act(() => {
      current?.document.publishers.draft("Autosave failed.");
      current?.setProjectError("Jobs failed.");
    });
    expect(current?.error).toContain("Autosave failed.");
    expect(current?.error).toContain("Jobs failed.");

    act(() => current?.setProjectError(null));
    expect(current?.error).toBe("Autosave failed.");
  });
});
