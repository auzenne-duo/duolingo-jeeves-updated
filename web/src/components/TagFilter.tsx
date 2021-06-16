import * as React from "react";
import { Link, useLocation } from "react-router-dom";

import Tag from "components/Tag";
import { getFilterLink } from "util";

interface Props extends React.ComponentProps<typeof Tag> {
  field: string;
}

const TagFilter = ({ field, ...tagProps }: Props) => {
  const location = useLocation();
  return (
    <Link
      // Prevent clicking a tag from selecting an item in the Issue Discovery list.
      onClick={e => e.stopPropagation()}
      to={getFilterLink(location, field, tagProps.value)}
    >
      <Tag {...tagProps} />
    </Link>
  );
};

export default TagFilter;
