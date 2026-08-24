/**
 * Auth lifecycle:
 *   restoring → authenticated
 *   restoring → unauthenticated
 *   restoring → restore_failed (bounded timeout / unexpected stall)
 */
export type AuthStatus = "restoring" | "authenticated" | "unauthenticated" | "restore_failed";
