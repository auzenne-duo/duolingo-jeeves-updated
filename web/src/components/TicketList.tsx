import { format, formatISO, isThisYear, isToday } from "date-fns";
import type { LocationDescriptor } from "history";
import * as React from "react";
import { Link, useLocation } from "react-router-dom";
import { alignNearest } from "web-ui/util/scroll";

import {
  formatCourseId,
  formatReadableDateTime,
  formatScreen,
  getFilterLink,
  getUntruncatedTitle,
} from "../util";
import JiraStatus from "components/JiraStatus";
import PlatformIcon from "components/PlatformIcon";
import Tag from "components/Tag";
import TagFilter from "components/TagFilter";
import type { Props as TagFilterProps } from "components/TagFilter";
import styles from "components/TicketList.scss";

const formatDate = (date: Date) => {
  if (isToday(date)) {
    return format(date, "HH:mm");
  }
  if (isThisYear(date)) {
    return format(date, "d MMM");
  }
  return formatISO(date, { representation: "date" });
};

const LinkOrSpan = ({
  children,
  className,
  to,
  useLink,
}: {
  children: React.ReactNode;
  className?: string;
  to: LocationDescriptor;
  useLink: boolean;
}) =>
  useLink ? (
    <Link className={className} onClick={e => e.stopPropagation()} to={to}>
      {children}
    </Link>
  ) : (
    <span className={className}>{children}</span>
  );

const TagFilterOrTag = ({
  className,
  useFilter,
  value,
  ...rest
}: TagFilterProps & {
  useFilter: boolean;
}) =>
  useFilter ? (
    <TagFilter className={className} value={value} {...rest} />
  ) : (
    <Tag className={className} value={value} />
  );

interface Props {
  onClick?: (ticket: JSONAPI.Ticket) => void;
  selectedId?: string;
  supportsTicketQuery?: boolean;
  tickets: JSONAPI.Ticket[];
}

const TicketList = ({
  onClick,
  selectedId: id,
  supportsTicketQuery = false,
  tickets,
}: Props) => {
  const location = useLocation();

  const currentRowRef = React.useRef<HTMLLIElement>(null);

  React.useEffect(() => {
    if (currentRowRef.current) {
      const bodyStyle = getComputedStyle(document.body);
      const topbarHeight = parseFloat(
        bodyStyle.getPropertyValue("--height-topbar"),
      );
      const margin = parseFloat(bodyStyle.getPropertyValue("--margin"));
      const target = currentRowRef.current.getBoundingClientRect();
      document.documentElement.scrollTop += alignNearest(
        topbarHeight + margin,
        window.innerHeight - margin,
        window.innerHeight - topbarHeight - 2 * margin,
        0,
        0,
        target.top,
        target.bottom,
        target.height,
      );
    }
  }, [id, tickets]);

  return (
    <ul className={styles.list}>
      {tickets.map((t, i) => {
        const date = t.date_time ? new Date(t.date_time) : undefined;
        return (
          <li
            className={styles[`item${t.jeeves_uid === id ? "-selected" : ""}`]}
            key={i}
            onClick={() => onClick?.(t)}
            ref={t.jeeves_uid === id ? currentRowRef : undefined}
          >
            <div className={styles["title-container"]}>
              <span className={styles.title}>{getUntruncatedTitle(t)}</span>
            </div>
            <div className={styles.tags}>
              {t.issue_key ? (
                <Tag className={styles["tag-ipad"]} value={t.issue_key} />
              ) : null}
              {t.course ? (
                <TagFilterOrTag
                  className={styles["tag-ipad"]}
                  field="course"
                  text={formatCourseId(t.course)}
                  useFilter={supportsTicketQuery}
                  value={t.course}
                />
              ) : null}
              {t.screen_content ? (
                <TagFilterOrTag
                  className={styles["tag-ipad"]}
                  field="screen_content"
                  text={formatScreen(t.screen_content)}
                  useFilter={supportsTicketQuery}
                  value={t.screen_content}
                />
              ) : null}
              {t.app_version ? (
                <TagFilterOrTag
                  className={styles["tag-ipad"]}
                  field="app_version"
                  text={
                    t.platform === "Web"
                      ? t.app_version.slice(0, 7)
                      : t.app_version
                  }
                  useFilter={supportsTicketQuery}
                  value={t.app_version}
                />
              ) : null}
              {t.data_source === "JIRA" && t.status ? (
                <LinkOrSpan
                  className={styles["tag-jira"]}
                  to={getFilterLink(location, "status", t.status)}
                  useLink={supportsTicketQuery}
                >
                  <JiraStatus status={t.status} />
                </LinkOrSpan>
              ) : null}
              {t.platform ? (
                <LinkOrSpan
                  className={styles["tag-platform"]}
                  to={getFilterLink(location, "platform", t.platform)}
                  useLink={supportsTicketQuery}
                >
                  <PlatformIcon className={styles.icon} platform={t.platform} />
                </LinkOrSpan>
              ) : t.data_source === "Reddit" ? (
                <LinkOrSpan
                  className={styles["tag-platform"]}
                  to={getFilterLink(location, "data_source", "reddit")}
                  useLink={supportsTicketQuery}
                >
                  <PlatformIcon className={styles.icon} platform="Reddit" />
                </LinkOrSpan>
              ) : t.data_source === "Zendesk" &&
                t.via?.channel === "twitter" ? (
                <LinkOrSpan
                  className={styles["tag-platform"]}
                  to={getFilterLink(location, "via.channel", "twitter")}
                  useLink={supportsTicketQuery}
                >
                  <PlatformIcon className={styles.icon} platform="Twitter" />
                </LinkOrSpan>
              ) : null}
              {date ? (
                <span
                  className={styles.date}
                  title={formatReadableDateTime(date)}
                >
                  {formatDate(date)}
                </span>
              ) : null}
            </div>
          </li>
        );
      })}
    </ul>
  );
};

export default TicketList;
