import * as React from "react";

import Tickets from "components/Tickets";
import SearchExample from "components/time-series-analyzer/SearchExample";
import styles from "components/time-series-analyzer/TimeSeriesAnalyzer.scss";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";

const EXAMPLES = [
  "/crash(es|ing|ed)/ OR /freez(e|es|ing)/ OR frozen OR /stop(s|ping|ped)/ unresponsive OR unusable OR slow",
  'I (hate OR "don\'t like")',
  '/refund(ed)?/ OR "money back"',
  "/unlock(ed)?/",
  "fix",
  'how ("do I" OR "can I" OR to)',
  '(latest (update OR version)) OR "last update"',
  "(please (include OR add)) OR /lack(ing|s)/ OR limited",
  "/(chat)?bot(s)?/ OR tutor",
  "pearson OR /class(room|rooms)?/ OR /(student|teacher|assignment|homework|school)(s)?/",
  "/(disappoint|annoy|frustrat|irritat)(ed|ing)/ OR terrible OR horrible OR worst OR bad OR unfortunately OR ridiculous OR /sad(ly)?/",
];

const TimeSeriesAnalyzer = () => {
  const search = useSearchParams();

  const query = search.get("q") ?? "";

  useDocumentTitle("Time Series Analyzer");
  usePageView();

  React.useEffect(() => {
    ga("send", "event", {
      eventAction: "search",
      eventCategory: "Tickets",
      eventLabel: query,
    });
  }, [query]);

  return query ? (
    <Tickets hasTrend={true} monthsAgo={3} />
  ) : (
    <div className={styles.explanation}>
      <span>
        You can use AND/OR with parentheses to specify queries with multiple
        words:
      </span>
      <ul>
        <li>
          <SearchExample query="inappropriate OR offensive" />
        </li>
        <li>
          <SearchExample query="stuck OR (I AND (can't OR couldn't))" />
        </li>
      </ul>
      <span>Use + and - to force a word to be included or excluded:</span>
      <ul>
        <li>
          <SearchExample query="+please add -Icelandic language" />
        </li>
      </ul>
      <span>
        Forward slashes will let you specify regular expressions, but they can
        only match single words:
      </span>
      <ul>
        <li>
          <SearchExample query="/(freeze|frozen|stopped|unresponsive)/" />
        </li>
        <li>
          <SearchExample query="/[0-9]{3,4}/ AND /day[s]?/ AND streak" />
        </li>
      </ul>
      <span>
        Since Jeeves searches per-word at word level, the following are
        equivalent:
      </span>
      <ul>
        <li>
          <SearchExample query="like need want" />
        </li>
        <li>
          <SearchExample query="like OR need OR want" />
        </li>
        <li>
          <SearchExample query="/(like|need|want)/" />
        </li>
      </ul>
      <span>
        Double quotes will let you search for a specific sequence of words:
      </span>
      <ul>
        <li>
          <SearchExample query='"lost my streak"' />
        </li>
        <li>
          <SearchExample query='"how come"' />
        </li>
      </ul>
      <span>
        You can specify a field to search by, if you have the full name of the
        field. For example, these queries will find tickets for particular app
        versions on iOS and Web, respectively, and tickets from Luis707110 on
        iOS:
        <ul>
          <li>
            <SearchExample query='app_version:"6.100.0.3"' />
          </li>
          <li>
            <SearchExample query='app_version:"1d5ab12bdfe724c626843f3db7b29bcb0e52618a"' />
          </li>
          <li>
            <SearchExample query='username:"Luis707110" AND platform:"iOS"' />
          </li>
        </ul>
      </span>
      <span>Here are some other search suggestions:</span>
      <ul>
        {EXAMPLES.map((q, i) => (
          <li key={i}>
            <SearchExample query={q} />
          </li>
        ))}
      </ul>
      <span>
        The &quot;Use lemmas&quot; toggle will let you search the lemmatized
        wordbanks of the tickets.
      </span>
    </div>
  );
};

export default TimeSeriesAnalyzer;
