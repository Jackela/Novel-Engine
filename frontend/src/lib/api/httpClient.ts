import axios from 'axios';
import type { AxiosInstance, CreateAxiosDefaults } from 'axios';
import config from '@/config/env';

export type HttpClientOptions = Pick<
  CreateAxiosDefaults,
  'baseURL' | 'timeout' | 'withCredentials' | 'headers'
>;

export const createHttpClient = (options: HttpClientOptions = {}): AxiosInstance => {
  const baseURL = options.baseURL ?? (config.apiBaseUrl || '/');
  const timeout = options.timeout ?? config.apiTimeout;
  const withCredentials = options.withCredentials ?? true;

  return axios.create({
    baseURL,
    timeout,
    withCredentials,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  });
};

