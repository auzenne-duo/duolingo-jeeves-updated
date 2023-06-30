import { format, formatISO, parseISO } from "date-fns";

import { convertTimeZone } from "../util";
import { get, patch, post } from "api/client";
import { transformQuery } from "opensearch";

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

export const getSpikeCategories = async (): Promise<
  JSONAPI.SpikeCategoryData[]
> => get<JSONAPI.SpikeCategoryData[]>("/1/spike_categories");

export const getSpikes = async (
  lang?: JSONAPI.LanguageId,
  {
    end_date,
    spike_category,
    start_date,
  }: {
    end_date?: Date;
    spike_category?: string;
    start_date?: Date;
  } = {},
): Promise<JSONAPI.SpikeDataResponse[]> => {
  const params = new URLSearchParams();

  // Spike detection is precomputed and does not support specifying a time zone.
  end_date && params.set("end_date", formatLocalDate(end_date));
  spike_category && params.set("spike_category", spike_category);
  start_date && params.set("start_date", formatLocalDate(start_date));

  const data = await get<JSONAPI.Spikes>(
    `/1/${lang ?? "ALL"}/spikes?${params.toString()}`,
  );

  return Object.entries(data).map(([date, value]) => ({
    // Spikes are actually computed on EST date grouping, but
    // for simplicity we pretend that they are local date groups
    // in the UI.
    date: parseISO(`${date}T00:00:00`),
    spikes: value?.spike ?? [],
  }));
};

export const getSpikeStats = async (
  lang: JSONAPI.LanguageId,
  {
    end_date,
    spike_category,
    start_date,
  }: {
    end_date?: Date;
    spike_category?: string;
    start_date?: Date;
  } = {},
): Promise<JSONAPI.SpikeStats> => {
  const params = new URLSearchParams();
  end_date && params.set("end_date", formatLocalDate(end_date));
  spike_category && params.set("spike_category", spike_category);
  start_date && params.set("start_date", formatLocalDate(start_date));

  const data = await get<JSONAPI.SpikeStats>(
    `/1/${lang}/spike_stats?${params.toString()}`,
  );

  return data;
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
    offset,
    prev_sort_id,
    sort_id,
    spike_category,
    start_time,
    use_lemmas,
    word,
  }: {
    areas: JSONAPI.Area[];
    beta_filter?: JSONAPI.ShakeToReportCategory;
    end_time?: Date;
    limit?: number;
    offset?: number; // offset is the index of the first displayed ticket
    prev_sort_id?: string;
    sort_id?: string;
    spike_category?: string;
    start_time?: Date;
    use_lemmas?: boolean;
    word?: string;
  },
) => {
  const params = new URLSearchParams();

  beta_filter && params.set("beta-filter", beta_filter);
  end_time && params.set("end_time", formatDateTime(end_time));
  limit && params.set("limit", `${limit}`);
  offset && params.set("offset", `${offset}`);
  prev_sort_id && params.set("prev-sort-id", prev_sort_id);
  sort_id && params.set("sort-id", sort_id);
  spike_category && params.set("spike-category", spike_category);
  start_time && params.set("start_time", formatDateTime(start_time));
  use_lemmas && params.set("use-lemmas", "true");
  word && params.set("word", transformQuery(word, areas));

  return get<JSONAPI.Tickets>(`/1/${lang}/tickets?${params.toString()}`);
};

export const getTimeSeries = async (
  lang: JSONAPI.LanguageId,
  {
    areas,
    beta_filter,
    spike_category,
    use_lemmas,
    word,
  }: {
    areas: JSONAPI.Area[];
    beta_filter?: JSONAPI.ShakeToReportCategory;
    spike_category?: string;
    use_lemmas?: boolean;
    word: string;
  },
): Promise<
  {
    date: Date;
    value: number;
  }[]
> => {
  const params = new URLSearchParams();
  beta_filter && params.set("beta-filter", beta_filter);
  spike_category && params.set("spike-category", spike_category);
  use_lemmas && params.set("use-lemmas", "true");
  word && params.set("word", transformQuery(word, areas));

  const data = (
    await get<JSONAPI.TimeSeries>(`/1/${lang}/time_series?${params.toString()}`)
  ).values;
  return Object.entries(data).map(([date, value]) => ({
    date: convertTimeZone(parseISO(`${date}T00:00:00`), "America/New_York"),
    value: value ?? 0,
  }));
};

export const nlpSearch = async (query: string) => {
  const params = new URLSearchParams();
  params.set("q", query);

  return post<JSONAPI.NLPSearchResponse>(`/3/nlp_search?${params.toString()}`);
};

export const sendBetaEmails = async (description: string, spikeId: string) =>
  post<JSONAPI.FixedResponse>("/1/send_beta_emails", {
    description,
    spike_id: spikeId,
  });

export const setSpikeConfirmed = async (
  desiredState: boolean,
  spikeId: string,
) =>
  patch<JSONAPI.ConfirmedResponse>("/1/set_spike_confirm", {
    desired_state: desiredState,
    spike_id: spikeId,
  });

export const setSpikeFixed = async (desiredState: boolean, spikeId: string) =>
  patch<JSONAPI.FixedResponse>("/1/set_spike_fixed", {
    desired_state: desiredState,
    spike_id: spikeId,
  });
