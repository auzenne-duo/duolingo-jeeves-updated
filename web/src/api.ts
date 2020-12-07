import { LanguageId } from "components/LanguagePicker";

/**
 * https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-links/#api-group-issue-links
 */
export interface JiraIssueLink {
  inwardIssue?: {
    fields: {
      summary: string;
    };
    id: string;
    key: string;
  };
  outwardIssue?: {
    fields: {
      summary: string;
    };
    id: string;
    key: string;
  };
  type: {
    id: string;
    inward: string;
    name: "Duplicate" | string;
    outward: string;
  };
}

// STR is short for shake-to-report. Internal vs. external
// refers to internal and external testers.
export type SpikeCategory =
  | "ALL_NON_STR_SPIKES"
  | "ALL_SPIKES"
  | "ALL_STR_SPIKES"
  | "EXTERNAL_NON_STR_SPIKES"
  | "EXTERNAL_STR_SPIKES"
  | "INTERNAL_NON_STR_SPIKES"
  | "INTERNAL_STR_SPIKES";

export interface Ticket {
  /** @deprecated This will be moved to the backend. Use the metadata field instead. */
  beta_feedback_metadata?: {
    app_information?: {
      api_level?: string;
      app_version_code?: string;
      course?: string;
      os?: string;
      os_version?: string;
      screen?: string;
      username?: string;
    };
    fullstory?: string;
    session_information?: {
      activity?: string;
      fullstory_session?: string;
      fullstory_session_if_recording?: string;
      url?: string;
    };
    system_information?: {
      app_version?: string;
      ios_version?: string;
      screen?: string;
      ui_language?: string;
    };
    user_information?: {
      current_course?: string;
      username?: string;
    };
    view_controller_name?: string;
  };
  /** Main content of the ticket. This is what we search against and perform spike detection on. */
  body_text?: string;
  /** String identifying where we got this ticket. */
  data_source?: "AppFigures" | "JIRA" | "Zendesk" | string;
  /** The date and time the ticket was submitted to its respective service. */
  date_time?: string;
  /** An identifier for this ticket, assigned by the API we got the ticket from. */
  document_id?: string;
  /** Title, subject line, etc. */
  header_text?: string;
  /** The issue key of a Jira ticket. */
  issue_key?: string;
  /** Linked Jira issues. */
  issue_links?: JiraIssueLink[];
  /** URLs we compute on the backend to direct the user to the original ticket/submitter. */
  links?: string[];
  metadata?: {
    app_version?: string;
    course?: string;
    full_story_url?: string;
    os_version?: string;
    platform?: "android" | "ios" | "web";
    raw: string;
    screen?: string;
    screen_name?: string;
    screenshot_url?: string;
    ui_language?: string;
    username?: string;
  };
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
  await (
    await fetch(`${API_URL}${url}`, {
      credentials: "include",
    })
  ).json();

export const getJiraDuplicates = async (issue_key: string) => {
  const data = (await get(
    `/detect_duplicates?issue_key=${encodeURIComponent(issue_key)}`,
  )) as Ticket[];
  data.forEach(ticket => loadTicketMetadata(ticket));
  return data;
};

export const getInfo = async (lang: LanguageId) =>
  (await get(`/${lang}/info`)) as {
    /** The time that the current Jeeves instance was created. */
    deployed_timestamp: string;
    initialized_timestamp: string;
    /** The time of the most recent ticket that Elasticsearch has stored. */
    latest_ticket_timestamp: string;
  };

export const getSpikes = async (
  lang: LanguageId,
  {
    end_date,
    spike_category,
    start_date,
  }: {
    end_date?: Date;
    spike_category?: SpikeCategory;
    start_date?: Date;
  } = {},
) => {
  const params = new URLSearchParams();

  end_date && params.set("end_date", end_date.toJSON().slice(0, 10));
  spike_category && params.set("spike_category", spike_category);
  start_date && params.set("start_date", start_date.toJSON().slice(0, 10));

  const data = (await get(`/${lang}/spikes?${params.toString()}`)) as {
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
  } = {},
) => {
  const params = new URLSearchParams();

  beta_filter && params.set("beta_filter", "1");
  end_time && params.set("end_time", end_time.toJSON().slice(0, 10));
  limit && params.set("limit", `${limit}`);
  page && params.set("page", `${page}`);
  start_time && params.set("start_time", start_time.toJSON().slice(0, 10));
  word && params.set("word", word);

  const data = (await get(`/${lang}/tickets?${params.toString()}`)) as {
    data: Ticket[];
    next_url?: string;
    total_records: number;
  };
  data.data.forEach(ticket => loadTicketMetadata(ticket));

  return data;
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

// TODO: move this to the backend.
const loadTicketMetadata = (ticket: Ticket) => {
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
