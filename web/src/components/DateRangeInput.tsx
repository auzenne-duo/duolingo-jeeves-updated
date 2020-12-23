import { formatISO, parse, startOfToday } from "date-fns";
import * as React from "react";
import { DateInput } from "web-ui";

import styles from "styles/DateRangeInput.scss";

type DateInputProps = React.ComponentProps<typeof DateInput>;

type DatePickerChangeEvent = Parameters<
  Exclude<DateInputProps["onChange"], undefined>
>[0];

export type DateRangeChangeEvent = { from?: Date; to?: Date };

type PopoverPositionProps = DateInputProps["popoverPosition"];

const formatDate = (date: Date) => formatISO(date, { representation: "date" });

const parseDate = (input: string) =>
  // The y-M-d format accepts but does not require leading zeros.
  parse(input, "y-M-d", startOfToday());

export interface Props
  extends Omit<
    DateInputProps,
    "alignPopover" | "mode" | "onChange" | "other" | "value"
  > {
  alignPopover: "start" | "end";
  from?: Date;
  onChange?: (e: DateRangeChangeEvent) => void;
  to?: Date;
}

const DateRangeInput: React.FC<Props> = ({
  alignPopover,
  from,
  onChange,
  to,
  ...dateInputProps
}) => {
  const endRef = React.useRef<HTMLInputElement>(null);
  const startRef = React.useRef<HTMLInputElement>(null);

  const handleEndChange = (e: DatePickerChangeEvent) => {
    onChange?.({ from: e.other, to: e.newValue });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Do not trigger shortcuts.
    e.stopPropagation();
  };

  const handleStartChange = (e: DatePickerChangeEvent) => {
    onChange?.({ from: e.newValue, to: e.other });
    endRef.current?.focus();
  };

  const popoverPosition: PopoverPositionProps = {
    className: styles[`popover-align-${alignPopover}`],
    direction: "down",
    manualPositioning: true,
  };

  return (
    <div className={styles.wrap} onKeyDown={handleKeyDown}>
      <DateInput
        formatDate={formatDate}
        mode="range-start"
        onChange={handleStartChange}
        other={to}
        parseDate={parseDate}
        popoverPosition={popoverPosition}
        ref={startRef}
        value={from}
        {...dateInputProps}
      />
      <span className={styles.separator}>to</span>
      <DateInput
        formatDate={formatDate}
        mode="range-end"
        onChange={handleEndChange}
        other={from}
        parseDate={parseDate}
        popoverPosition={popoverPosition}
        ref={endRef}
        value={to}
        {...dateInputProps}
      />
    </div>
  );
};

export default DateRangeInput;
