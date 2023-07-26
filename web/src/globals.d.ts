/** Google Analytics */
declare let ga: (
  action: string,
  type: string,
  data: Record<string, unknown> | string,
) => void;

declare let process: {
  env: {
    API?: string;
    DUOLINGO_JWT?: string;
    NODE_ENV: "development" | "production";
  };
};
