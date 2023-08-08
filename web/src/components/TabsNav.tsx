import * as React from "react";
import { NavLink } from "react-router-dom";

import cn from "classnames";
import styles from "components/TabsNav.scss";

interface Tab {
  href: string;
  isActive: boolean;
  name: string;
}

interface Props {
  className?: string;
  tabs: Tab[];
}

const TabsNav = ({ className, tabs }: Props) => (
  <nav className={cn(styles.wrap, className)}>
    {tabs.map(t => (
      <span className={styles.tab} key={t.name}>
        <NavLink
          activeClassName={styles["link-active"]}
          className={styles.link}
          isActive={() => t.isActive}
          to={t.href}
        >
          {t.name}
        </NavLink>
      </span>
    ))}
  </nav>
);

export default TabsNav;
