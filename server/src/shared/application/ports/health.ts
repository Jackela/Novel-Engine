/**
 * Health probe port: the injectable seam through which the composition root
 * reports runtime dependency status. #264 wires the real SQLite probe here;
 * until then the app runs with an empty default probe and stays ready.
 */

export type HealthStatus = "healthy" | "unhealthy";

export interface HealthComponent {
  name: string;
  status: HealthStatus;
  message?: string;
  error?: string;
}

export interface HealthReport {
  components: HealthComponent[];
}

export type HealthProbe = () => Promise<HealthReport>;
