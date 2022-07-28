import Cookies from "js-cookie";

import { get } from "api/client";

const API_ORIGIN = "https://www.duolingo.com/2017-06-30";

const USER_FIELDS = ["email", "username"].join(",");

export const getLoggedIn = () => {
  const loggedInUserId = getLoggedInUserId();
  if (loggedInUserId) {
    // This can be called without authentication but that returns a limited set of fields.
    return get<Monolith.User>(
      `${API_ORIGIN}/users/${loggedInUserId}?fields=${USER_FIELDS}`,
    );
  }
  throw Error("User is not logged in");
};

export const getLoggedInUserId = () => {
  const jwt = process.env.DUOLINGO_JWT ?? Cookies.get("jwt_token");
  const jwtUserId = jwt ? parseUserId(jwt) : undefined;
  if (!jwtUserId) {
    throw Error("JWT missing");
  }
  return jwtUserId;
};

export const getUser = (userId: number) =>
  get<Monolith.User>(`${API_ORIGIN}/users/${userId}?fields=${USER_FIELDS}`);

const parseUserId = (jwt: string) => {
  try {
    return Number(JSON.parse(atob(jwt.split(".")[1])).sub);
  } catch (ex) {
    return undefined;
  }
};
