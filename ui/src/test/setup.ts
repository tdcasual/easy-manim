import "@testing-library/jest-dom/vitest";

class _MemoryStorage implements Storage {
  #items = new Map<string, string>();

  get length(): number {
    return this.#items.size;
  }

  clear(): void {
    this.#items.clear();
  }

  getItem(key: string): string | null {
    return this.#items.has(key) ? (this.#items.get(key) as string) : null;
  }

  key(index: number): string | null {
    return Array.from(this.#items.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.#items.delete(key);
  }

  setItem(key: string, value: string): void {
    this.#items.set(key, String(value));
  }
}

// Some environments (or node flags) can produce a partial localStorage implementation.
// Ensure a stable, in-memory implementation for unit tests.
Object.defineProperty(globalThis, "localStorage", {
  value: new _MemoryStorage(),
  writable: false,
  configurable: true
});
