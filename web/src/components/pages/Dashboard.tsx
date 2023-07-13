import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow, startOfYesterday } from "date-fns";
import * as React from "react";
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

  const { data: spikesByDate, isLoading } = useQuery(
    ["spikes", { spikesStartDate }],
    () =>
      getSpikes(undefined, {
        start_date: spikesStartDate,
      }),
    {
      select: d => {
        d.reverse();
        const spikes = [];
        for (const dateResponse of d ?? []) {
          const langToSpikes = new Map<
            JSONAPI.LanguageId,
            JSONAPI.SpikeDataResponse
          >();
          for (const spike of dateResponse?.spikes ?? []) {
            const language = spike.lang as JSONAPI.LanguageId;
            if (!langToSpikes.has(language)) {
              langToSpikes.set(language, {
                date: dateResponse.date,
                spikes: [],
              });
            }
            langToSpikes.get(language)?.spikes.push(spike);
          }
          spikes.push(langToSpikes);
        }
        return spikes;
      },
    },
  );

  usePageView();

  return (
    <>
      {spikesByDate?.length ? (
        spikesByDate.map(langToSpikes =>
          [...langToSpikes.keys()].map(language => (
            <SpikeTable
              date={langToSpikes.get(language)?.date}
              key={`${language}-${langToSpikes.get(language)?.date}`}
              language={language}
              spikes={langToSpikes.get(language)?.spikes.slice(0, 5) ?? []}
            />
          )),
        )
      ) : (
        <SpikeTable
          date={spikesStartDate}
          isLoading={isLoading}
          language={lang}
          spikes={[]}
        />
      )}
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
