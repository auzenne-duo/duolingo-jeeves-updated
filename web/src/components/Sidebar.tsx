import * as React from "react";
import { NavLink, useHistory, useLocation, useParams } from "react-router-dom";

import LanguagePicker from "components/LanguagePicker";
import styles from "styles/Sidebar.scss";

const LinkItem = ({
  children,
  ...rest
}: React.ComponentProps<typeof NavLink>) => (
  <NavLink
    activeClassName={styles["item-active"]}
    className={styles.item}
    exact={true}
    {...rest}
  >
    {children}
  </NavLink>
);

interface Props {
  onItemClick?: React.MouseEventHandler;
}

const Sidebar = ({ onItemClick }: Props) => {
  const history = useHistory();
  const location = useLocation();
  const { lang } = useParams<{ lang: JSONAPI.LanguageId }>();

  return (
    <nav className={styles.wrap}>
      <div className={styles["item-language"]}>
        <LanguagePicker
          className={styles.language}
          onChange={newValue => {
            // Replace the language part of the URL, which
            // is the first part of the path. This also unsets
            // any search parameters. The assumption is that
            // search parameters for one language don't make
            // sense in the other.
            const parts = location.pathname.split("/");
            parts[1] = newValue;
            history.push(parts.join("/"));
          }}
          value={lang}
        />
      </div>
      <LinkItem onClick={onItemClick} to={`/${lang}`}>
        Dashboard
      </LinkItem>
      <LinkItem onClick={onItemClick} to={`/${lang}/discovery`}>
        Issue Discovery
      </LinkItem>
      <LinkItem
        onClick={onItemClick}
        title="Ask free-text questions to GPT about Jeeves documents."
        to={`/${lang}/gpt-search`}
      >
        GPT Search (beta)
      </LinkItem>
      <LinkItem
        onClick={onItemClick}
        title="Browse the list of trending words where the volume of matched tickets spiked."
        to={`/${lang}/spike`}
      >
        Spike Detector
      </LinkItem>
      <LinkItem
        onClick={onItemClick}
        title="See how many reported spikewords were confirmed bugs and how often spikewords appear."
        to={`/${lang}/spike-stats`}
      >
        Spike Stats
      </LinkItem>
      <LinkItem
        onClick={onItemClick}
        title="Visualize Zendesk tickets over time with a keyword filter."
        to={`/${lang}/analysis`}
      >
        Time Series Analyzer
      </LinkItem>
    </nav>
  );
};

export default Sidebar;
