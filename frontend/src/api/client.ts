import type {
  BomGroupsResponse,
  BomResponse,
  OptimizationAlgorithm,
  PurchaseOrderResponse,
} from './types'

/**
 * Tunn fetch-klient mot backend-API:et (se docs/api-contract.md). Vite-devservern proxyar
 * /api mot http://localhost:8000 (vite.config.ts) så relativa paths räcker här.
 */

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(`${path} svarade ${response.status}`)
  }
  return (await response.json()) as T
}

export function getBom(): Promise<BomResponse> {
  return getJson('/api/bom')
}

export function getBomGroups(): Promise<BomGroupsResponse> {
  return getJson('/api/bom/groups')
}

/**
 * `exact` tar sekunder till minuter (OR-Tools CP-SAT, docs/adr.md ADR-2-tillägget) och får bara
 * anropas på explicit användarval -- aldrig vid vanlig sidladdning (docs/api-contract.md).
 */
export function getPurchaseOrder(
  algorithm: OptimizationAlgorithm = 'greedy',
): Promise<PurchaseOrderResponse> {
  return getJson(`/api/purchase-order?algorithm=${algorithm}`)
}
