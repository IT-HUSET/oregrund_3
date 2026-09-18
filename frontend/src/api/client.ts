import type { BomGroupsResponse, BomResponse, PurchaseOrderResponse } from './types'

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

export function getPurchaseOrder(): Promise<PurchaseOrderResponse> {
  return getJson('/api/purchase-order')
}
