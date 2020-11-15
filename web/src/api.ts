import { LanguageId } from "components/LanguagePicker";

export interface Ticket {
  /** Main content of the ticket. This is what we search against and perform spike detection on. */
  body_text?: string;
  /** String identifying where we got this ticket. Currently we support Zendesk and Appfigures, with JIRA coming in the near future. */
  data_source?: "AppFigures" | "Zendesk" | string;
  /** The date and time the ticket was submitted to its respective service. */
  date_time?: string;
  /** An identifier for this ticket, assigned by the API we got the ticket from. */
  document_id?: string;
  /** Title, subject line, etc. */
  header_text?: string;
  /** URLs we compute on the backend to direct the user to the original ticket/submitter. */
  links?: string[];
  /** Field assigned by Zendesk. */
  priority?: string;
  /** ID assigned to the user on Zendesk that submitted this ticket. */
  requester_id?: number;
  store?: string;
  tags?: string[];
  /** Only applies to Zendesk tickets. */
  via?: {
    channel?: string;
    source?: {
      from?: {
        address?: string;
        name?: string;
      };
    };
  };
}

const API_URL =
  process.env.NODE_ENV === "production"
    ? "/api/1"
    : "http://localhost:5000/api/1";

const get = async (url: string) =>
  await (await fetch(`${API_URL}${url}`)).json();

export const getInfo = async (lang: LanguageId) =>
  (await get(`/${lang}/info`)) as {
    /** The time that the current Jeeves instance was created. */
    deployed_timestamp: string;
    initialized_timestamp: string;
    /** The time of the most recent ticket that Elasticsearch has stored. */
    latest_ticket_timestamp: string;
  };

export const getSpikes = async (lang: LanguageId) => {
  const data = (await get(`/${lang}/spikes`)) as {
    [date: string]:
      | {
          spike: [number, string][];
        }
      | undefined;
  };
  return Object.fromEntries(
    Object.entries(data).map(([date, value]) => [date, value?.spike]),
  );
};

export const getTickets = async (
  lang: LanguageId,
  {
    beta_filter,
    end_time,
    limit,
    page,
    start_time,
    word,
  }: {
    beta_filter?: boolean;
    end_time?: Date;
    limit?: number;
    page?: number;
    start_time?: Date;
    word?: string;
  },
) => {
  const params = new URLSearchParams();

  beta_filter && params.set("beta_filter", "1");
  end_time && params.set("end_time", end_time.toJSON().slice(0, 10));
  limit && params.set("limit", `${limit}`);
  page && params.set("page", `${page}`);
  start_time && params.set("start_time", start_time.toJSON().slice(0, 10));
  word && params.set("word", word);

  return (await get(`/${lang}/tickets?${params.toString()}`)) as {
    data: Ticket[];
    next_url?: string;
    total_records: number;
  };
};

export const getTimeSeries = async (
  lang: LanguageId,
  {
    word,
  }: {
    word: string;
  },
) =>
  ((await get(`/${lang}/time_series?word=${word}`)) as {
    values: {
      [date: string]: number | undefined;
    };
  }).values;
