import * as React from "react";
import { useParams } from "react-router-dom";

import { getInfo, getSpikes } from "api";
import { AppDispatch } from "components/App";
import { LanguageId } from "components/LanguagePicker";
import SpikeTable from "components/SpikeTable";
import Table from "components/Table";
import { useAwaitedValue } from "components/useAwaitedValue";
import usePageView from "components/usePageView";

const Dashboard = () => {
  const { lang } = useParams<{ lang: LanguageId }>();

  const dispatch = React.useContext(AppDispatch);

  const [info, isLoadingInfo] = useAwaitedValue(
    undefined,
    () => getInfo(lang),
    [lang],
  );

  const [spikes, isLoading] = useAwaitedValue(
    undefined,
    () => getSpikes(lang),
    [lang],
  );

  const [recentSpikeDate] = Object.keys(spikes ?? {}).slice(-1);
  const recentSpikes = spikes?.[recentSpikeDate];

  const latestTicketDate = info?.latest_ticket_timestamp
    ? new Date(info.latest_ticket_timestamp).toLocaleString()
    : null;
  const deployedAtDate = info?.deployed_timestamp
    ? new Date(info.deployed_timestamp).toLocaleString()
    : null;

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
        date={recentSpikeDate}
        isLoading={isLoading}
        language={lang}
        spikes={isLoading ? [] : recentSpikes?.slice(0, 5) ?? []}
      />
      <Table>
        <tbody>
          <tr>
            <th>Most recent ticket</th>
            {isLoadingInfo ? null : <td>{latestTicketDate}</td>}
          </tr>
          <tr>
            <th>Last Jeeves deployment</th>
            {isLoadingInfo ? null : <td>{deployedAtDate}</td>}
          </tr>
        </tbody>
      </Table>
    </>
  );
};

export default Dashboard;
