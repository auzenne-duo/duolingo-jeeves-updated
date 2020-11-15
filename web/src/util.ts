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
    c => "%" + c.charCodeAt(0).toString(16),
  );

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
