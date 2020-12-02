/**
 * Encodes URLSearchParams using encodeURIComponent instead of
 * application/x-www-form-urlencoded, for consistency.
 */
export const encodeURLSearchParams = (params: URLSearchParams) =>
  [...params.entries()]
    .map(
      ([key, value]) =>
        `${fixedEncodeURIComponent(key)}=${fixedEncodeURIComponent(value)}`,
    )
    .join("&");

export const escapeHTML = (unsafe: string) =>
  unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");

/** https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/encodeURIComponent */
const fixedEncodeURIComponent = (str: string) =>
  encodeURIComponent(str).replace(
    /[!'()*]/g,
    c => "%" + c.charCodeAt(0).toString(16),
  );

export const formatCourseId = (courseId: string) =>
  courseId.slice("DUOLINGO_".length).split(" ")[0].replace("_", "<");

export const formatPlatform = (platform: "android" | "ios" | "web") =>
  platform === "android"
    ? "Android"
    : platform === "ios"
    ? "iOS"
    : platform === "web"
    ? "Web"
    : "";

export const getPaginationString = ({
  page,
  perPage,
  total,
}: {
  page: number;
  perPage: number;
  total: number | undefined;
}) =>
  total
    ? `${(page - 1) * perPage + 1}-${Math.min(
        page * perPage,
        total,
      )} of ${total}`
    : undefined;

/**
 * Tries to highlight all instances of a word in the text.
 * Returns the original text if highlighting failed, for
 * example because the generated regex pattern is invalid.
 */
export const highlightWord = (str: string, word: string) => {
  try {
    return str.replace(RegExp(`\\b(${word})\\b`, "gi"), "<mark>$1</mark>");
  } catch {
    return str;
  }
};

export const normalizeNewLines = (str: string) =>
  str
    .replace(/\r\n/g, "\n")
    .replace(/\n\s+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n");

/** Removes the time portion of a Date. */
export const midnight = (date: Date) =>
  new Date(date.getFullYear(), date.getMonth(), date.getDate());
