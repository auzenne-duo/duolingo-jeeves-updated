import * as React from "react";

import cn from "classnames";
import styles from "components/Table.module.scss";

interface Props {
  children: React.ReactNode;
  className?: string;
}

const Table = ({ children, className }: Props) => (
  <table className={cn(styles.table, className)}>{children}</table>
);

export default Table;
