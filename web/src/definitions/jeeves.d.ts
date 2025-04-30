declare namespace JSONAPI {
  interface Area {
    area_name: string;
    teams: Team[];
  }

  interface ConfirmedResponse {
    confirmed: boolean;
    confirmed_user_id: number;
  }

  type DataSource = "AppFigures" | "JIRA" | "Reddit" | "Zendesk";

  interface DetailedAreaQualityReport extends DetailedQualityReport {
    teams: DetailedQualityReport[];
  }

  interface DetailedQualityReport {
    design_quality_issues: Ticket[];
    end_date: string;
    features: string[];
    max_dupes_issues: Ticket[];
    max_priority_issues: Ticket[];
    open_bugs_count: number;
    open_bugs_url: string;
    open_issues?: {
      key: string;
      title: string;
      assignee: string;
      creation_date: string;
    }[];
    overall_score: number;
    recent_changes?: QualityReportRecentChanges;
    score_breakdowns: {
      closed_points: number;
      date: string;
      num_issues: number;
      open_points: number;
      overall_score: number;
      quality_score_type_counts: {
        count: number;
        duplicate_bonus_points?: number;
        label: string;
        points: number;
      }[];
    }[];
    scores: QualityScores;
    start_date: string;
    title: string;
  }

  interface DocumentContent {
    body: string;
    title: string;
  }

  interface DuolingoMetadata {
    app_version?: string;
    course?: string;
    fullstory_url?: string;
    os_version?: string;
    platform?: Platform;
    screen_content?: string;
    screen_size?: string;
    ui_language?: string;
    username?: string;
  }

  interface ExperimentSpike {
    experiment: string;
    score: number;
  }

  interface FiltersResponse {
    lucene_filters: Record<string, string>;
  }

  interface FixedResponse {
    fixed: boolean;
    fixed_user_id: number;
    num_emails: number;
  }

  interface GPTAnswerResponse extends GPTBaseResponse {
    answer: string;
    supporting_docs: GPTSearchResult[];
  }

  interface GPTBaseResponse {
    error?: string;
  }

  interface GPTDocsResponse extends GPTBaseResponse {
    docs: Ticket[];
  }

  interface GPTFiltersResponse extends FiltersResponse, GPTBaseResponse {
    request_id: string;
  }

  interface GPTSearchResult {
    bolded_body: string;
    doc: Ticket;
    translated_text?: LanguageContent;
  }

  type GPTSearchStage = "filters" | "knn" | "answer";

  interface Info {
    /** The time that the current Jeeves instance was created. */
    deployed_timestamp: string;
    initialized_timestamp: string;
    /** The time of the most recent ticket that OpenSearch has stored. */
    latest_ticket_timestamp: string;
  }

  /**
   * https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-links/#api-group-issue-links
   */
  interface JiraIssueLink {
    inwardIssue?: {
      fields: {
        status: {
          name: string;
        };
        summary: string;
      };
      id: string;
      key: string;
    };
    outwardIssue?: {
      fields: {
        status: {
          name: string;
        };
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

  interface LanguageContent extends DocumentContent {
    // The original body text of the document, taken directly from OpenSearch, so that we can check if GPT
    //   has changed the text somehow while formatting with markup tags
    body_orig: string;
    language: string;
  }

  type LanguageId =
    | "all"
    | "de"
    | "fr"
    | "en"
    | "es"
    | "hi"
    | "it"
    | "ja"
    | "pt"
    | "ru"
    | "xx"
    | "zh";

  type Platform = "Android" | "iOS" | "Web";

  type Priority =
    | "Highest"
    | "High"
    | "Medium"
    | "Low"
    | "Lowest"
    | "Unprioritized"
    | ZendeskPriority;

  interface QualityReportOverviewPillar {
    pillars: {
      scores: QualityScores;
      title: string;
    }[];
  }

  interface QualityReportOverviewTeam {
    teams: {
      scores: QualityScores;
      title: string;
    }[];
  }

  interface QualityReport {
    areas: {
      scores: QualityScores;
      title: string;
    }[];
  }

  interface QualityReportRecentChanges {
    previous_report_date_string: string;
    change_due_to_added_issues: number;
    change_due_to_resolved_issues: number;
    resolved_issue_count: number;
    resolved_issue_link?: string;
    added_issue_count: number;
    added_issue_link?: string;
  }

  interface QualityScores {
    DLAA: [date: string, score: number][];
    DLAI: [date: string, score: number][];
    DLAW: [date: string, score: number][];
    Overall: [date: string, score: number][];
  }

  interface QualityScoresHistory {
    scores: QualityScores;
  }

  interface SearchResult {
    datetime: string;
    origin: string;
    score: number;
    uid: string;
    url?: string;
  }

  interface SentimentBucket {
    average_sentiment_score: number;
    num_documents: number;
  }

  interface SentimentSearchData extends FiltersResponse {
    negative_bucket: { date: Date; score: number; count: number }[];
    positive_bucket: { date: Date; score: number; count: number }[];
    results: SentimentSearchResult[];
    topic: string;
  }

  interface SentimentSearchResponse extends FiltersResponse {
    negative_bucket: Record<string, SentimentBucket | undefined>;
    positive_bucket: Record<string, SentimentBucket | undefined>;
    results: SentimentSearchResult[];
    topic: string;
  }

  interface SentimentSearchResult extends SearchResult {
    label: string;
    original_text: DocumentContent;
  }

  type ShakeToReportCategory =
    | "EXTERNAL"
    | "INTERNAL"
    | "NON_STR_EXTERNAL"
    | "NON_STR_INTERNAL";

  interface SpikeCategoryData {
    text: string;
    value: string;
  }

  interface SpikeDataResponse {
    date: Date;
    spikes: SpikeWord[];
  }

  type Spikes = Record<
    string,
    | {
        spike: SpikeWord[];
      }
    | undefined
  >;

  interface SpikeStats {
    month_count: { date_str: string; confirmed: number; total: number }[];
    word_count: SpikeWordStats[];
  }

  type SpikeStatus =
    | "CONFIRMED"
    | "UNCONFIRMED"
    | "FIXED"
    | "INVESTIGATING"
    | "IGNORED";

  interface SpikeStatusResponse {
    status: string;
    user_id: number;
  }

  interface SpikeWord {
    confirmed: boolean;
    confirmed_user_id?: number;
    experiment_spikes: ExperimentSpike[];
    email_sent_date?: string;
    email_user_id?: number;
    fixed: boolean;
    fixed_user_id?: number;
    is_bug: boolean;
    lang: string;
    score: number;
    spike_id: string;
    status: SpikeStatus;
    status_user_id?: number;
    summary: string;
    word: string;
  }

  interface SpikeWordStats {
    dates: string[];
    num_confirmed: number;
    stem: string;
    terms: string[];
    total: number;
  }

  interface Team {
    features: string[];
    team_name: string;
  }

  interface Ticket extends DuolingoMetadata {
    /** The user who is assigned to the ticket. */
    assignee?: string;
    /** URLs to file attachments. Currently only available for Jira tickets. */
    attachments?: string[];
    /** Review author for AppFigures tickets. */
    author?: string;
    /** Main content of the ticket. This is what we search against and perform spike detection on. */
    body_text?: string;
    /** If this is a parent bug, this contains a list of child issues. */
    child_issues?: string[];
    /** Jira components. */
    components?: string[];
    /** Currently only available for Jira tickets. */
    creation_date?: string;
    /** String identifying where we got the ticket. */
    data_source: DataSource;
    /** The date and time the ticket was submitted to its respective service. */
    date_time?: string;
    /** An identifier for the ticket, assigned by the API we got the ticket from. */
    document_id: string;
    duolingo_metadata: {
      raw?: string;
    };
    email?: string;
    /** Feature field of a Jira ticket. */
    feature?: string;
    /** Title, subject line, etc. */
    header_text?: string;
    /** The issue key of a Jira ticket. */
    issue_key?: string;
    /** Linked Jira issues. */
    issue_links?: JiraIssueLink[];
    /** A globally unique identifier for the ticket. */
    jeeves_uid: string;
    /** Issue keys of linked Jira issues. */
    linked_duplicate_keys?: string[];
    /** URLs we compute on the backend to direct the user to the original ticket/submitter. */
    links?: string[];
    priority?: Priority;
    /** ID assigned to the user on Zendesk that submitted the ticket. */
    requester_id?: number;
    shake_to_report_category: ShakeToReportCategory;
    /** The status of a Jira ticket. */
    status?: string;
    store?: string;
    tags?: string[];
    user_id?: number;
    /** Only applies to Zendesk tickets. */
    via?:
      | {
          channel: "api";
        }
      | {
          channel: "email";
          source: {
            from: ZendeskEmailAccount;
          };
        }
      | {
          channel: "mobile_sdk";
        }
      | {
          channel: "twitter";
          source: {
            from: ZendeskTwitterAccount;
            to: ZendeskTwitterAccount;
          };
        }
      | {
          channel: "web";
        };
  }

  interface Tickets {
    data: Ticket[];
    next_sort_id?: string;
    prev_sort_id?: string;
    total_records: number;
  }

  interface TimeSeries {
    values: Record<string, number | undefined>;
  }

  interface ZendeskEmailAccount {
    address: string;
    name?: string;
  }

  type ZendeskPriority = "urgent" | "high" | "normal" | "low";

  interface ZendeskTwitterAccount {
    name?: string;
    profile_url: string;
    twitter_id: string;
    username: string;
  }
}
