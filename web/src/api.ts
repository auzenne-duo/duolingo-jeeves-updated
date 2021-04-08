import { format, formatISO, parseISO } from "date-fns";

import { convertTimeZone } from "util";

const API_URL =
  process.env.NODE_ENV === "production"
    ? "/api/1"
    : "http://localhost:5000/api/1";

export const createJira = async ({
  description,
  generated_description,
  project,
  summary,
}: {
  pre_release?: boolean;
  description: string;
  feature?: string;
  generated_description?: string;
  project: "DLAA" | "DLAI" | "DLAW";
  reporter_email?: string;
  summary: string;
}) => {
  const formData = new FormData();
  formData.set(
    "issueData",
    JSON.stringify({
      description,
      generatedDescription: generated_description,
      project,
      summary,
    }),
  );
  return (await post("/shakira/report_issue", formData)) as {
    issueKey: string;
    url: string;
  };
};

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

const post = async (url: string, data = {}) =>
  await (
    await fetch(`${API_URL}${url}`, {
      body: data instanceof FormData ? data : JSON.stringify(data),
      credentials: "include",
      headers:
        data instanceof FormData
          ? // The browser should set this.
            {}
          : { "Content-Type": "application/json" },
      method: "POST",
    })
  ).json();

export const getJiraDuplicates = async (
  issue_key: string,
): Promise<JSONAPI.Ticket[]> =>
  (await get(
    `/detect_duplicates?issue_key=${encodeURIComponent(issue_key)}`,
  )) as JSONAPI.Ticket[];

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
    date: parseISO(`${date}T00:00:00`),
    spikes: value?.spike ?? [],
  }));
};

export const getTicket = async (
  lang: JSONAPI.LanguageId,
  id: string,
): Promise<JSONAPI.Ticket | undefined> => {
  const data = ((await get(
    `/${lang}/tickets?jeeves_id=${encodeURIComponent(id)}`,
  )) as JSONAPI.Tickets).data[0];
  if (!data) {
    throw Error("Ticket not found.");
  }
  return data;
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

  return (await get(
    `/${lang}/tickets?${params.toString()}`,
  )) as JSONAPI.Tickets;
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
    date: convertTimeZone(parseISO(`${date}T00:00:00`), "America/New_York"),
    value: value ?? 0,
  }));
};
