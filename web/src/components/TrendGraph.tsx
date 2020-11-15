import Plotly from "plotly.js-basic-dist";
import * as React from "react";
import createPlotlyComponent from "react-plotly.js/factory";

import { getTimeSeries } from "api";
import { LanguageId } from "components/LanguagePicker";
import { useAwaitedValue } from "components/useAwaitedValue";
import styles from "styles/TrendGraph.scss";

interface PlotState {
  config: any;
  data: any[];
  frames: any[];
  layout: any;
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
  language: LanguageId;
  onRangeChange?: (e: RangeChangeEvent) => void;
  query: string;
  zoomFrom?: Date;
  zoomTo?: Date;
}

const TrendGraph: React.FC<Props> = ({
  language: lang,
  onRangeChange,
  query,
  zoomFrom,
  zoomTo,
}) => {
  const [data] = useAwaitedValue(
    undefined,
    async () => {
      if (!query) {
        return [];
      }
      const unfiltered = await getTimeSeries(lang, { word: query });
      const origin = new Date();
      origin.setDate(origin.getDate() - 100); // 100 days ago.
      return Object.entries(unfiltered).filter(
        ([date]) => new Date(date) >= origin,
      );
    },
    [lang, query],
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
    // Invoking the Date constructor with a date-only string
    // creates a UTC date. Plotly will show it in the local timezone.
    const x = data?.map(([date]) => new Date(date));
    const y = data?.map(([, freq]) => freq);

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
  }, [data, zoomFrom?.toJSON(), zoomTo?.toJSON]);

  return (
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
  );
};

export default TrendGraph;
