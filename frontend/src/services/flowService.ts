/**
 * Flow Service
 * Handles API calls for NiFi flow management
 */

import { apiRequest } from '@/utils/api';

export interface Flow {
  id: number;
  flow_name: string;
  bucket_name: string;
  registry_name: string;
  version: number;
  flow_id: string;
  bucket_id: string;
  src_connection_param?: string;
  dest_connection_param?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Get all flows
 */
export async function getFlows(): Promise<Flow[]> {
  return apiRequest<Flow[]>('/api/nifi-flows');
}

/**
 * Get a single flow by ID
 */
export async function getFlow(flowId: number): Promise<Flow> {
  return apiRequest<Flow>(`/api/nifi-flows/${flowId}`);
}

export const flowService = {
  getFlows,
  getFlow,
};
