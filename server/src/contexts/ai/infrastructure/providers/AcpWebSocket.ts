import WebSocket from "ws";

/**
 * SDK 1.7 detaches its error listener when its stream is cancelled. Closing
 * a connecting Node socket then emits this specific, expected abort error
 * asynchronously. Keep it handled while preserving every other error.
 */
export class AcpWebSocket extends WebSocket {
  private connectingAbortHandled = false;

  override close(code?: number, data?: string | Buffer): void {
    if (this.readyState === WebSocket.CONNECTING && !this.connectingAbortHandled) {
      this.connectingAbortHandled = true;
      this.once("error", (error: Error) => {
        if (error.message !== "WebSocket was closed before the connection was established")
          throw error;
      });
    }
    super.close(code, data);
  }
}
