import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Mock Canvas API for jsdom
// @ts-expect-error - simplified mock for tests
HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
  fillRect: vi.fn(),
  clearRect: vi.fn(),
  getImageData: vi.fn(() => ({ data: new Array(4) })),
  putImageData: vi.fn(),
  createImageData: vi.fn(() => ({ data: new Array(4) })),
  setTransform: vi.fn(),
  drawImage: vi.fn(),
  save: vi.fn(),
  fillText: vi.fn(),
  restore: vi.fn(),
  beginPath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  closePath: vi.fn(),
  stroke: vi.fn(),
  translate: vi.fn(),
  scale: vi.fn(),
  rotate: vi.fn(),
  arc: vi.fn(),
  fill: vi.fn(),
  measureText: vi.fn(() => ({ width: 0 })),
  transform: vi.fn(),
  rect: vi.fn(),
  clip: vi.fn(),
} as unknown as CanvasRenderingContext2D));

// Mock window.scrollTo
Object.defineProperty(window, "scrollTo", {
  value: vi.fn(),
  writable: false,
  configurable: true
});

// Mock window.matchMedia
Object.defineProperty(window, "matchMedia", {
  value: vi.fn((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
  writable: false,
  configurable: true
});

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
