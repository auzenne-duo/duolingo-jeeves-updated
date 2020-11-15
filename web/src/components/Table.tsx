import cn from "classnames";
import * as React from "react";

import styles from "styles/Table.scss";

interface Props {
  className?: string;
}

const Table: React.FC<Props> = ({ children, className }) => (
  <table className={cn(styles.table, className)}>{children}</table>
);

export default Table;
