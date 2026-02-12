/**
 * Common TypeScript Types.
 *
 * Ref: .blueprint/data.md §4
 * - ID: UUID format
 * - Money: string (Decimal from backend)
 */

/** UUID string type (matches backend UUID fields) */
export type UUID = string;

/** ISO 8601 datetime string */
export type ISODateTime = string;

/** Decimal as string (from backend DecimalField) */
export type DecimalString = string;

/** Pagination metadata */
export interface PaginationMeta {
  count: number;
  next: string | null;
  previous: string | null;
}

/** Paginated response wrapper */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
