import { formatDistanceToNow, startOfYesterday } from "date-fns";
import * as React from "react";
import { useQuery } from "react-query";
import { useParams } from "react-router-dom";

import { formatReadableDate } from "../../util";
import { getInfo, getSpikes } from "api/jeeves";
import SpikeTable from "components/SpikeTable";
import Table from "components/Table";
import usePageView from "components/usePageView";

const Dashboard = () => {
  const { lang } = useParams<{ lang: JSONAPI.LanguageId }>();

  const spikesStartDate = startOfYesterday();

  const { data: info, isLoading: isLoadingInfo } = useQuery(
    ["info", { lang }],
    () => getInfo(lang),
    {
      staleTime: 60000, // 1m
    },
  );

  const { data: spikes, isLoading } = useQuery(
    ["spikes", { lang, spikesStartDate }],
    () =>
      getSpikes(lang, {
        start_date: spikesStartDate,
      }),
    {
      select: d => d.slice().reverse(),
    },
  );

  usePageView();

  return (
    <>
      <SpikeTable
        date={spikes?.[0]?.date}
        isLoading={isLoading}
        language={lang}
        spikes={isLoading ? [] : spikes?.[0]?.spikes.slice(0, 5) ?? []}
      />
      <Table>
        <tbody>
          <tr>
            <th>Most recent ticket</th>
            {info ? (
              <td>
                {formatDistanceToNow(info.latest_ticket_timestamp, {
                  addSuffix: true,
                  includeSeconds: true,
                })}
              </td>
            ) : isLoadingInfo ? null : (
              <td>Failed to retrieve data.</td>
            )}
          </tr>
          <tr>
            <th>Last Jeeves deployment</th>
            {info ? (
              <td>{formatReadableDate(info.deployed_timestamp)}</td>
            ) : isLoadingInfo ? null : (
              <td>Failed to retrieve data.</td>
            )}
          </tr>
        </tbody>
      </Table>
    </>
  );
};

export default Dashboard;
