import * as React from "react";

/**
 * Use a value that must be awaited before it is available.
 */
export const useAwaitedValue = <T, U>(
  initialValue: U,
  getValue: () => Promise<T>,
  deps: React.DependencyList,
): [T | U, boolean] => {
  const [isLoading, setIsLoading] = React.useState(false);
  const [value, setValue] = React.useState<T | U>(initialValue);

  // Use a layout effect to guarantee the loading
  // state is up-to-date when rendering.
  React.useLayoutEffect(() => {
    let isCleanedUp = false;

    setIsLoading(true);

    (async () => {
      const newValue = await getValue();
      if (!isCleanedUp) {
        setIsLoading(false);
        setValue(newValue);
      }
    })();

    return () => {
      isCleanedUp = true;
    };
  }, deps);

  return [value, isLoading];
};
