import { get, post } from "api/client";

interface IssueData {
  description?: string;
  feature?: string;
  generatedDescription?: string;
  preRelease: boolean;
  project: JiraProject;
  reporterEmail?: string;
  slackReportType?: string;
  summary: string;
}

export type JiraProject = "DLAA" | "DLAI" | "DLAW";

interface ReportIssueJiraResult {
  issueKey: string;
  jiraUrl: string;
  slackChannel?: null;
  slackUrl?: null;
}

interface ReportIssueSlackResult {
  issueKey?: null;
  jiraUrl?: null;
  slackChannel: string;
  slackUrl: string;
}

export type ReportIssueResult =
  | ReportIssueJiraResult
  | ReportIssueSlackResult
  | (ReportIssueJiraResult & ReportIssueSlackResult);

export interface SlackReportType {
  alsoPostsToJira: boolean;
  name: string;
}

interface SuggestedFeaturesResult {
  other_features: string[];
  suggested_features: string[];
}

/** Detects potential duplicates for a Jira issue. */
export const detectDuplicates = (issueKey: string) =>
  get<JSONAPI.Ticket[]>(
    `/1/detect_duplicates?issue_key=${encodeURIComponent(issueKey)}`,
  );

export const fullyConnectDuplicates = (issueKeys: string[]) =>
  post("/1/fully_connect_duplicates", {
    issue_keys: issueKeys,
  });

export const getFeaturesByTeamAndArea = () =>
  get<JSONAPI.Area[]>("/2/shakira/features_by_team_and_area");

export const getSlackReportTypes = () =>
  get<SlackReportType[]>("/2/shakira/slack_report_types");

/** Gets the possible values for the feature field of a Jira issue. */
export const getSuggestedFeatures = async (data: {
  description?: string;
  generated_description?: string;
  summary: string;
}): Promise<SuggestedFeaturesResult> => {
  const params = new URLSearchParams();
  data.description && params.set("description", data.description);
  data.generated_description &&
    params.set("generated_description", data.generated_description);
  params.set("summary", data.summary);
  return get<SuggestedFeaturesResult>(
    `/2/shakira/suggested_features?${params.toString()}`,
  );
};

/** Creates an issue in Jira and/or posts it to Slack. */
export const reportIssue = (data: IssueData, attachments: [string, File][]) => {
  const formData = new FormData();
  formData.set("issueData", JSON.stringify(data));
  attachments.forEach(([key, file]) => formData.set(key, file));
  return post<ReportIssueResult>("/2/shakira/report_issue", formData);
};
