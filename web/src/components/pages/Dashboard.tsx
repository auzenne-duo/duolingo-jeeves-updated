import { formatDistanceToNow, startOfYesterday } from "date-fns";
import * as React from "react";
import { useParams } from "react-router-dom";

import { getInfo, getSpikes } from "api";
import SpikeTable from "components/SpikeTable";
import Table from "components/Table";
import { useAwaitedValue } from "components/useAwaitedValue";
import usePageView from "components/usePageView";
import AppStateContext from "contexts/AppStateContext";
import { formatReadableDate } from "util";

const Dashboard = () => {
  const { lang } = useParams<{ lang: JSONAPI.LanguageId }>();

  const [, dispatch] = React.useContext(AppStateContext);

  const [info, isLoadingInfo] = useAwaitedValue(
    undefined,
    () => getInfo(lang),
    [lang],
  );

  const [spikes, isLoading] = useAwaitedValue(
    undefined,
    async () =>
      (
        await getSpikes(lang, {
          start_date: startOfYesterday(),
        })
      ).reverse(),
    [lang],
  );

  usePageView();

  React.useEffect(() => {
    if (isLoading || isLoadingInfo) {
      dispatch?.({ type: "LOADING" });
      return () => {
        dispatch?.({ type: "LOADED" });
      };
    }
  }, [isLoading || isLoadingInfo]);

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
            {isLoadingInfo || !info ? null : (
              <td>
                {formatDistanceToNow(info.latest_ticket_timestamp, {
                  addSuffix: true,
                  includeSeconds: true,
                })}
              </td>
            )}
          </tr>
          <tr>
            <th>Last Jeeves deployment</th>
            {isLoadingInfo || !info ? null : (
              <td>{formatReadableDate(info.deployed_timestamp)}</td>
            )}
          </tr>
        </tbody>
      </Table>
    </>
  );
};

export default Dashboard;
