import * as React from "react";
import { Link, useLocation } from "react-router-dom";

import { getFilterLink } from "../util";
import cn from "classnames";
import Tag from "components/Tag";
import styles from "components/TagFilter.scss";

export interface Props extends React.ComponentProps<typeof Tag> {
  field: string;
}

const TagFilter = ({ className, field, ...tagProps }: Props) => {
  const location = useLocation();
  return (
    <Link
      className={cn(styles.link, className)}
      // Prevent clicking a tag from selecting an item in the tickets list.
      onClick={e => e.stopPropagation()}
      to={getFilterLink(location, field, tagProps.value)}
    >
      <Tag {...tagProps} />
    </Link>
  );
};

export default TagFilter;
