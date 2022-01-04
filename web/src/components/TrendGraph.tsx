import Plotly from "plotly.js-basic-dist";
import * as React from "react";
import createPlotlyComponent from "react-plotly.js/factory";
import { useQuery } from "react-query";

import { getTimeSeries } from "api";
import useFeaturesByTeamAndArea from "components/useFeaturesByTeamAndArea";
import styles from "styles/TrendGraph.scss";

interface PlotState {
  config: unknown;
  data: unknown[];
  frames: unknown[];
  layout: unknown;
}

export interface RangeChangeEvent {
  from?: Date;
  to?: Date;
}

interface RelayoutEvent {
  /** Set when using the range slider. */
  "xaxis.range"?: [string, string];
  /** Set when selecting an area directly on the plot. */
  "xaxis.range[0]"?: string;
  /** Set when selecting an area directly on the plot. */
  "xaxis.range[1]"?: string;
}

const BLACK_TEXT = "#3c3c3c";
const JUICY_MACAW = "#1cb0f6";
const JUICY_SWAN = "#e5e5e5";

const Plot = createPlotlyComponent(Plotly);

interface Props {
  language: JSONAPI.LanguageId;
  onRangeChange?: (e: RangeChangeEvent) => void;
  query: string;
  zoomFrom?: Date;
  zoomTo?: Date;
}

const TrendGraph = ({
  language: lang,
  onRangeChange,
  query,
  zoomFrom,
  zoomTo,
}: Props) => {
  const { data: areas = [], isSuccess: areasLoaded } =
    useFeaturesByTeamAndArea();

  const { data } = useQuery(
    ["time-series", { areas, lang, query }],
    () => getTimeSeries(lang, { areas, word: query }),
    {
      enabled: areasLoaded && !!query,
    },
  );

  const [plotState, setPlotState] = React.useState<PlotState>({
    config: {},
    data: [],
    frames: [],
    layout: {},
  });

  const handleRelayout = (e: RelayoutEvent) => {
    if (!data) {
      return;
    }
    let from = e["xaxis.range"]?.[0] ?? e["xaxis.range[0]"];
    let to = e["xaxis.range"]?.[1] ?? e["xaxis.range[1]"];
    // Plotly doesn't really document this event and doesn't
    // supply the data in a consistent format. Just in case
    // they would provide a date-only string, pad it with
    // zeroes to force the Date constructor to treat it as
    // a date in the local timezone.
    if (from?.length === 10) {
      from += " 00:00:00";
    }
    if (to?.length === 10) {
      to += " 00:00:00";
    }
    onRangeChange?.({
      from: from ? new Date(from) : undefined,
      to: to ? new Date(to) : undefined,
    });
  };

  React.useEffect(() => {
    const x = data?.map(({ date }) => date);
    const y = data?.map(({ value }) => value);

    const range = x
      ? [
          zoomFrom ?? new Date(Math.min(...x.map(d => d.valueOf()))),
          zoomTo ?? new Date(Math.max(...x.map(d => d.valueOf()))),
        ]
      : undefined;

    setPlotState({
      config: {
        displayModeBar: false,
        showTips: false,
      },
      data: [
        {
          line: {
            color: JUICY_MACAW,
          },
          mode: "lines",
          type: "scatter",
          x,
          y,
        },
      ],
      frames: [],
      layout: {
        autosize: true,
        font: {
          color: BLACK_TEXT,
          family: "din-round, sans-serif",
        },
        margin: {
          b: 10,
          l: 50,
          r: 10,
          t: 10,
        },
        xaxis: {
          gridcolor: JUICY_SWAN,
          range,
          rangeslider: {
            visible: true,
          },
        },
        yaxis: {
          fixedrange: true,
          gridcolor: JUICY_SWAN,
          rangemode: "tozero",
          title: "# of tickets",
        },
      },
    });
  }, [data, zoomFrom?.valueOf(), zoomTo?.valueOf()]);

  return (
    <div className={styles.container}>
      <div className={styles.inner}>
        <Plot
          className={styles.plot}
          config={plotState.config}
          data={plotState.data}
          frames={plotState.frames}
          layout={plotState.layout}
          onInitialized={(figure: Partial<PlotState>) =>
            setPlotState(value => ({ ...value, figure }))
          }
          onRelayout={handleRelayout}
          onUpdate={(figure: Partial<PlotState>) =>
            setPlotState(value => ({ ...value, figure }))
          }
          useResizeHandler={true}
        />
      </div>
    </div>
  );
};

export default TrendGraph;
