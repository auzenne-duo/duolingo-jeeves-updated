import { addDays, formatISO } from "date-fns";
import * as React from "react";
import { Link } from "react-router-dom";

import { encodeURLSearchParams } from "../util";
import ConfirmButton from "components/ConfirmButton";
import EmailBetaButton from "components/EmailBetaButton";
import ExperimentsList from "components/ExperimentsList";
import FixedToggle from "components/FixedToggle";
import Table from "components/Table";
import useIsMobile from "components/useIsMobile";
import styles from "styles/SpikeTable.scss";

interface Props {
  date: Date | undefined;
  isLoading?: boolean;
  language: JSONAPI.LanguageId;
  linkFilter?: JSONAPI.ShakeToReportCategory;
  onlyBugs?: boolean;
  spikeCategory?: string;
  spikes: JSONAPI.SpikeWord[];
}

const SpikeTable = ({
  date,
  isLoading,
  language,
  linkFilter,
  onlyBugs,
  spikeCategory,
  spikes,
}: Props) => {
  const spikeDetectorParams = new URLSearchParams();
  const isMobile = useIsMobile();
  if (date) {
    spikeDetectorParams.set("to", addDays(date, 1).toJSON());
    spikeDetectorParams.set("from", date.toJSON());
  }
  return (
    <Table className={styles.table}>
      <thead>
        <tr>
          <th colSpan={isMobile ? 2 : 5}>
            <Link
              to={`/${language}/spike?${encodeURLSearchParams(
                spikeDetectorParams,
              )}`}
            >
              Trending words on{" "}
              {date ? formatISO(date, { representation: "date" }) : null} (
              {language})
            </Link>
          </th>
        </tr>
        <tr>
          <th>Word</th>
          <th>Summary</th>
          <th className={styles["hide-mobile-column"]}>Confirmed</th>
          <th className={styles["hide-mobile-column"]}>Fixed</th>
          <th className={styles["hide-mobile-column"]}>Email Beta</th>
        </tr>
      </thead>
      <tbody>
        {spikes
          .filter(spike => !onlyBugs || spike.is_bug)
          .map(spike => {
            const params = new URLSearchParams();
            if (linkFilter) {
              params.set("filter", linkFilter);
            }
            if (spikeCategory) {
              params.set("spike-category", spikeCategory);
            }
            params.set("q", spike.word);
            return (
              <tr key={spike.word}>
                <td>
                  <Link
                    to={`/${language}/analysis?${encodeURLSearchParams(
                      params,
                    )}&use-lemmas=true`}
                  >
                    {spike.word}
                  </Link>
                </td>
                <td>
                  {spike.summary && (
                    <div className={styles.summary}>{spike.summary}</div>
                  )}
                  {spike.experiment_spikes?.length > 0 && (
                    <>
                      <div>Common experiment conditions:</div>
                      <ExperimentsList
                        experimentSpikes={spike.experiment_spikes}
                      />
                    </>
                  )}
                </td>
                <td className={styles["hide-mobile-column"]}>
                  <ConfirmButton spike={spike} />
                </td>
                <td className={styles["hide-mobile-column"]}>
                  <FixedToggle spike={spike} />
                </td>
                <td className={styles["hide-mobile-column"]}>
                  <EmailBetaButton spike={spike} />
                </td>
              </tr>
            );
          })}
        {!spikes.length && !isLoading ? (
          <tr>
            <td colSpan={isMobile ? 2 : 5}>
              No data is available for this date.
            </td>
          </tr>
        ) : null}
      </tbody>
    </Table>
  );
};

export default SpikeTable;
