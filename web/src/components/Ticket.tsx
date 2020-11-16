import * as React from "react";
import { Button } from "web-ui";

import { Ticket } from "api";
import Table from "components/Table";
import imageClose from "images/x.svg";
import styles from "styles/Ticket.scss";

/**
 * Tries to highlight all instances of a word in the text.
 * Returns the original text if highlighting failed, for
 * example because the generated regex pattern is invalid.
 */
const highlightWord = (str: string, word: string) => {
  try {
    return str.replace(RegExp(`\\b(${word})\\b`, "gi"), "<mark>$1</mark>");
  } catch {
    return str;
  }
};

interface Props {
  highlight?: string;
  onRequestClose?: () => void;
  ticket: Ticket;
}

const Ticket: React.FC<Props> = ({ highlight, onRequestClose, ticket }) => {
  let body = (ticket.body_text ?? "")
    .trim()
    .replace(/\n{3,}/g, "\n\n")
    .replace(/\n/g, "<br />");
  body = highlight ? highlightWord(body, highlight) : body;

  const date = ticket.date_time
    ? new Date(ticket.date_time).toLocaleString()
    : null;

  return (
    <div className={styles.wrap}>
      <Table className={styles.table}>
        <tbody>
          <tr>
            <th>Subject</th>
            <td>{ticket.header_text?.trim()}</td>
          </tr>
          <tr>
            <th>Date</th>
            <td>
              {ticket.data_source === "Zendesk" ? (
                <a
                  href={ticket.links?.[0]}
                  rel="noopener noreferer"
                  target="_blank"
                >
                  {date}
                </a>
              ) : (
                date
              )}
            </td>
          </tr>
          <tr>
            <th>Source</th>
            <td>
              {ticket.data_source === "AppFigures" ? (
                `${ticket.data_source}, ${ticket.store}`
              ) : ticket.data_source === "Zendesk" ? (
                <a
                  href={ticket.links?.[1]}
                  rel="noopener noreferer"
                  target="_blank"
                >
                  {[
                    ticket.via?.source?.from?.name,
                    ticket.via?.source?.from?.address
                      ? `<${ticket.via.source.from.address}>`
                      : undefined,
                    `via ${ticket.via?.channel}`,
                    ticket.data_source,
                  ]
                    .filter(part => part)
                    .join(" ")}
                </a>
              ) : (
                ticket.data_source
              )}
            </td>
          </tr>
          {ticket.data_source === "Zendesk" ? (
            <tr>
              <th>Tags</th>
              <td>
                <div className={styles.tags}>
                  {ticket.priority ? (
                    <span className={styles["tag-priority"]}>
                      {ticket.priority}
                    </span>
                  ) : null}
                  {ticket.tags?.map(tag => (
                    <span className={styles.tag} key={tag}>
                      {tag}
                    </span>
                  ))}
                </div>
              </td>
            </tr>
          ) : null}
          <tr>
            <td
              colSpan={2}
              dangerouslySetInnerHTML={{
                __html: body,
              }}
            />
          </tr>
        </tbody>
      </Table>
      {onRequestClose ? (
        <Button className={styles.close} onClick={onRequestClose}>
          <img src={imageClose} />
        </Button>
      ) : null}
    </div>
  );
};

export default Ticket;
