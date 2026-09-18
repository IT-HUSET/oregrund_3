/**
 * TypeScript-spegel av backend/app/models.py.
 *
 * Detta är, tillsammans med docs/api-contract.md, den bindande kontraktsdefinitionen mellan
 * backend och frontend (docs/adr.md ADR-1). Ändras ett fält i backend/app/models.py: uppdatera
 * docs/api-contract.md och denna fil i samma commit -- inget delar typerna automatiskt.
 *
 * Alla längder/mått är i mm.
 */

// --- GET /api/bom (inkrement 1) ---------------------------------------------------------

export interface FramePiece {
  /** FRAMEPIECE OID. Matchar IFCBEAM.Tag i .ifc-filen 1:1 -- nyckeln för 3D-highlight. */
  oid: string
  item_id: string | null
  /** Tvärsnittskod, t.ex. "45x182". */
  code: string
  width_mm: number
  height_mm: number
  length_mm: number
  /** Hållfasthetsklass, t.ex. C24, C16, C14, GL. */
  mat_code: string
  module_name: string | null
  module_flat: string | null
  use: string
  bom_phase: string | null
}

export interface BomResponse {
  count: number
  items: FramePiece[]
}

// --- GET /api/bom/groups (inkrement 2) --------------------------------------------------

export interface GroupedPiece {
  oid: string
  length_mm: number
}

export interface BomGroup {
  code: string
  mat_code: string
  piece_count: number
  total_length_mm: number
  pieces: GroupedPiece[]
  available_trade_lengths_mm: number[]
}

export interface BomGroupsResponse {
  groups: BomGroup[]
}

// --- GET /api/purchase-order (inkrement 3, underlag för inkrement 4) --------------------

export interface Cut {
  /** Samma oid som i FramePiece.oid -- vad inkrement 4 slår upp mot IFC Tag. */
  oid: string
  length_mm: number
}

export interface Bar {
  purchase_length_mm: number
  cuts: Cut[]
  used_length_mm: number
  kerf_total_mm: number
  waste_mm: number
}

export interface GroupCuttingResult {
  code: string
  mat_code: string
  waste_percent: number
  bars: Bar[]
}

export interface PurchaseOrderLine {
  code: string
  mat_code: string
  purchase_length_mm: number
  quantity: number
  article_number: string
  price_per_unit_sek: number
  lead_time_days: number
  total_price_sek: number
}

export interface PurchaseOrderSummary {
  total_bars: number
  total_needed_length_mm: number
  total_purchased_length_mm: number
  total_waste_percent: number
  total_cost_sek: number
}

export interface PurchaseOrderResponse {
  kerf_mm: number
  groups: GroupCuttingResult[]
  order_lines: PurchaseOrderLine[]
  summary: PurchaseOrderSummary
}
