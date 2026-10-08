import { fireEvent, screen } from "@testing-library/dom";
import { afterEach, expect, it, vi } from "vitest";
import { createMountHarness } from "@/test/harness";
import { StudioAcpOperations } from "./StudioAcpOperations";

const harness = createMountHarness();
afterEach(() => harness.cleanup());
it("names the target and forwards the exact CLI option without treating Stop as rollback", () => {
  const respond = vi.fn();
  const cancel = vi.fn();
  harness.mount(
    <StudioAcpOperations
      operations={[
        {
          id: "operation",
          phase: "waiting",
          tools: [],
          permissions: [
            {
              type: "permission",
              permission_id: "permission",
              tool: { title: "Write notes", kind: "edit", target: "chapter-notes.md" },
              options: [
                {
                  option_id: "keep-cli-policy",
                  name: "Always allow for this session",
                  kind: "allow_always",
                },
                { option_id: "deny", name: "Reject", kind: "reject_once" },
              ],
            },
          ],
          error: null,
          effects: "completed",
          decidingPermissionIds: [],
        },
      ]}
      onRespond={respond}
      onCancel={cancel}
    />,
  );
  expect(screen.getByText("chapter-notes.md")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Always allow for this session" }));
  expect(respond).toHaveBeenCalledWith("operation", "permission", "keep-cli-policy");
  fireEvent.click(screen.getByRole("button", { name: "Stop operation" }));
  expect(cancel).toHaveBeenCalledWith("operation");
  expect(screen.getByText("Completed file changes remain in your working folder.")).toBeTruthy();
});
