import * as React from "react";

import Tag from "components/Tag";
import type { Props as TagFilterProps } from "components/TagFilter";
import TagFilter from "components/TagFilter";

interface Props extends TagFilterProps {
  useFilter: boolean;
}

const TagFilterOrTag = ({
  className,
  isPriority,
  useFilter,
  value,
  ...rest
}: Props) =>
  useFilter ? (
    <TagFilter
      className={className}
      isPriority={isPriority}
      value={value}
      {...rest}
    />
  ) : (
    <Tag className={className} isPriority={isPriority} value={value} />
  );

export default TagFilterOrTag;
