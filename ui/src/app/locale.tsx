import { useEffect, useMemo, useSyncExternalStore } from "react";
import {
  getMessages,
  getPluralOverride,
  type Locale,
  type MessageParams,
  type Messages,
} from "../locales";

export type { Locale, MessageParams } from "../locales";
type MessageValue = string | string[] | ((params: MessageParams) => string);

const DEFAULT_LOCALE: Locale = "zh-CN";
const LOCALE_KEY = "easy_manim_locale";
const listeners = new Set<() => void>();

const BASE_MESSAGES: Record<Locale, Messages> = {
  "zh-CN": getMessages("zh-CN"),
  "en-US": getMessages("en-US"),
};

function buildMessages(locale: Locale): Record<string, MessageValue> {
  const base = BASE_MESSAGES[locale];
  const plural = getPluralOverride(locale);
  if (!plural) return base as Record<string, MessageValue>;
  return { ...base, ...plural } as Record<string, MessageValue>;
}

const MESSAGES: Record<Locale, Record<string, MessageValue>> = {
  "zh-CN": buildMessages("zh-CN"),
  "en-US": buildMessages("en-US"),
};

function isLocale(value: string | null): value is Locale {
  return value === "zh-CN" || value === "en-US";
}

function readLocaleFromStorage(): Locale {
  if (typeof window === "undefined") return DEFAULT_LOCALE;

  try {
    const stored = window.localStorage.getItem(LOCALE_KEY);
    return isLocale(stored) ? stored : DEFAULT_LOCALE;
  } catch {
    return DEFAULT_LOCALE;
  }
}

function emitLocaleChange() {
  for (const listener of Array.from(listeners)) listener();
}

function resolveMessage(locale: Locale, key: string): MessageValue | undefined {
  return MESSAGES[locale][key] ?? MESSAGES[DEFAULT_LOCALE][key];
}

function interpolate(template: string, params: MessageParams = {}): string {
  return template.replace(/\{(\w+)\}/g, (_, token: string) => {
    const value = params[token];
    return value === null || value === undefined ? "" : String(value);
  });
}

export function readLocale(): Locale {
  return readLocaleFromStorage();
}

export function writeLocale(locale: Locale): void {
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(LOCALE_KEY, locale);
    } catch {
      // Ignore storage write failures and keep the in-memory update path.
    }
  }
  emitLocaleChange();
}

export function subscribeLocale(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function translate(locale: Locale, key: string, params: MessageParams = {}): string {
  const value = resolveMessage(locale, key);
  if (!value) return key;
  if (typeof value === "function") return value(params);
  if (Array.isArray(value)) return value.join(", ");
  return interpolate(value, params);
}

export function translateList(locale: Locale, key: string): string[] {
  const value = resolveMessage(locale, key);
  return Array.isArray(value) ? value : [];
}

export function syncDocumentLocale(locale: Locale): void {
  if (typeof document === "undefined") return;
  document.documentElement.lang = locale;
  document.title = translate(locale, "app.meta.title");
}

export function useI18n() {
  const locale = useSyncExternalStore(subscribeLocale, readLocale, () => DEFAULT_LOCALE);

  return useMemo(
    () => ({
      locale,
      setLocale: writeLocale,
      t: (key: string, params?: MessageParams) => translate(locale, key, params),
      list: (key: string) => translateList(locale, key),
    }),
    [locale]
  );
}

export function useLocaleDocument() {
  const locale = useSyncExternalStore(subscribeLocale, readLocale, () => DEFAULT_LOCALE);

  useEffect(() => {
    syncDocumentLocale(locale);
  }, [locale]);
}
