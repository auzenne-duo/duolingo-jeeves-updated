import { format } from "date-fns";
import type { Location } from "history";

import { escapeTerm } from "opensearch";

const download = (blob: Blob, name: string) => {
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("download", name);
  link.setAttribute("href", url);
  link.click();
};

export const downloadAsCsv = (
  tickets: JSONAPI.Ticket[],
  lang: JSONAPI.LanguageId,
) => {
  const separator = ",";

  const keys: (keyof (typeof tickets)[0])[] = [];
  let k: keyof (typeof tickets)[0];
  for (k in tickets[0]) {
    if (Object.prototype.hasOwnProperty.call(tickets[0], k)) {
      keys.push(k);
    }
  }

  const csvHeader = ["jeeves_link"].concat(keys).join(separator);
  const csvRows = tickets
    .map(ticket => {
      const jeevesUrl = `https://jeeves.duolingo.com/${lang}/discovery?id=${ticket.jeeves_uid}`;
      return [jeevesUrl]
        .concat(
          keys.map(key => {
            let cell = ticket[key] ?? "";

            // Avoid calling toString on objects that result in [object Object]
            cell =
              cell instanceof Date
                ? cell.toLocaleString()
                : typeof cell === "object"
                  ? ""
                  : cell.toString().replace(/"/g, '""');

            if (cell.search(/("|,|\n)/g) >= 0) {
              cell = `"${cell}"`;
            }
            return cell;
          }),
        )
        .join(separator);
    })
    .join("\n");
  const csvContent = `${csvHeader}\n${csvRows}`;

  download(
    new Blob([csvContent], { type: "text/csv;charset=utf-8;" }),
    "jeeves_issues.csv",
  );
};

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

/** https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/encodeURIComponent */
const fixedEncodeURIComponent = (str: string) =>
  encodeURIComponent(str).replace(
    /[!'()*]/g,
    c => `%${c.charCodeAt(0).toString(16)}`,
  );

export const formatAttachment = (url: string) => {
  if (url.startsWith("https://duolingotest.zendesk.com/attachments/")) {
    return url.split("?name=")[1];
  }
  if (url.startsWith("https://duolingo.atlassian.net/")) {
    return url.split("/").slice(-1)[0];
  }
  return url;
};

export const formatCourseId = (courseId: string) => {
  if (courseId.startsWith("DUOLINGO_")) {
    return courseId.slice("DUOLINGO_".length).replace("_", "<");
  }
  return courseId;
};

export const formatPriority = (priority: JSONAPI.Priority) => {
  switch (priority) {
    // Zendesk priorities are lowercase.
    case "high":
      return "High";
    case "low":
      return "Low";
    case "normal":
      return "Normal";
    case "urgent":
      return "Urgent";
    default:
      return priority;
  }
};

export const formatReadableDate = (date: Date) =>
  format(date, "eee, d MMM yyyy");

export const formatReadableDateTime = (date: Date) =>
  format(date, "eee, d MMM yyyy HH:mm:ss z");

export const formatScreen = (screen: string) =>
  screen.startsWith("com.duolingo.")
    ? screen.replace("com.duolingo.", "")
    : screen.replace(/^https?:\/\/(.+\.)?duolingo\.com/, "");

export const getFilterLink = (
  location: Location,
  field: string,
  value: string,
) => {
  const params = new URLSearchParams(location.search);
  params.delete("page");
  params.delete("use-lemmas");
  params.delete("offset");
  params.delete("prev-sort-id");
  params.delete("sort-id");
  params.set("q", `${field}:"${escapeTerm(value, true)}"`);
  return {
    ...location,
    search: params.toString(),
  };
};

export const getPaginationString = ({
  offset,
  perPage,
  total,
}: {
  offset: number;
  perPage: number;
  total: number | undefined;
}) =>
  total
    ? `${offset + 1}-${Math.min(offset + perPage, total)} of ${total}`
    : undefined;

export const getUntruncatedTitle = (t: JSONAPI.Ticket) =>
  !t.header_text ||
  // Header text for tickets reported via the Zendesk mobile SDK
  // is often truncated after just a few characters.
  (t.data_source === "Zendesk" && t.via?.channel === "mobile_sdk") ||
  // Header text for tickets reported via Zendesk email often don't have descriptive headers
  (t.data_source === "Zendesk" &&
    t.via?.channel === "email" &&
    t.header_text.split(" ").length < 3)
    ? t.body_text?.trim().split(/\n|\.\s/)[0]
    : t.header_text;

export const isImage = (url: string) => /\.(png|jpe?g)$/.test(url);

export const normalizeNewLines = (str: string) =>
  str
    .replace(/\r\n/g, "\n")
    .replace(/\n\s+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n");

/**
 * Gets the shake-to-report category that corresponds
 * to a spike category, if there's a 1:1 mapping.
 */
export const spikeToStrCategory = (
  category: string,
): JSONAPI.ShakeToReportCategory | undefined => {
  // https://github.com/duolingo/duolingo-jeeves/blob/8ae6871a7cce0a2a5ac775d2aa6e4ea14310ebb9/jeeves/model/spike_categories.py#L37
  switch (category) {
    case "EXTERNAL_NON_STR_SPIKES":
      return "NON_STR_EXTERNAL";
    case "EXTERNAL_STR_SPIKES":
      return "EXTERNAL";
    case "INTERNAL_NON_STR_SPIKES":
      return "NON_STR_INTERNAL";
    case "INTERNAL_STR_SPIKES":
      return "INTERNAL";
    default:
      return undefined;
  }
};

/**
 * Compile time assert that the given value should be of type never. This is
 * useful for guaranteeing all cases are handled in a switch statement.
 */
export const staticAssertNever = (value: never) => value;

export const toDateString = (date: Date) => format(date, "yyyy-MM-dd");
