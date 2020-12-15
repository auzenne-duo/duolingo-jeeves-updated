import cn from "classnames";
import * as React from "react";
import { LoadingDots } from "web-ui";

import { getJiraDuplicates } from "api";
import CloseButton from "components/CloseButton";
import JiraIssues from "components/JiraIssues";
import Tag from "components/Tag";
import renderTicketSource from "components/renderTicketSource";
import { useAwaitedValue } from "components/useAwaitedValue";
import styles from "styles/Ticket.scss";
import {
  escapeHTML,
  formatAttachment,
  formatCourseId,
  formatPlatform,
  formatReadableDate,
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
  let body = normalizeNewLines(escapeHTML(ticket.body_text ?? ""))
    .trim()
    .replace(/\n/g, "<br />");
  body = highlight ? highlightWord(body, highlight) : body;

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
          {ticket.metadata?.app_version ? (
            <section className={styles.section}>
              <span className={styles.label}>App version</span>
              <div>{ticket.metadata?.app_version}</div>
            </section>
          ) : null}
          {ticket.attachments?.length ? (
            <section className={styles.section}>
              <span className={styles.label}>Attachments</span>
              <div>
                {ticket.attachments.map((url, i) => (
                  <a className={styles.attachment} href={url} key={i}>
                    {formatAttachment(url)}
                  </a>
                ))}
              </div>
            </section>
          ) : null}
          {ticket.metadata?.course ? (
            <section className={styles.section}>
              <span className={styles.label}>Course</span>
              <div>{formatCourseId(ticket.metadata?.course)}</div>
            </section>
          ) : null}
          {ticket.metadata?.full_story_url ? (
            <section className={styles.section}>
              <span className={styles.label}>FullStory recording</span>
              <div>
                <a href={ticket.metadata.full_story_url}>View session</a>
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
          {ticket.metadata?.os_version ? (
            <section className={styles.section}>
              <span className={styles.label}>OS version</span>
              <div>{ticket.metadata.os_version}</div>
            </section>
          ) : null}
          {ticket.metadata?.platform ? (
            <section className={styles.section}>
              <span className={styles.label}>Platform</span>
              <div>{formatPlatform(ticket.metadata.platform)}</div>
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
                <Tag
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
          {ticket.metadata?.screen_name ? (
            <section className={styles.section}>
              <span className={styles.label}>Screen</span>
              <div>{ticket.metadata.screen_name}</div>
            </section>
          ) : null}
          {ticket.metadata?.screen ? (
            <section className={styles.section}>
              <span className={styles.label}>Screen dimensions</span>
              <div>{ticket.metadata.screen}</div>
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
                  <Tag className={styles.tag} value={tag} key={tag} />
                ))}
              </div>
            </section>
          ) : null}
          {ticket.metadata?.ui_language ? (
            <section className={styles.section}>
              <span className={styles.label}>UI language</span>
              <div>{ticket.metadata.ui_language}</div>
            </section>
          ) : null}
          {ticket.metadata?.username ? (
            <section className={styles.section}>
              <span className={styles.label}>User</span>
              <div>{ticket.metadata.username}</div>
            </section>
          ) : null}
          {onRequestClose ? <CloseButton onClick={onRequestClose} /> : null}
        </div>
      </div>
    </div>
  );
};

export default Ticket;
