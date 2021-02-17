import cn from "classnames";
import * as React from "react";
import { Link, useLocation } from "react-router-dom";
import { LoadingDots } from "web-ui";

import { getJiraDuplicates } from "api";
import CloseButton from "components/CloseButton";
import JiraIssues from "components/JiraIssues";
import PlatformIcon from "components/PlatformIcon";
import TagFilter from "components/TagFilter";
import renderTicketSource from "components/renderTicketSource";
import { useAwaitedValue } from "components/useAwaitedValue";
import styles from "styles/Ticket.scss";
import {
  escapeElasticQuery,
  escapeHTML,
  formatAttachment,
  formatCourseId,
  formatReadableDate,
  formatScreen,
  highlightWord,
  normalizeNewLines,
} from "util";

interface Props {
  className?: string;
  highlight?: string;
  onRequestClose?: () => void;
  ticket: JSONAPI.Ticket;
}

const Ticket: React.FC<Props> = ({
  className,
  highlight,
  onRequestClose,
  ticket,
}) => {
  const location = useLocation();

  let body = normalizeNewLines(escapeHTML(ticket.body_text ?? ""))
    .trim()
    .replace(/\n/g, "<br />");
  body = highlight ? highlightWord(body, highlight) : body;

  const dateTime =
    ticket.data_source === "JIRA" ? ticket.creation_date : ticket.date_time;

  const duplicates = ticket.issue_links?.filter(
    link => link.type.name === "Duplicate",
  );

  const [
    potentialDuplicates,
    isLoadingPotentialDuplicates,
  ] = useAwaitedValue(
    undefined,
    async () =>
      ticket.issue_key ? await getJiraDuplicates(ticket.issue_key) : [],
    [ticket.issue_key],
  );

  const getFilterLink = (field: string, value: string) => {
    const params = new URLSearchParams(location.search);
    params.delete("page");
    params.set("q", `${field}:"${escapeElasticQuery(value)}"`);
    return {
      ...location,
      search: params.toString(),
    };
  };

  return (
    <div className={cn(styles.container, className)}>
      <div className={styles.bordered}>
        <div className={styles.content}>
          {ticket.header_text ? <h2>{ticket.header_text}</h2> : null}
          {body ? (
            <section className={styles.section}>
              <span className={styles.label}>Description</span>
              <div
                dangerouslySetInnerHTML={{
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
                <JiraIssues issues={duplicates} />
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
                <Link to={getFilterLink("platform", ticket.platform)}>
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
                  <JiraIssues issues={potentialDuplicates} />
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
          {dateTime ? (
            <section className={styles.section}>
              <span className={styles.label}>Reported at</span>
              <div>{formatReadableDate(new Date(dateTime))}</div>
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
                <JiraIssues issues={[ticket]} />
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
