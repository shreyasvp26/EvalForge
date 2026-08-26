export type OAuthProvider = "google" | "github";

export function buildOAuthAuthorizeUrl(
  provider: OAuthProvider,
  nextPath: string,
  apiBaseUrl: string,
): string {
  const params = new URLSearchParams();
  if (nextPath && nextPath !== "/") {
    params.set("next", nextPath);
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return `${apiBaseUrl.replace(/\/$/, "")}/v1/auth/${provider}/authorize${suffix}`;
}
