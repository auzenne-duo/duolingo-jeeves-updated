import { convertTimeZone } from "util";

import { format, formatISO, parseISO } from "date-fns";

import { get, patch } from "api/client";
import { transformQuery } from "elastic";

/** Converts a date and time to a format that the API supports. */
const formatDateTime = (date: Date) => format(date, "yyyy-MM-dd'T'HH:mm:ssxx");

/** Converts a date to a format that the API supports. */
const formatLocalDate = (date: Date) =>
  formatISO(date, { representation: "date" });

export const getInfo = async (
  lang: JSONAPI.LanguageId,
): Promise<{
  deployed_timestamp: Date;
  initialized_timestamp: Date;
  latest_ticket_timestamp: Date;
}> => {
  const data = await get<JSONAPI.Info>(`/1/${lang}/info`);
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
    spikes: JSONAPI.SpikeWord[];
  }[]
> => {
  const params = new URLSearchParams();

  // Spike detection is precomputed and does not support specifying a time zone.
  end_date && params.set("end_date", formatLocalDate(end_date));
  spike_category && params.set("spike_category", spike_category);
  start_date && params.set("start_date", formatLocalDate(start_date));

  const data = await get<JSONAPI.Spikes>(
    `/1/${lang}/spikes?${params.toString()}`,
  );

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
  const data = (
    await get<JSONAPI.Tickets>(
      `/1/${lang}/tickets?jeeves_id=${encodeURIComponent(id)}`,
    )
  ).data[0];
  if (!data) {
    throw Error("Ticket not found.");
  }
  return data;
};

export const getTickets = (
  lang: JSONAPI.LanguageId,
  {
    areas,
    beta_filter,
    end_time,
    limit,
    page,
    start_time,
    word,
  }: {
    areas: JSONAPI.Area[];
    beta_filter?: JSONAPI.ShakeToReportCategory;
    end_time?: Date;
    limit?: number;
    page?: number;
    start_time?: Date;
    word?: string;
  },
) => {
  const params = new URLSearchParams();

  beta_filter && params.set("beta_filter", beta_filter);
  end_time && params.set("end_time", formatDateTime(end_time));
  limit && params.set("limit", `${limit}`);
  page && params.set("page", `${page}`);
  start_time && params.set("start_time", formatDateTime(start_time));
  word && params.set("word", transformQuery(word, areas));

  return get<JSONAPI.Tickets>(`/1/${lang}/tickets?${params.toString()}`);
};

export const getTimeSeries = async (
  lang: JSONAPI.LanguageId,
  {
    areas,
    word,
  }: {
    areas: JSONAPI.Area[];
    word: string;
  },
): Promise<
  {
    date: Date;
    value: number;
  }[]
> => {
  const data = (
    await get<JSONAPI.TimeSeries>(
      `/1/${lang}/time_series?word=${encodeURIComponent(
        transformQuery(word, areas),
      )}`,
    )
  ).values;
  return Object.entries(data).map(([date, value]) => ({
    date: convertTimeZone(parseISO(`${date}T00:00:00`), "America/New_York"),
    value: value ?? 0,
  }));
};

export const setSpikeConfirmed = async (
  spike_id: string,
  desired_state: boolean,
) =>
  patch<boolean>("/1/set_spike_confirm", {
    spike_id: spike_id,
    desired_state: desired_state,
  });
