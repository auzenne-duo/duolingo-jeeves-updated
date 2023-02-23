import React from "react";
import { Link } from "react-router-dom";

import { encodeURLSearchParams } from "../util";
import SortTable from "components/SortTable";
import type { Column } from "components/SortTable";

interface Props {
  language: JSONAPI.LanguageId;
  linkFilter?: JSONAPI.ShakeToReportCategory;
  spikeStats: JSONAPI.SpikeStats;
}

const SpikeWordStatsTable = ({ language, linkFilter, spikeStats }: Props) => {
  const confirmedColumn: Column<JSONAPI.SpikeWordStats> = {
    getCell: m => m.num_confirmed,
    getValue: m => m.num_confirmed,
    header: "Number confirmed",
  };

  const datesColumn: Column<JSONAPI.SpikeWordStats> = {
    getCell: m => m.dates.join(", "),
    getValue: m => m.dates.join(", "),
    header: "Dates",
  };

  const percentColumn: Column<JSONAPI.SpikeWordStats> = {
    getCell: m => `${Math.round((100 * m.num_confirmed) / m.total)}%`,
    getValue: m => Math.round((100 * m.num_confirmed) / m.total),
    header: "Percent",
  };

  const termsColumn: Column<JSONAPI.SpikeWordStats> = {
    getCell: m =>
      m.terms
        .map<React.ReactNode>(term => {
          const params = new URLSearchParams();
          if (linkFilter) {
            params.set("filter", linkFilter);
          }
          params.set("q", term);
          return (
            <Link
              key={term}
              to={`/${language}/analysis?${encodeURLSearchParams(params)}`}
            >
              {term}
            </Link>
          );
        })
        .reduce((prev, curr) => [prev, ", ", curr]),
    getValue: m => m.terms.join(", "),
    header: "Terms",
  };

  const totalColumn: Column<JSONAPI.SpikeWordStats> = {
    getCell: m => m.total,
    getValue: m => m.total,
    header: "Total",
  };

  const statColumns = [
    termsColumn,
    datesColumn,
    confirmedColumn,
    totalColumn,
    percentColumn,
  ];
  return <SortTable columns={statColumns} data={spikeStats.word_count} />;
};

export default SpikeWordStatsTable;
