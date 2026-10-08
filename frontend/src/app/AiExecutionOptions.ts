/** Per-operation transport options; ACP has a 600s server budget plus response grace. */
export interface AiExecutionOptions extends RequestInit {
  readonly timeoutMs?: number;
}
export const ACP_REQUEST_TIMEOUT_MS = 610_000;
