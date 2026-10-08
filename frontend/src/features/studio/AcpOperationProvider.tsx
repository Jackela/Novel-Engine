import { createContext, type ReactNode, useContext } from "react";
import { translateActive } from "@/app/i18n/translate";
import { useSessionExpiredRedirect } from "@/app/sessionExpiry";
import { type AcpExecute, useAcpOperation } from "./hooks/useAcpOperation";

const AcpOperationContext = createContext<ReturnType<typeof useAcpOperation> | null>(null);
const executeWithoutObserver: AcpExecute = async (provider, operation) => {
  if (provider === "acp") throw new Error(translateActive("acp.error.missingObserver"));
  return operation();
};

/** One project owns the observation state used by all four generation steps. */
export function AcpOperationProvider({
  projectId,
  children,
}: {
  readonly projectId: string;
  readonly children: ReactNode;
}) {
  const onSessionLost = useSessionExpiredRedirect();
  const value = useAcpOperation(projectId, onSessionLost);
  return <AcpOperationContext value={value}>{children}</AcpOperationContext>;
}
export function useAcpExecution(): AcpExecute {
  return useContext(AcpOperationContext)?.execute ?? executeWithoutObserver;
}
export function useAcpOperationView() {
  return useContext(AcpOperationContext);
}
