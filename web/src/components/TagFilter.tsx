import * as React from "react";
import { Link, useLocation } from "react-router-dom";

import Tag from "components/Tag";
import { escapeElasticQuery } from "util";

interface Props extends React.ComponentProps<typeof Tag> {
  field: string;
}

const TagFilter = ({ field, ...tagProps }: Props) => {
  const location = useLocation();

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
    <Link to={getFilterLink(field, tagProps.value)}>
      <Tag {...tagProps} />
    </Link>
  );
};

export default TagFilter;
