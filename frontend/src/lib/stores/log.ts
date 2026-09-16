import { writable } from 'svelte/store';

export interface LogEntry {
  time: string;
  level: string;
  message: string;
}

export const logStore = writable<LogEntry[]>([]);