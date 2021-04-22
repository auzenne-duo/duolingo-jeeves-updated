declare namespace JSONAPI {
  interface DuolingoMetadata {
    app_version?: string;
    course?: string;
    fullstory_url?: string;
    os_version?: string;
    platform?: "Android" | "iOS" | "Web";
    screen_content?: string;
    screen_size?: string;
    ui_language?: string;
    username?: string;
  }

  interface Info {
    /** The time that the current Jeeves instance was created. */
    deployed_timestamp: string;
    initialized_timestamp: string;
    /** The time of the most recent ticket that Elasticsearch has stored. */
    latest_ticket_timestamp: string;
  }

  /**
   * https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-links/#api-group-issue-links
   */
  interface JiraIssueLink {
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

  type LanguageId =
    | "de"
    | "fr"
    | "en"
    | "es"
    | "it"
    | "ja"
    | "ru"
    | "xx"
    | "zh";

  type ShakeToReportCategory =
    | "EXTERNAL"
    | "INTERNAL"
    | "NON_STR_EXTERNAL"
    | "NON_STR_INTERNAL";

  // STR is short for shake-to-report. Internal vs. external
  // refers to internal and external testers.
  type SpikeCategory =
    | "ALL_NON_STR_SPIKES"
    | "ALL_SPIKES"
    | "ALL_STR_SPIKES"
    | "EXTERNAL_NON_STR_SPIKES"
    | "EXTERNAL_STR_SPIKES"
    | "INTERNAL_NON_STR_SPIKES"
    | "INTERNAL_STR_SPIKES";

  interface Spikes {
    [date: string]:
      | {
          spike: [number, string][];
        }
      | undefined;
  }

  interface Ticket extends DuolingoMetadata {
    /** URLs to file attachments. Currently only available for Jira tickets. */
    attachments?: string[];
    /** Main content of the ticket. This is what we search against and perform spike detection on. */
    body_text?: string;
    /** Jira components. */
    components?: string[];
    /** Currently only available for Jira tickets. */
    creation_date?: string;
    /** String identifying where we got the ticket. */
    data_source: "AppFigures" | "JIRA" | "Zendesk" | string;
    /** The date and time the ticket was submitted to its respective service. */
    date_time?: string;
    /** An identifier for the ticket, assigned by the API we got the ticket from. */
    document_id: string;
    duolingo_metadata: {
      raw?: string;
    };
    /** Title, subject line, etc. */
    header_text?: string;
    /** The issue key of a Jira ticket. */
    issue_key?: string;
    /** Linked Jira issues. */
    issue_links?: JiraIssueLink[];
    /** A globally unique identifier for the ticket. */
    jeeves_uid: string;
    /** URLs we compute on the backend to direct the user to the original ticket/submitter. */
    links?: string[];
    /** Field assigned by Zendesk. */
    priority?: string;
    /** ID assigned to the user on Zendesk that submitted the ticket. */
    requester_id?: number;
    shake_to_report_category: ShakeToReportCategory;
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

  interface Tickets {
    data: Ticket[];
    next_url?: string;
    total_records: number;
  }

  interface TimeSeries {
    values: {
      [date: string]: number | undefined;
    };
  }
}
