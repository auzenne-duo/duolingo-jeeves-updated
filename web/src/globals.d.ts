/** Google Analytics */
declare let ga: (
  action: string,
  type: string,
  data: Record<string, unknown> | string,
) => void;

declare let process: {
  env: {
    NODE_ENV: "development" | "production";
  };
};
