import * as React from "react";
import { useParams } from "react-router-dom";

import { getInfo, getSpikes } from "api";
import { LanguageId } from "components/LanguagePicker";
import Loading from "components/Loading";
import SpikeTable from "components/SpikeTable";
import Table from "components/Table";
import { useAwaitedValue } from "components/useAwaitedValue";
import usePageView from "components/usePageView";

const Dashboard = () => {
  const { lang } = useParams<{ lang: LanguageId }>();

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

  return (
    <>
      <SpikeTable
        date={recentSpikeDate}
        isLoading={isLoading}
        language={lang}
        spikes={recentSpikes?.slice(0, 5) ?? []}
      />
      <Table>
        <tbody>
          <tr>
            <th>Most recent ticket</th>
            <td>
              {isLoadingInfo ? <Loading type="table-cell" /> : latestTicketDate}
            </td>
          </tr>
          <tr>
            <th>Last Jeeves deployment</th>
            <td>
              {isLoadingInfo ? <Loading type="table-cell" /> : deployedAtDate}
            </td>
          </tr>
        </tbody>
      </Table>
    </>
  );
};

export default Dashboard;
