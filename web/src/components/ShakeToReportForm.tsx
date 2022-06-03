import { formatAttachment, getUntruncatedTitle, isImage } from "util";

import * as React from "react";
import { useQuery } from "react-query";
import {
  Button,
  Input,
  List,
  Select,
  TextArea,
  getButtonClassName,
} from "web-ui";

import { getBlob } from "api/client";
import * as shakiraApi from "api/shakira";
import { getLoggedIn } from "api/user";
import cn from "classnames";
import imageArrowLeft from "images/arrow-left.svg";
import styles from "styles/ShakeToReportForm.scss";
import track from "track";

const NONE_APPLY = "None apply";

const getAttachments = async (urls: string[]) => {
  const attachments: [string, File][] = [];
  const promises = urls.map(async url => {
    try {
      const urlWithCors = new URL(url);
      if (isImage(url)) {
        // Add a query parameter to the image URL to indicate that we're
        // fetching image data with CORS enabled. Without this parameter
        // most browsers don't keep separate cache entries for CORS and
        // non-CORS requests of the same resource. As the image has already
        // been fetched without CORS by the <img> tag, that would cause
        // this request to fail.
        urlWithCors.searchParams.set("with-cors", "1");
      }
      const blob = await getBlob(urlWithCors.toString());
      const name = formatAttachment(url);
      attachments.push([
        // Shakira expects this to be named `screenshot` for uploading it to Slack.
        isImage(url) && !attachments.some(([n]) => n === "screenshot")
          ? "screenshot"
          : name,
        new File([blob], name, {
          type: blob.type,
        }),
      ]);
    } catch (ex) {
      // eslint-disable-next-line no-console
      console.error(ex);
    }
  });
  await Promise.all(promises);
  return attachments;
};

interface Props {
  onReported?: (result: shakiraApi.ReportIssueResult, summary: string) => void;
  onRequestClose: () => void;
  ticket: JSONAPI.Ticket;
}

const ShakeToReportForm = ({ onReported, onRequestClose, ticket }: Props) => {
  const [description, setDescription] = React.useState(ticket.body_text ?? "");
  const [duplicates, setDuplicates] = React.useState<JSONAPI.Ticket[]>();
  // eslint-disable-next-line @typescript-eslint/naming-convention
  const [_feature, setFeature] = React.useState<string>();
  const [featuresQuery, setFeaturesQuery] = React.useState("");
  const [generatedDescription] = React.useState(ticket.duolingo_metadata.raw);
  const [issue, setIssue] = React.useState<shakiraApi.ReportIssueResult>();
  const [markedDuplicates, setMarkedDuplicates] = React.useState<number[]>([]);
  const [slackChannel, setSlackChannel] =
    React.useState<shakiraApi.SlackReportType>();
  const [step, setStep] = React.useState<
    "duplicates" | "features" | "report" | "submitted"
  >("report");
  const [submitting, setSubmitting] = React.useState(false);
  const [suggestedFeature, setSuggestedFeature] = React.useState<string>();
  const [summary, setSummary] = React.useState(
    () => getUntruncatedTitle(ticket) ?? "",
  );

  const { data: featuresResult } = useQuery(
    [
      "suggested-features",
      {
        description: description.trim(),
        generatedDescription,
        summary: summary.trim(),
      },
    ],
    () =>
      shakiraApi.getSuggestedFeatures({
        description: description.trim(),
        generated_description: generatedDescription,
        summary: summary.trim(),
      }),
    {
      enabled: step === "features",
    },
  );

  const features = React.useMemo(
    () =>
      featuresResult ? [...featuresResult.other_features].sort() : undefined,
    [featuresResult],
  );

  const suggestedFeatures = featuresResult
    ? [...featuresResult.suggested_features, NONE_APPLY]
    : undefined;

  const { data: slackChannels } = useQuery("slack-report-types", () =>
    shakiraApi.getSlackReportTypes(),
  );
  const { data: user } = useQuery("user", () => getLoggedIn());

  const canShowFeatures = featuresResult !== undefined;
  const feature = _feature ?? suggestedFeature;
  const isLoading = submitting || (step === "features" && !canShowFeatures);

  const handleSubmit: React.FormEventHandler<HTMLFormElement> = async e => {
    e.preventDefault();
    // TODO: use customValidity API to show errors?
    //  See https://github.com/duolingo/duolingo-web/pull/3755.
    if (!(e.target as HTMLFormElement).checkValidity()) {
      return;
    }
    switch (step) {
      case "duplicates":
        if (duplicates && markedDuplicates.length) {
          shakiraApi.fullyConnectDuplicates(
            markedDuplicates.map((_, i) => duplicates[i].issue_key as string),
          );
        }
        onRequestClose();
        return;
      case "features":
        break;
      case "report":
        if (slackChannel === undefined || slackChannel?.alsoPostsToJira) {
          setStep("features");
          return;
        }
        break;
      case "submitted":
        onRequestClose();
        return;
      default:
        return;
    }
    setSubmitting(true);
    try {
      const result = await shakiraApi.reportIssue(
        {
          description: description.trim(),
          feature,
          generatedDescription,
          // This data isn't available in Jeeves yet.
          preRelease: false,
          project:
            ticket.platform === "Android"
              ? "DLAA"
              : ticket.platform === "iOS"
              ? "DLAI"
              : "DLAW",
          reporterEmail: user?.email,
          slackReportType: slackChannel?.name,
          summary: `[via Jeeves] ${summary.trim()}`,
        },
        await getAttachments(ticket.attachments ?? []),
      );
      setIssue(result);
      onReported?.(result, summary.trim());
      if (result.issueKey) {
        const dups = await shakiraApi.detectDuplicates(result.issueKey);
        if (dups.length) {
          setDuplicates(dups);
          setStep("duplicates");
        } else {
          setStep("submitted");
        }
      } else {
        setStep("submitted");
      }
      track("shake_to_report_feedback", {
        feature,
        number_suggested_features: suggestedFeatures
          ? suggestedFeatures.length - 1
          : 0,
        report_type: "jeeves",
        selected_suggested_feature:
          suggestedFeature !== undefined && suggestedFeature !== NONE_APPLY,
        slack_channel: slackChannel?.name,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const renderFeaturesStep = () => [
    <div className={styles.header} key="header">
      <Button disabled={isLoading} onClick={() => setStep("report")}>
        <img className={styles.icon} src={imageArrowLeft} />
      </Button>
      <h2>Choose a feature</h2>
    </div>,
    <>
      {suggestedFeatures !== undefined &&
      // One of the features is "None apply".
      suggestedFeatures.length > 1 ? (
        <>
          <strong>Recommended features</strong>
          <List
            items={suggestedFeatures.map(s => ({ text: s }))}
            onChange={e =>
              setSuggestedFeature(
                e.selectedIndices.length
                  ? suggestedFeatures[e.selectedIndices[0]]
                  : undefined,
              )
            }
            selectedIndices={
              suggestedFeature !== undefined &&
              suggestedFeatures.includes(suggestedFeature)
                ? [suggestedFeatures.indexOf(suggestedFeature)]
                : []
            }
          />
        </>
      ) : null}
      {features !== undefined &&
      (suggestedFeatures?.length === 1 || suggestedFeature === NONE_APPLY) ? (
        <>
          <strong>Select a feature</strong>
          <List
            className={styles.list}
            items={features.map(s => ({ text: s }))}
            onChange={e =>
              setFeature(
                e.selectedIndices.length
                  ? features[e.selectedIndices[0]]
                  : undefined,
              )
            }
            onQueryChange={e => setFeaturesQuery(e.value)}
            query={featuresQuery}
            scrollable={true}
            selectedIndices={
              feature !== undefined && features.includes(feature)
                ? [features.indexOf(feature)]
                : []
            }
            showSearch={true}
          />
        </>
      ) : null}
    </>,
    <Button
      color="owl"
      disabled={!feature || feature === NONE_APPLY}
      key="footer"
      submitting={isLoading}
      type="submit"
      variant="solid"
    >
      Create Jira ticket
    </Button>,
  ];

  const renderReportStep = () => [
    <div className={styles.header} key="header">
      <h2>Internal bug report</h2>
    </div>,
    <>
      <Input
        disabled={isLoading}
        onChange={e => setSummary(e.target.value)}
        placeholder="Short description"
        required={true}
        type="text"
        value={summary}
      />
      <TextArea
        disabled={isLoading}
        onChange={e => setDescription(e.target.value)}
        placeholder="What went wrong in more detail?"
        rows={5}
        value={description}
      />
      <Select
        disabled={isLoading}
        onChange={e =>
          setSlackChannel(slackChannels?.find(c => c.name === e.target.value))
        }
        options={[
          { text: "Choose Slack (optional)", value: "" },
          ...(slackChannels?.map(c => ({ text: c.name, value: c.name })) ?? []),
        ]}
        value={slackChannel?.name ?? ""}
      />
      <span className={styles.small}>
        If your report belongs in #visual-polish, #feedback-language,
        #feedback-tts, or #feedback-product on Slack, choose one.
      </span>
    </>,
    <Button
      color={
        slackChannel === undefined || slackChannel.alsoPostsToJira
          ? undefined
          : "owl"
      }
      disabled={!summary.trim()}
      key="footer"
      submitting={isLoading}
      type="submit"
      variant={
        slackChannel === undefined || slackChannel.alsoPostsToJira
          ? "stroke"
          : "solid"
      }
    >
      {slackChannel === undefined || slackChannel.alsoPostsToJira
        ? "Next"
        : "Post to Slack"}
    </Button>,
  ];

  const renderSubmittedStep = () => [
    <div className={styles.header} key="header">
      <h2>{step === "duplicates" ? "Possible duplicates" : "Thank you"}</h2>
    </div>,
    <>
      <strong>Thanks for your feedback!</strong>
      {duplicates?.length ? (
        <>
          <span>We’ve identified potential duplicate reports.</span>
          <span>
            Please help us improve our duplicate detection system by taking a
            few moments to mark any of the following reports that might be
            duplicates of your issue.
          </span>
        </>
      ) : null}
      <a
        className={cn(getButtonClassName({ variant: "stroke" }), styles.button)}
        href={issue?.jiraUrl ?? issue?.slackUrl ?? ""}
        rel="noreferrer"
        target="_blank"
      >
        <span className={styles["button-inner"]}>
          {issue?.issueKey
            ? `Your Jira ticket: ${issue.issueKey}`
            : `View in ${issue?.slackChannel}`}
        </span>
      </a>
      {duplicates?.length ? (
        <List
          items={duplicates.map(d => ({
            text: `${d.issue_key}: ${d.header_text}`,
            textEl: (
              <a
                className={styles["link-ellipsis"]}
                href={`https://duolingo.atlassian.net/browse/${encodeURIComponent(
                  d.issue_key as string,
                )}`}
                onClick={e => e.stopPropagation()}
                rel="noreferrer"
                target="_blank"
              >
                {d.issue_key}: {d.header_text}
              </a>
            ),
          }))}
          multiple={true}
          onChange={e => setMarkedDuplicates(e.selectedIndices)}
          selectedIndices={markedDuplicates}
        />
      ) : null}
    </>,
    <Button color="owl" key="footer" type="submit" variant="solid">
      Done
    </Button>,
  ];

  const [header, content, footer] =
    step === "report" || (step === "features" && !canShowFeatures)
      ? renderReportStep()
      : step === "features"
      ? renderFeaturesStep()
      : step === "duplicates"
      ? renderSubmittedStep()
      : step === "submitted"
      ? renderSubmittedStep()
      : [];

  return (
    <>
      {header}
      <form className={styles.form} noValidate={true} onSubmit={handleSubmit}>
        {content}
        {footer}
      </form>
    </>
  );
};

export default ShakeToReportForm;
