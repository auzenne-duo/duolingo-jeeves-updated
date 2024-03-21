import { format, formatISO, isThisYear, isToday } from "date-fns";
import type { LocationDescriptor } from "history";
import * as React from "react";
import { Link, useLocation } from "react-router-dom";

import {
  formatCourseId,
  formatPriority,
  formatReadableDateTime,
  formatScreen,
  getFilterLink,
  getUntruncatedTitle,
  staticAssertNever,
} from "../util";
import JiraStatus from "components/JiraStatus";
import PlatformIcon from "components/PlatformIcon";
import Tag from "components/Tag";
import TagFilterOrTag from "components/TagFilterOrTag";
import styles from "components/TicketListItem.module.scss";
import useIsTablet from "components/useIsTablet";

export type RenderableTag =
  | "app_version"
  | "child_issues"
  | "course"
  | "date"
  | "duplicates"
  | "issue_key"
  | "platform"
  | "priority"
  | "screen_content"
  | "status";

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

interface Props {
  onClick?: () => void;
  selected?: boolean;
  showTags?: RenderableTag[];
  supportsTicketQuery?: boolean;
  ticket: JSONAPI.Ticket;
}

const TicketListItem = (
  {
    onClick,
    selected,
    showTags: _showTags,
    supportsTicketQuery = false,
    ticket: t,
  }: Props,
  ref: React.Ref<HTMLLIElement>,
) => {
  const isTablet = useIsTablet();
  const location = useLocation();

  const date = t.date_time ? new Date(t.date_time) : undefined;
  const duplicates = t.linked_duplicate_keys?.length ?? 0;
  const isParentBug = !!t.child_issues?.length;

  const showTags: RenderableTag[] =
    _showTags ??
    (isParentBug
      ? ["issue_key", "child_issues", "status", "platform", "date"]
      : isTablet
        ? [
            "issue_key",
            "course",
            "screen_content",
            "app_version",
            "duplicates",
            "status",
            "platform",
            "date",
          ]
        : ["status", "platform", "date"]);

  return (
    <li
      className={styles[`item${selected ? "-selected" : ""}`]}
      onClick={onClick}
      ref={ref}
    >
      <div className={styles["title-container"]}>
        <span className={styles.title}>{getUntruncatedTitle(t)}</span>
      </div>
      <div className={styles.tags}>
        {showTags.map(tag => (
          <React.Fragment key={tag}>
            {(() => {
              switch (tag) {
                case "app_version":
                  return t.app_version ? (
                    <TagFilterOrTag
                      field="app_version"
                      text={
                        t.platform === "Web"
                          ? t.app_version.slice(0, 7)
                          : t.app_version
                      }
                      useFilter={supportsTicketQuery}
                      value={t.app_version}
                    />
                  ) : null;
                case "child_issues":
                  return t.child_issues?.length ? (
                    <Tag value={`${t.child_issues?.length} reports`} />
                  ) : null;
                case "course":
                  return t.course ? (
                    <TagFilterOrTag
                      field="course"
                      text={formatCourseId(t.course)}
                      useFilter={supportsTicketQuery}
                      value={t.course}
                    />
                  ) : null;
                case "date":
                  return date ? (
                    <span
                      className={styles.date}
                      title={formatReadableDateTime(date)}
                    >
                      {formatDate(date)}
                    </span>
                  ) : null;
                case "duplicates":
                  return duplicates ? (
                    <Tag
                      value={`${duplicates} ${
                        duplicates === 1 ? "duplicate" : "duplicates"
                      }`}
                    />
                  ) : null;
                case "issue_key":
                  return t.issue_key ? (
                    <a
                      className={styles["tag-link"]}
                      href={`https://duolingo.atlassian.net/browse/${encodeURIComponent(
                        t.issue_key,
                      )}`}
                      onClick={e => e.stopPropagation()}
                      rel="noreferrer"
                      target="_blank"
                    >
                      <Tag showLinkIcon={true} value={t.issue_key} />
                    </a>
                  ) : null;
                case "platform":
                  return t.platform ? (
                    <LinkOrSpan
                      className={styles["tag-link"]}
                      to={getFilterLink(location, "platform", t.platform)}
                      useLink={supportsTicketQuery}
                    >
                      <PlatformIcon
                        className={styles.icon}
                        platform={t.platform}
                      />
                    </LinkOrSpan>
                  ) : t.data_source === "Reddit" ? (
                    <LinkOrSpan
                      className={styles["tag-link"]}
                      to={getFilterLink(location, "data_source", "Reddit")}
                      useLink={supportsTicketQuery}
                    >
                      <PlatformIcon className={styles.icon} platform="Reddit" />
                    </LinkOrSpan>
                  ) : t.data_source === "Zendesk" &&
                    t.via?.channel === "twitter" ? (
                    <LinkOrSpan
                      className={styles["tag-link"]}
                      to={getFilterLink(location, "via.channel", "twitter")}
                      useLink={supportsTicketQuery}
                    >
                      <PlatformIcon
                        className={styles.icon}
                        platform="Twitter"
                      />
                    </LinkOrSpan>
                  ) : null;
                case "priority":
                  return t.priority && t.priority !== "Unprioritized" ? (
                    <TagFilterOrTag
                      field="priority"
                      isPriority={true}
                      text={formatPriority(t.priority)}
                      useFilter={supportsTicketQuery}
                      value={t.priority}
                    />
                  ) : null;
                case "screen_content":
                  return t.screen_content ? (
                    <TagFilterOrTag
                      field="screen_content"
                      text={formatScreen(t.screen_content)}
                      useFilter={supportsTicketQuery}
                      value={t.screen_content}
                    />
                  ) : null;
                case "status":
                  return t.data_source === "JIRA" && t.status ? (
                    <LinkOrSpan
                      className={styles["tag-link"]}
                      to={getFilterLink(location, "status", t.status)}
                      useLink={supportsTicketQuery}
                    >
                      <JiraStatus status={t.status} />
                    </LinkOrSpan>
                  ) : null;
                default:
                  staticAssertNever(tag);
                  return null;
              }
            })()}
          </React.Fragment>
        ))}
      </div>
    </li>
  );
};

export default React.forwardRef(TicketListItem);
