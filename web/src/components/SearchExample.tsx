import * as React from "react";
import { Link } from "react-router-dom";

import styles from "styles/SearchExample.scss";

interface Props {
  query: string;
}

const SearchExample: React.FC<Props> = ({ query }) => (
  <Link className={styles.link} to={`?q=${encodeURIComponent(query)}`}>
    <code>{query}</code>
  </Link>
);

export default SearchExample;
