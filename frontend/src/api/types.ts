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
  /**
   * True om detta bara är ett segment av en kapbit som är längre än längsta handelslängden
   * (5400 mm) och därför skarvas ur flera inköpta stänger. Se GroupCuttingResult.splices.
   */
  spliced?: boolean
  /** 1-baserat segmentnummer, satt endast när spliced är true. */
  segment_index?: number | null
  /** Totalt antal segment kapbiten är byggd av, satt endast när spliced är true. */
  segment_count?: number | null
}

export interface Bar {
  purchase_length_mm: number
  cuts: Cut[]
  used_length_mm: number
  kerf_total_mm: number
  waste_mm: number
}

/**
 * Aggregat för en kapbit (oid) som är skarvad ur flera inköpta längder. Validerar bara
 * materialtäckning/spill, inte var skarven strukturellt får sitta (docs/prd.md §4, medveten
 * avgränsning). Ingen extra kerf modelleras för skarven själv -- varje segments kerf räknas
 * redan i dess Bar.kerf_total_mm.
 */
export interface Splice {
  oid: string
  /** Kapbitens fulla behovslängd, samma som i FramePiece.length_mm. */
  total_length_mm: number
  segment_count: number
  /** Inköpta längder biten byggs av. */
  purchase_lengths_mm: number[]
  /** segment_count - 1. */
  joint_count: number
}

export interface GroupCuttingResult {
  code: string
  mat_code: string
  waste_percent: number
  bars: Bar[]
  /** En rad per skarvat oid i gruppen. */
  splices: Splice[]
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
  /** Antal oid som behövde skarvas. */
  spliced_piece_count: number
  /** Summa joint_count över alla splices. */
  total_joints: number
}

export interface PurchaseOrderResponse {
  kerf_mm: number
  groups: GroupCuttingResult[]
  order_lines: PurchaseOrderLine[]
  summary: PurchaseOrderSummary
}
