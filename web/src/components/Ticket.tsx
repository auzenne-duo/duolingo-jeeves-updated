import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { Link, useLocation } from "react-router-dom";
import { LoadingDots } from "web-ui";
import type { Range } from "web-ui/util/highlight";
import { highlightText } from "web-ui/util/highlight";

import {
  formatAttachment,
  formatCourseId,
  formatPriority,
  formatReadableDateTime,
  formatScreen,
  getFilterLink,
  isImage,
  normalizeNewLines,
} from "../util";
import { detectDuplicates } from "api/shakira";
import cn from "classnames";
import IconButton from "components/IconButton";
import JiraIssues from "components/JiraIssues";
import PlatformIcon from "components/PlatformIcon";
import ShakeToReportForm from "components/ShakeToReportForm";
import Tag from "components/Tag";
import TagFilterOrTag from "components/TagFilterOrTag";
import styles from "components/Ticket.scss";
import AppStateContext from "contexts/AppStateContext";
import imageBug from "images/ant.svg";
import imageClose from "images/x.svg";

const getZendeskChannel = (ticket: JSONAPI.Ticket) =>
  ticket.via?.channel === "email"
    ? "Email"
    : ticket.via?.channel === "mobile_sdk"
    ? "Zendesk mobile"
    : ticket.via?.channel === "twitter"
    ? "Twitter"
    : "Zendesk";

interface Props {
  className?: string;
  highlight?: Range[];
  onRequestClose?: () => void;
  supportsTicketQuery?: boolean;
  ticket: JSONAPI.Ticket;
}

// eslint-disable-next-line complexity
const Ticket = ({
  className,
  highlight,
  onRequestClose,
  supportsTicketQuery = false,
  ticket,
}: Props) => {
  const location = useLocation();

  const [state, dispatch] = React.useContext(AppStateContext);
  const [isReporting, setIsReporting] = React.useState(false);

  const body = normalizeNewLines(
    highlightText(ticket.body_text ?? "", highlight ?? []),
  )
    .trim()
    .replace(/\n/g, "<br />");

  const duplicates = ticket.issue_links?.filter(
    link => link.type.name === "Duplicate",
  );

  const { data: potentialDuplicates, isLoading: isLoadingPotentialDuplicates } =
    useQuery(
      ["jira-duplicates", { issueKey: ticket.issue_key }],
      () => detectDuplicates(ticket.issue_key as string),
      {
        enabled: !!ticket.issue_key,
      },
    );

  const imageAttachments = ticket.attachments?.filter(url => isImage(url));
  const urlAttachments = ticket.attachments?.filter(url => !isImage(url));

  const reportedIssue = state.reportedIssues.find(
    i => i.jeeves_uid === ticket.jeeves_uid,
  );

  const content = isReporting ? (
    <ShakeToReportForm
      onReported={(result, summary) =>
        dispatch({
          issue: {
            jeeves_uid: ticket.jeeves_uid,
            result,
            summary,
          },
          type: "REPORTED_ISSUE",
        })
      }
      onRequestClose={() => setIsReporting(false)}
      ticket={ticket}
    />
  ) : (
    <>
      <h2>{ticket.header_text ?? "(No title)"}</h2>
      {reportedIssue?.result.issueKey ? (
        <section className={styles.section}>
          <JiraIssues
            issues={[
              {
                key: reportedIssue.result.issueKey,
                summary: reportedIssue.summary,
              },
            ]}
          />
        </section>
      ) : null}
      {body ? (
        <section className={styles.section}>
          <span className={styles.label}>Description</span>
          <div
            dangerouslySetInnerHTML={{
              // eslint-disable-next-line @typescript-eslint/naming-convention
              __html: body,
            }}
          />
        </section>
      ) : null}
      {ticket.app_version ? (
        <section className={styles.section}>
          <span className={styles.label}>App version</span>
          <div>
            <TagFilterOrTag
              className={styles.tag}
              field="app_version"
              useFilter={supportsTicketQuery}
              value={ticket.app_version}
            />
          </div>
        </section>
      ) : null}
      {imageAttachments?.length ||
      urlAttachments?.length ||
      ticket.fullstory_url ? (
        <section className={styles.section}>
          <span className={styles.label}>Attachments</span>
          {urlAttachments?.length || ticket.fullstory_url ? (
            <div className={styles.attachments}>
              {urlAttachments?.map((url, i) => (
                <a href={url} key={i}>
                  {formatAttachment(url)}
                </a>
              ))}
              {ticket.fullstory_url ? (
                <a href={ticket.fullstory_url}>FullStory recording</a>
              ) : null}
            </div>
          ) : null}
          {imageAttachments?.length ? (
            <div className={styles.thumbs}>
              {imageAttachments.map(url => (
                <img
                  alt=""
                  className={styles.thumb}
                  key={url}
                  onClick={() => dispatch({ type: "LIGHTBOX", url })}
                  src={url}
                  tabIndex={0}
                />
              ))}
            </div>
          ) : null}
        </section>
      ) : null}
      {ticket.components?.length ? (
        <section className={styles.section}>
          <span className={styles.label}>Components</span>
          <div>
            {ticket.components?.map(c => (
              <TagFilterOrTag
                className={styles.tag}
                field="components"
                key={c}
                useFilter={supportsTicketQuery}
                value={c}
              />
            ))}
          </div>
        </section>
      ) : null}
      {ticket.course ? (
        <section className={styles.section}>
          <span className={styles.label}>Course</span>
          <div>
            <TagFilterOrTag
              className={styles.tag}
              field="course"
              text={formatCourseId(ticket.course)}
              useFilter={supportsTicketQuery}
              value={ticket.course}
            />
          </div>
        </section>
      ) : null}
      {ticket.feature ? (
        <section className={styles.section}>
          <span className={styles.label}>Feature</span>
          <div>
            <TagFilterOrTag
              className={styles.tag}
              field="feature.keyword"
              useFilter={supportsTicketQuery}
              value={ticket.feature}
            />
          </div>
        </section>
      ) : null}
      {duplicates?.length ? (
        <section className={styles.section}>
          <span
            className={styles.label}
            title="These are confirmed duplicates and are linked in the Jira record."
          >
            Linked duplicates
          </span>
          <div>
            <JiraIssues
              issues={duplicates.map(issue => ({
                key: (issue.inwardIssue?.key ??
                  issue.outwardIssue?.key) as string,
                status: (issue.inwardIssue?.fields.status.name ??
                  issue.outwardIssue?.fields.status.name) as string,
                summary: (issue.inwardIssue?.fields.summary ??
                  issue.outwardIssue?.fields.summary) as string,
              }))}
            />
          </div>
        </section>
      ) : null}
      {ticket.os_version ? (
        <section className={styles.section}>
          <span className={styles.label}>OS version</span>
          <div>
            <TagFilterOrTag
              className={styles.tag}
              field="os_version"
              useFilter={supportsTicketQuery}
              value={ticket.os_version}
            />
          </div>
        </section>
      ) : null}
      {ticket.platform ? (
        <section className={styles.section}>
          <span className={styles.label}>Platform</span>
          <div>
            <Link to={getFilterLink(location, "platform", ticket.platform)}>
              <PlatformIcon
                className={styles.icon}
                platform={ticket.platform}
              />
            </Link>
          </div>
        </section>
      ) : null}
      {ticket.data_source === "JIRA" ? (
        <section className={styles.section}>
          <span
            className={styles.label}
            title="Jeeves has detected these issues as potential duplicates of this ticket."
          >
            Potential duplicates
          </span>
          <div>
            {isLoadingPotentialDuplicates || !potentialDuplicates?.length ? (
              <div className={styles["loading-container"]}>
                <span
                  className={
                    isLoadingPotentialDuplicates ? styles.invisible : undefined
                  }
                >
                  None
                </span>
                {isLoadingPotentialDuplicates ? (
                  <LoadingDots type="button" />
                ) : null}
              </div>
            ) : (
              <JiraIssues
                issues={potentialDuplicates.map(t => ({
                  key: t.issue_key as string,
                  status: t.status as string,
                  summary: t.header_text as string,
                }))}
              />
            )}
          </div>
        </section>
      ) : null}
      {ticket.priority ? (
        <section className={styles.section}>
          <span className={styles.label}>Priority</span>
          <div>
            <TagFilterOrTag
              className={styles.tag}
              field="priority"
              isPriority={true}
              text={formatPriority(ticket.priority)}
              useFilter={supportsTicketQuery}
              value={ticket.priority}
            />
          </div>
        </section>
      ) : null}
      {ticket.date_time ? (
        <section className={styles.section}>
          <span className={styles.label}>Reported at</span>
          <div>{formatReadableDateTime(new Date(ticket.date_time))}</div>
        </section>
      ) : null}
      {ticket.screen_content ? (
        <section className={styles.section}>
          <span className={styles.label}>Screen</span>
          <div>
            <TagFilterOrTag
              className={styles.tag}
              field="screen_content"
              text={formatScreen(ticket.screen_content)}
              useFilter={supportsTicketQuery}
              value={ticket.screen_content}
            />
          </div>
        </section>
      ) : null}
      {ticket.screen_size ? (
        <section className={styles.section}>
          <span className={styles.label}>Screen dimensions</span>
          <div>
            <TagFilterOrTag
              className={styles.tag}
              field="screen_size"
              useFilter={supportsTicketQuery}
              value={ticket.screen_size}
            />
          </div>
        </section>
      ) : null}
      <section className={styles.section}>
        <span className={styles.label}>Source</span>
        <div>
          {ticket.data_source === "AppFigures" ? (
            <>
              {ticket.author ? (
                <>
                  <TagFilterOrTag
                    className={styles.tag}
                    field="author"
                    useFilter={supportsTicketQuery}
                    value={ticket.author}
                  />
                  {" via "}
                </>
              ) : null}
              AppFigures
              {ticket.store ? (
                <>
                  ,{" "}
                  <TagFilterOrTag
                    className={styles.tag}
                    field="store"
                    useFilter={supportsTicketQuery}
                    value={ticket.store}
                  />
                </>
              ) : null}
            </>
          ) : ticket.data_source === "JIRA" ? (
            <JiraIssues
              issues={[
                {
                  key: ticket.issue_key as string,
                  status: ticket.status as string,
                  summary: ticket.header_text as string,
                },
              ]}
            />
          ) : ticket.data_source === "Reddit" ? (
            <>
              {ticket.author ? (
                <>
                  <TagFilterOrTag
                    className={styles.tag}
                    field="author"
                    useFilter={supportsTicketQuery}
                    value={ticket.author}
                  />
                  {" via "}
                </>
              ) : null}
              <a href={ticket.links?.[0]}>Reddit</a>
            </>
          ) : ticket.data_source === "Zendesk" ? (
            <>
              {ticket.email ? (
                <>
                  <a
                    href={`https://duolingo.com/diagnostics/user/summary/email/${ticket.email}`}
                  >
                    {ticket.email}
                  </a>
                  {" via "}
                </>
              ) : ticket.via?.channel === "twitter" ? (
                <>
                  <a href={ticket.via.source.from.profile_url}>
                    @{ticket.via.source.from.username}
                  </a>
                  {" via "}
                </>
              ) : null}
              <a href={ticket.links?.[0]}>{getZendeskChannel(ticket)}</a>
            </>
          ) : (
            ticket.data_source
          )}
        </div>
      </section>
      {ticket.tags?.length ? (
        <section className={styles.section}>
          <span className={styles.label}>Tags</span>
          <div className={styles.tags}>
            {ticket.tags?.map(tag => (
              <TagFilterOrTag
                className={styles.tag}
                field="tags"
                key={tag}
                useFilter={supportsTicketQuery}
                value={tag}
              />
            ))}
          </div>
        </section>
      ) : null}
      {ticket.ui_language ? (
        <section className={styles.section}>
          <span className={styles.label}>UI language</span>
          <div>
            <TagFilterOrTag
              className={styles.tag}
              field="ui_language"
              useFilter={supportsTicketQuery}
              value={ticket.ui_language}
            />
          </div>
        </section>
      ) : null}
      {ticket.username ? (
        <section className={styles.section}>
          <span className={styles.label}>User</span>
          <div>
            <TagFilterOrTag
              className={styles.tag}
              field="username"
              useFilter={supportsTicketQuery}
              value={ticket.username}
            />
          </div>
        </section>
      ) : null}
      {ticket.user_id ? (
        <section className={styles.section}>
          <span className={styles.label}>User Diagnostics</span>
          <div>
            <Link
              className={cn(styles.link, className)}
              target="_blank"
              to={{
                pathname: `https://www.duolingo.com/diagnostics/user/summary/user_id/${ticket.user_id}`,
              }}
            >
              <Tag value={ticket.user_id.toString()} />
            </Link>
          </div>
        </section>
      ) : null}
    </>
  );

  return (
    <div className={cn(styles.container, className)}>
      <div className={styles.bordered}>
        <div className={styles.content}>
          {content}
          {ticket.data_source === "JIRA" ? null : (
            <IconButton
              className={styles["btn-bug"]}
              icon={imageBug}
              onClick={() => setIsReporting(value => !value)}
              title="Report to Jira/Slack"
            />
          )}
          {onRequestClose ? (
            <IconButton
              className={styles["btn-close"]}
              icon={imageClose}
              onClick={onRequestClose}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default Ticket;
