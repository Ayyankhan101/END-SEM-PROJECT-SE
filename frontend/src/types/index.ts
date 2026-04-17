/**
 * Type definitions for DockWatch frontend
 */

// Container types
export interface Container {
  id: string;
  name: string;
  image: string;
  status: string;
  created?: string;
  state?: ContainerState;
  created_at?: string;
  last_updated?: string;
}

export interface ContainerState {
  Status?: string;
  Running?: boolean;
  Paused?: boolean;
  Restarting?: boolean;
  OOMKilled?: boolean;
  Dead?: boolean;
  Pid?: number;
  ExitCode?: number;
  Error?: string;
  StartedAt?: string;
  FinishedAt?: string;
  Health?: HealthState;
}

export interface HealthState {
  Status: string;
  FailingStreak?: number;
  Log?: HealthLogEntry[];
}

export interface HealthLogEntry {
  Start: string;
  End: string;
  ExitCode: number;
  Output: string;
}

export interface ContainerDetail extends Container {
  metrics: Metric[];
  alerts: Alert[];
  config?: ContainerConfig;
  network_settings?: NetworkSettings;
}

export interface ContainerConfig {
  Hostname?: string;
  Domainname?: string;
  User?: string;
  AttachStdin?: boolean;
  AttachStdout?: boolean;
  AttachStderr?: boolean;
  Tty?: boolean;
  OpenStdin?: boolean;
  StdinOnce?: boolean;
  Env?: string[];
  Cmd?: string[];
  Image?: string;
  Volumes?: Record<string, unknown>;
  WorkingDir?: string;
  Entrypoint?: string[];
  OnBuild?: string[];
  Labels?: Record<string, string>;
}

export interface NetworkSettings {
  Bridge?: string;
  SandboxID?: string;
  HairpinMode?: boolean;
  LinkLocalIPv6Address?: string;
  LinkLocalIPv6PrefixLen?: number;
  Ports?: Record<string, PortBinding[]>;
  SandboxKey?: string;
  SecondaryIPAddresses?: IPAddress[];
  SecondaryIPv6Addresses?: IPAddress[];
  EndpointID?: string;
  Gateway?: string;
  GlobalIPv6Address?: string;
  GlobalIPv6PrefixLen?: number;
  IPAddress?: string;
  IPPrefixLen?: number;
  IPv6Gateway?: string;
  MacAddress?: string;
  Networks?: Record<string, NetworkInfo>;
}

export interface PortBinding {
  HostIp?: string;
  HostPort?: string;
}

export interface IPAddress {
  Addr?: string;
  PrefixLen?: number;
}

export interface NetworkInfo {
  IPAMConfig?: IPAMConfig;
  Links?: string[];
  Aliases?: string[];
  NetworkID?: string;
  EndpointID?: string;
  Gateway?: string;
  IPAddress?: string;
  IPPrefixLen?: number;
  IPv6Gateway?: string;
  GlobalIPv6Address?: string;
  GlobalIPv6PrefixLen?: number;
  MacAddress?: string;
}

export interface IPAMConfig {
  IPv4Address?: string;
  IPv6Address?: string;
  LinkLocalIPs?: string[];
}

// Metric types
export interface Metric {
  id: number;
  container_id: string;
  cpu_percent?: number;
  memory_percent?: number;
  memory_usage?: number;
  timestamp?: string;
}

export interface MetricsHistory {
  container_id?: string;
  metrics: Metric[];
}

// Alert types
export interface Alert {
  id: number;
  container_id: string;
  alert_type: string;
  message: string;
  severity: string;
  timestamp?: string;
}

export type AlertSeverity = 'info' | 'warning' | 'critical';

// Recovery action types
export interface RecoveryAction {
  id: number;
  container_id: string;
  action_type: string;
  status: string;
  timestamp?: string;
}

// Stack types
export interface Stack {
  id: number;
  name: string;
  compose_file: string;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface StackCreate {
  name: string;
  compose_file: string;
}

// Host types
export interface Host {
  id: number;
  name: string;
  socket_path: string;
  api_version: string;
  status: string;
  last_seen?: string;
}

export interface HostCreate {
  name: string;
  socket_path?: string;
  api_version?: string;
}

// User types
export interface User {
  id: number;
  username: string;
  created_at?: string;
  updated_at?: string;
  must_change_password?: boolean;
}

// Auth types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// Settings types
export interface Settings {
  poll_interval: number;
  cpu_threshold: number;
  memory_threshold: number;
  metrics_ttl_days: number;
  recovery_enabled: boolean;
  jwt_expiration_hours: number;
}

export interface SettingsUpdate {
  poll_interval?: number;
  cpu_threshold?: number;
  memory_threshold?: number;
  metrics_ttl_days?: number;
  recovery_enabled?: boolean;
}

// API Response types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  details?: Record<string, unknown>;
  status_code?: number;
}

// WebSocket types
export interface WebSocketMessage {
  type: 'metrics' | 'container_update' | 'alert' | 'recovery' | 'ping' | 'pong';
  container_id?: string;
  container?: Container;
  stats?: Metric;
  alert_type?: string;
  message?: string;
  severity?: string;
  action_type?: string;
  status?: string;
  timestamp?: string;
}

// Container creation types
export interface ContainerCreateConfig {
  image: string;
  name: string;
  ports?: Record<string, number>;
  volumes?: Array<{
    host_path: string;
    container_path: string;
    mode?: string;
  }>;
  environment?: Record<string, string>;
  command?: string;
  memory_limit?: number;
  cpu_limit?: number;
}