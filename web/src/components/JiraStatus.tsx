import cn from "classnames";
import * as React from "react";

import styles from "styles/JiraStatus.scss";

const getColor = (status: string): "blue" | "gray" | "green" => {
  switch (status.toLowerCase()) {
    case "in code review":
    case "in design":
    case "in development":
    case "in progress":
    case "in testing":
    case "merged before qa":
    case "ready for development":
    case "ready for merge":
      return "blue";
    case "closed":
    case "done":
    case "merged":
      return "green";
  }
  return "gray";
};

interface Props {
  className?: string;
  status: string;
}

const JiraStatus: React.FC<Props> = ({ className, status }) => (
  <span className={cn(styles[getColor(status)], className)}>{status}</span>
);

export default JiraStatus;
