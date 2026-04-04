import { writable } from 'svelte/store';

const SPA_BASE = '/app';

function normalizePath(pathname: string): string {
  if (!pathname) {
    return '/';
  }

  let normalized = pathname;
  if (normalized.startsWith(SPA_BASE)) {
    normalized = normalized.slice(SPA_BASE.length) || '/';
  }

  if (!normalized.startsWith('/')) {
    normalized = `/${normalized}`;
  }

  if (normalized.length > 1 && normalized.endsWith('/')) {
    normalized = normalized.slice(0, -1);
  }

  return normalized || '/';
}

export const route = writable(normalizePath(window.location.pathname));

export function href(path: string): string {
  const normalized = normalizePath(path);
  return normalized === '/' ? SPA_BASE : `${SPA_BASE}${normalized}`;
}

export function navigate(path: string, options: { replace?: boolean } = {}): void {
  const destination = href(path);
  const method = options.replace ? 'replaceState' : 'pushState';
  window.history[method]({}, '', destination);
  route.set(normalizePath(window.location.pathname));
}

window.addEventListener('popstate', () => {
  route.set(normalizePath(window.location.pathname));
});
