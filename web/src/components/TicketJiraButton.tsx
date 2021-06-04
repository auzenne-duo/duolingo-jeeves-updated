import * as React from "react";
import { Button } from "web-ui";

import { createJira } from "api";
import JiraIssues from "components/JiraIssues";
import { getUntruncatedTitle } from "util";

interface Props {
  ticket: JSONAPI.Ticket;
}

const TicketJiraButton = ({ ticket }: Props) => {
  const [issueKey, setIssueKey] = React.useState<string>();
  const [submitting, setSubmitting] = React.useState(false);

  const handleClick = async () => {
    setSubmitting(true);
    try {
      const result = await createJira({
        description: `${ticket.body_text ?? ""}${
          ticket.attachments?.length
            ? `\n\nAttachments:\n${ticket.attachments.join("\n")}`
            : ""
        }`,
        generated_description: ticket.duolingo_metadata.raw,
        project:
          ticket.platform === "Android"
            ? "DLAA"
            : ticket.platform === "iOS"
            ? "DLAI"
            : "DLAW",
        summary: getUntruncatedTitle(ticket) ?? "New issue",
      });
      setIssueKey(result.issueKey);
    } finally {
      setSubmitting(false);
    }
  };

  // The component may be reused for different tickets.
  React.useEffect(() => {
    setIssueKey(undefined);
  }, [ticket.jeeves_uid]);

  return issueKey ? (
    <JiraIssues
      issues={[{ key: issueKey, summary: ticket.header_text ?? "New issue" }]}
    />
  ) : (
    <Button
      onClick={handleClick}
      style={{
        // Make the button the same height as the Jira issue component.
        ["--web-ui_button-padding" as string]: "11px 16px",
      }}
      submitting={submitting}
      variant="stroke"
    >
      Create Jira
    </Button>
  );
};

export default TicketJiraButton;
