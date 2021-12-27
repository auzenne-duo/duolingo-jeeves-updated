import {
  escapeHTML,
  formatAttachment,
  formatCourseId,
  formatReadableDate,
  formatScreen,
  getFilterLink,
  highlightWord,
  normalizeNewLines,
} from "util";

import * as React from "react";
import { useQuery } from "react-query";
import { Link, useLocation } from "react-router-dom";
import { LoadingDots } from "web-ui";

import { getJiraDuplicates } from "api";
import cn from "classnames";
import CloseButton from "components/CloseButton";
import JiraIssues from "components/JiraIssues";
import PlatformIcon from "components/PlatformIcon";
import TagFilter from "components/TagFilter";
import TicketJiraButton from "components/TicketJiraButton";
import renderTicketSource from "components/renderTicketSource";
import styles from "styles/Ticket.scss";

interface Props {
  className?: string;
  highlight?: string;
  onRequestClose?: () => void;
  ticket: JSONAPI.Ticket;
}

// eslint-disable-next-line complexity
const Ticket = ({ className, highlight, onRequestClose, ticket }: Props) => {
  const location = useLocation();

  let body = normalizeNewLines(escapeHTML(ticket.body_text ?? ""))
    .trim()
    .replace(/\n/g, "<br />");
  body = highlight ? highlightWord(body, highlight) : body;

  const duplicates = ticket.issue_links?.filter(
    link => link.type.name === "Duplicate",
  );

  const { data: potentialDuplicates, isLoading: isLoadingPotentialDuplicates } =
    useQuery(
      ["jira-duplicates", { issueKey: ticket.issue_key }],
      () => getJiraDuplicates(ticket.issue_key as string),
      {
        enabled: !!ticket.issue_key,
      },
    );

  return (
    <div className={cn(styles.container, className)}>
      <div className={styles.bordered}>
        <div className={styles.content}>
          <h2>{ticket.header_text ?? "(No title)"}</h2>
          {(ticket.platform === "Android" || ticket.platform === "iOS") &&
          ticket.shake_to_report_category === "EXTERNAL" ? (
            <section className={styles.section}>
              <TicketJiraButton ticket={ticket} />
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
                <TagFilter
                  className={styles.tag}
                  field="app_version"
                  value={ticket.app_version}
                />
              </div>
            </section>
          ) : null}
          {ticket.attachments?.length || ticket.fullstory_url ? (
            <section className={styles.section}>
              <span className={styles.label}>Attachments</span>
              <div className={styles.attachments}>
                {ticket.attachments?.map((url, i) => (
                  <a href={url} key={i}>
                    {formatAttachment(url)}
                  </a>
                ))}
                {ticket.fullstory_url ? (
                  <a href={ticket.fullstory_url}>FullStory recording</a>
                ) : null}
              </div>
            </section>
          ) : null}
          {ticket.components?.length ? (
            <section className={styles.section}>
              <span className={styles.label}>Components</span>
              <div>
                {ticket.components?.map(c => (
                  <TagFilter
                    className={styles.tag}
                    field="components"
                    key={c}
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
                <TagFilter
                  className={styles.tag}
                  field="course"
                  text={formatCourseId(ticket.course)}
                  value={ticket.course}
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
                <TagFilter
                  className={styles.tag}
                  field="os_version"
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
                {isLoadingPotentialDuplicates ||
                !potentialDuplicates?.length ? (
                  <div className={styles["loading-container"]}>
                    <span
                      className={
                        isLoadingPotentialDuplicates
                          ? styles.invisible
                          : undefined
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
                <TagFilter
                  className={styles.tag}
                  field="priority"
                  isPriority={["high", "highest", "urgent"].includes(
                    ticket.priority.toLowerCase(),
                  )}
                  value={ticket.priority}
                />
              </div>
            </section>
          ) : null}
          {ticket.date_time ? (
            <section className={styles.section}>
              <span className={styles.label}>Reported at</span>
              <div>{formatReadableDate(new Date(ticket.date_time))}</div>
            </section>
          ) : null}
          {ticket.screen_content ? (
            <section className={styles.section}>
              <span className={styles.label}>Screen</span>
              <div>
                <TagFilter
                  className={styles.tag}
                  field="screen_content"
                  text={formatScreen(ticket.screen_content)}
                  value={ticket.screen_content}
                />
              </div>
            </section>
          ) : null}
          {ticket.screen_size ? (
            <section className={styles.section}>
              <span className={styles.label}>Screen dimensions</span>
              <div>
                <TagFilter
                  className={styles.tag}
                  field="screen_size"
                  value={ticket.screen_size}
                />
              </div>
            </section>
          ) : null}
          <section className={styles.section}>
            <span className={styles.label}>Source</span>
            <div>
              {ticket.data_source === "JIRA" ? (
                <JiraIssues
                  issues={[
                    {
                      key: ticket.issue_key as string,
                      status: ticket.status as string,
                      summary: ticket.header_text as string,
                    },
                  ]}
                />
              ) : (
                renderTicketSource(ticket)
              )}
            </div>
          </section>
          {ticket.tags?.length ? (
            <section className={styles.section}>
              <span className={styles.label}>Tags</span>
              <div className={styles.tags}>
                {ticket.tags?.map(tag => (
                  <TagFilter
                    className={styles.tag}
                    field="tags"
                    key={tag}
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
                <TagFilter
                  className={styles.tag}
                  field="ui_language"
                  value={ticket.ui_language}
                />
              </div>
            </section>
          ) : null}
          {ticket.username ? (
            <section className={styles.section}>
              <span className={styles.label}>User</span>
              <div>
                <TagFilter
                  className={styles.tag}
                  field="username"
                  value={ticket.username}
                />
              </div>
            </section>
          ) : null}
          {onRequestClose ? <CloseButton onClick={onRequestClose} /> : null}
        </div>
      </div>
    </div>
  );
};

export default Ticket;
