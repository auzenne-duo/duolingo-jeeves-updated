import cn from "classnames";
import * as React from "react";
import { LegacyButton } from "web-ui/legacy";

import styles from "components/NamedSection.module.scss";
import imageCaret from "images/caret.svg";

interface Props {
  children: React.ReactNode;
  className?: string;
  collapsible?: boolean;
  layout?: "grid";
  name: string;
}

const NamedSection = ({
  children,
  className,
  collapsible,
  layout,
  name,
}: Props) => {
  const [isOpen, setIsOpen] = React.useState(false);
  return (
    <section className={cn(styles.wrap, className)}>
      {collapsible ? (
        <LegacyButton
          className={styles.toggle}
          onClick={() => setIsOpen(value => !value)}
        >
          <span>{name}</span>
          <img
            alt={isOpen ? "Hide section" : "Show section"}
            className={isOpen ? styles["caret-up"] : styles.caret}
            src={imageCaret}
          />
        </LegacyButton>
      ) : (
        <div className={styles.name}>{name}</div>
      )}
      {collapsible && !isOpen ? null : layout === "grid" ? (
        <div className={styles.grid}>{children}</div>
      ) : (
        children
      )}
    </section>
  );
};

export default NamedSection;
