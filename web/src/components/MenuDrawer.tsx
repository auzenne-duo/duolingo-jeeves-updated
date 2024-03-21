import * as React from "react";
import { useClickOutside } from "web-ui";

import styles from "components/MenuDrawer.module.scss";
import Sidebar from "components/Sidebar";

const WIDTH_APP_MAX = 1140;
const WIDTH_MENU = 270;

export const canFitMenuAndContent = () =>
  (window.innerWidth - WIDTH_APP_MAX) / 2 >= WIDTH_MENU;

interface Props {
  isOpen: boolean;
  onRequestClose?: () => void;
}

const MenuDrawer = ({ isOpen, onRequestClose }: Props) => {
  const ref = React.useRef<HTMLDivElement>(null);

  const handleImplicitClose = () => {
    // If there's space to show the menu together with the contents,
    // we keep it open unless the user explicitly clicks the close button.
    if (!canFitMenuAndContent()) {
      onRequestClose?.();
    }
  };

  useClickOutside({
    disabled: !isOpen,
    onClick: handleImplicitClose,
    ref,
  });

  return (
    <div className={styles[`wrap${isOpen ? "-open" : ""}`]} ref={ref}>
      <Sidebar onItemClick={handleImplicitClose} />
      <footer className={styles.footer} />
    </div>
  );
};

export default MenuDrawer;
