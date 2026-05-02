import enMessages from "./en-US.json";
import zhMessages from "./zh-CN.json";

export type Locale = "zh-CN" | "en-US";
export type MessageParams = Record<string, number | string | null | undefined>;
export type Messages = Record<string, string | string[]>;

const BASE_MESSAGES: Record<Locale, Messages> = {
  "zh-CN": zhMessages as Messages,
  "en-US": enMessages as Messages,
};

// Plural overrides that cannot be expressed in plain JSON
const PLURAL_OVERRIDES: Partial<Record<Locale, Record<string, (params: MessageParams) => string>>> =
  {
    "en-US": {
      "studio.history.count": ({ count }) =>
        Number(count) === 1 ? "1 creation" : `${count ?? 0} creations`,
    },
  };

export function getMessages(locale: Locale): Messages {
  return BASE_MESSAGES[locale];
}

export function getPluralOverride(
  locale: Locale
): Record<string, (params: MessageParams) => string> | undefined {
  return PLURAL_OVERRIDES[locale];
}
