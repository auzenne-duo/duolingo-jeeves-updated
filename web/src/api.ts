import { format, formatISO } from "date-fns";

import { convertTimeZone } from "util";

const API_URL =
  process.env.NODE_ENV === "production"
    ? "/api/1"
    : "http://localhost:5000/api/1";

/** Converts a date and time to a format that the API supports. */
const formatDateTime = (date: Date) => format(date, "yyyy-MM-dd'T'HH:mm:ssxx");

/** Converts a date to a format that the API supports. */
const formatLocalDate = (date: Date) =>
  formatISO(date, { representation: "date" });

const get = async (url: string) =>
  await (
    await fetch(`${API_URL}${url}`, {
      credentials: "include",
    })
  ).json();

export const getJiraDuplicates = async (
  issue_key: string,
): Promise<JSONAPI.Ticket[]> => {
  const data = (await get(
    `/detect_duplicates?issue_key=${encodeURIComponent(issue_key)}`,
  )) as JSONAPI.Ticket[];
  data.forEach(ticket => loadTicketMetadata(ticket));
  return data;
};

export const getInfo = async (
  lang: JSONAPI.LanguageId,
): Promise<{
  deployed_timestamp: Date;
  initialized_timestamp: Date;
  latest_ticket_timestamp: Date;
}> => {
  const data = (await get(`/${lang}/info`)) as JSONAPI.Info;
  return {
    deployed_timestamp: new Date(data.deployed_timestamp),
    initialized_timestamp: new Date(data.initialized_timestamp),
    latest_ticket_timestamp: new Date(data.latest_ticket_timestamp),
  };
};

export const getSpikes = async (
  lang: JSONAPI.LanguageId,
  {
    end_date,
    spike_category,
    start_date,
  }: {
    end_date?: Date;
    spike_category?: JSONAPI.SpikeCategory;
    start_date?: Date;
  } = {},
): Promise<
  {
    date: Date;
    spikes: [number, string][];
  }[]
> => {
  const params = new URLSearchParams();

  // Spike detection is precomputed and does not support specifying a time zone.
  end_date && params.set("end_date", formatLocalDate(end_date));
  spike_category && params.set("spike_category", spike_category);
  start_date && params.set("start_date", formatLocalDate(start_date));

  const data = (await get(
    `/${lang}/spikes?${params.toString()}`,
  )) as JSONAPI.Spikes;

  return Object.entries(data).map(([date, value]) => ({
    // Spikes are actually computed on EST date grouping, but
    // for simplicity we pretend that they are local date groups
    // in the UI.
    date: new Date(`${date} 00:00:00`),
    spikes: value?.spike ?? [],
  }));
};

export const getTickets = async (
  lang: JSONAPI.LanguageId,
  {
    beta_filter,
    end_time,
    limit,
    page,
    start_time,
    word,
  }: {
    beta_filter?: JSONAPI.ShakeToReportCategory;
    end_time?: Date;
    limit?: number;
    page?: number;
    start_time?: Date;
    word?: string;
  } = {},
): Promise<JSONAPI.Tickets> => {
  const params = new URLSearchParams();

  beta_filter && params.set("beta_filter", beta_filter);
  end_time && params.set("end_time", formatDateTime(end_time));
  limit && params.set("limit", `${limit}`);
  page && params.set("page", `${page}`);
  start_time && params.set("start_time", formatDateTime(start_time));
  word && params.set("word", word);

  const data = (await get(
    `/${lang}/tickets?${params.toString()}`,
  )) as JSONAPI.Tickets;
  data.data.forEach(ticket => loadTicketMetadata(ticket));

  return data;
};

export const getTimeSeries = async (
  lang: JSONAPI.LanguageId,
  {
    word,
  }: {
    word: string;
  },
): Promise<
  {
    date: Date;
    value: number;
  }[]
> => {
  const data = ((await get(
    `/${lang}/time_series?word=${word}`,
  )) as JSONAPI.TimeSeries).values;
  return Object.entries(data).map(([date, value]) => ({
    date: convertTimeZone(new Date(`${date} 00:00:00`), "America/New_York"),
    value: value ?? 0,
  }));
};

// TODO: move this to the backend.
const loadTicketMetadata = (ticket: JSONAPI.Ticket) => {
  try {
    const d = ticket.beta_feedback_metadata;
    const app_version =
      d?.app_information?.app_version_code ??
      d?.system_information?.app_version;
    const course =
      d?.app_information?.course ??
      d?.user_information?.current_course?.split(" ")[0];
    const full_story_url =
      d?.fullstory && d?.fullstory !== "No session recorded"
        ? d.fullstory.replace("- session url: ", "")
        : (d?.session_information?.fullstory_session ??
            d?.session_information?.fullstory_session_if_recording) !==
          "unavailable"
        ? d?.session_information?.fullstory_session ??
          d?.session_information?.fullstory_session_if_recording
        : undefined;
    const os_version =
      d?.system_information?.ios_version ??
      d?.app_information?.os ??
      d?.app_information?.os_version;
    const platform = (() => {
      if (d?.app_information) {
        return d.app_information.api_level ? "android" : "web";
      }
      if (d?.system_information) {
        return "ios";
      }
      for (const tag of ticket.tags ?? []) {
        switch (tag) {
          case "android":
          case "androidapp":
          case "bug_report_android":
            return "android";
          case "bug_report_web":
            return "web";
          case "bug_report_ios":
          case "device_type__ios":
          case "iphone":
          case "iphoneapp":
            return "ios";
        }
      }
    })();
    const screen = d?.app_information?.screen ?? d?.system_information?.screen;
    const screen_name =
      d?.session_information?.activity?.replace("com.duolingo.", "") ??
      d?.session_information?.url?.replace(
        /https:\/\/(.+\.)?duolingo\.com/,
        "",
      ) ??
      d?.view_controller_name;
    const ui_language = d?.system_information?.ui_language;
    const username =
      d?.app_information?.username ?? d?.user_information?.username;
    ticket.metadata = {
      app_version,
      course,
      full_story_url,
      os_version,
      platform,
      raw: "",
      screen,
      screen_name,
      ui_language,
      username,
    };
  } catch (ex) {
    console.error(ex);
  }
};
