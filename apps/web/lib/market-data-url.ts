function resolveApiOrigin(apiBase: string, origin?: string) {
  if (apiBase.startsWith("http://") || apiBase.startsWith("https://")) {
    return apiBase;
  }

  if (origin) {
    return new URL(apiBase, origin).toString();
  }

  const normalizedPath = apiBase.startsWith("/") ? apiBase : `/${apiBase}`;
  return `http://localhost:8000${normalizedPath}`;
}

export function resolveMarketStreamUrl(apiBase: string, origin?: string) {
  const url = new URL(resolveApiOrigin(apiBase, origin));
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/market/stream";
  url.search = "";
  return url.toString();
}
