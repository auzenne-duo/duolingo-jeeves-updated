import Cookies from "js-cookie";

const BEARER = `Bearer ${process.env.DUOLINGO_JWT ?? Cookies.get("jwt_token")}`;

export const get = async <T>(url: string, throwError = true): Promise<T> => {
  const response = await fetch(resolveUrl(url), {
    credentials: "include",
    headers: [["Authorization", BEARER]],
  });
  if (!response.ok && throwError) {
    throw Error(`Request failed with status ${response.status}`);
  }
  return response.json();
};

export const getBlob = async (
  url: string,
  throwError = true,
): Promise<Blob> => {
  const response = await fetch(resolveUrl(url));
  if (!response.ok && throwError) {
    throw Error(`Request failed with status ${response.status}`);
  }
  return response.blob();
};

export const patch = async <T>(
  url: string,
  data = {},
  throwError = true,
): Promise<T> => post(url, data, "PATCH", throwError);

export const post = async <T>(
  url: string,
  data = {},
  method = "POST",
  throwError = true,
): Promise<T> => {
  const response = await fetch(resolveUrl(url), {
    body: data instanceof FormData ? data : JSON.stringify(data),
    credentials: "include",
    headers: [
      ["Authorization", BEARER],
      ...(data instanceof FormData
        ? // The browser should set this.
          []
        : [["Content-Type", "application/json"]]),
    ] as [string, string][],
    method,
  });
  if (!response.ok && throwError) {
    throw Error(`Request failed with status ${response.status}`);
  }
  return response.json();
};

const resolveUrl = (url: string) =>
  /^https?:/.test(url) ? url : `${process.env.API}${url}`;
