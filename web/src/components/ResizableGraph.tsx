import Plotly from "plotly.js-basic-dist";
import * as React from "react";
import createPlotlyComponent from "react-plotly.js/factory";

import cn from "classnames";
import styles from "components/ResizableGraph.scss";

/* eslint-disable @typescript-eslint/naming-convention */
export interface RelayoutEvent {
  /** Set when double-clicking the plot to reset the range. */
  "xaxis.autorange"?: boolean;
  /** Set when using the range slider. */
  "xaxis.range"?: [string, string];
  /** Set when selecting an area directly on the plot. */
  "xaxis.range[0]"?: string;
  /** Set when selecting an area directly on the plot. */
  "xaxis.range[1]"?: string;
}
/* eslint-enable @typescript-eslint/naming-convention */

interface PlotState {
  config: unknown;
  data: unknown[];
  frames: unknown[];
  layout: unknown;
}

const Plot = createPlotlyComponent(Plotly);

export const usePlotState = () =>
  React.useState<PlotState>({
    config: {},
    data: [],
    frames: [],
    layout: {},
  });

interface Props {
  className?: string;
  onChange: React.Dispatch<React.SetStateAction<PlotState>>;
  onRelayout?: (e: RelayoutEvent) => void;
  state: PlotState;
}

const ResizableGraph = ({
  className,
  onChange,
  onRelayout,
  state: plotState,
}: Props) => {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const plotRef = React.useRef<typeof Plot>(null);

  React.useEffect(() => {
    if (containerRef.current && plotRef.current) {
      const observer = new ResizeObserver(() =>
        Plotly.Plots.resize(plotRef.current.el),
      );
      observer.observe(containerRef.current);
      return () => observer.disconnect();
    }
    return undefined;
  }, []);

  return (
    <div className={cn(styles.container, className)} ref={containerRef}>
      <div className={styles.inner}>
        <Plot
          className={styles.plot}
          config={plotState.config}
          data={plotState.data}
          frames={plotState.frames}
          layout={plotState.layout}
          onInitialized={(figure: Partial<PlotState>) =>
            onChange(value => ({ ...value, figure }))
          }
          onRelayout={onRelayout}
          onUpdate={(figure: Partial<PlotState>) =>
            onChange(value => ({ ...value, figure }))
          }
          ref={plotRef}
        />
      </div>
    </div>
  );
};

export default ResizableGraph;
