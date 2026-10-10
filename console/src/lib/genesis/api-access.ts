// Session memory only; never put usage credentials in persisted settings.
let accessToken = "";
export function setApiAccessToken(token: string) { accessToken = token.trim(); if (typeof window !== "undefined") window.dispatchEvent(new Event("genesis-api-access-changed")); }
export function authorizedFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return fetch(input, {...init, headers});
}
