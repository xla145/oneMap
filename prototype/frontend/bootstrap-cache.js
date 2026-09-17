// Page-memory only: never persist account data in browser storage.
export function createBootstrapCache({ttl = 30000, now = Date.now} = {}) {
  const entries = new Map();
  return {
    invalidate() { entries.clear(); },
    async get(key, fetcher, {force = false} = {}) {
      let entry = entries.get(key);
      if (!entry || (!entry.pending && (force || now() - entry.at >= ttl))) {
        entry = {pending: null, at: 0, value: null};
        entries.set(key, entry);
        entry.pending = Promise.resolve().then(fetcher).then(value => {
          entry.value = value;
          entry.at = now();
          entry.pending = null;
          return value;
        }, error => {
          if (entries.get(key) === entry) entries.delete(key);
          throw error;
        });
      }
      const value = entry.pending ? await entry.pending : entry.value;
      // Return a private copy: editors may mutate the displayed state.
      return JSON.parse(JSON.stringify(value));
    },
  };
}
